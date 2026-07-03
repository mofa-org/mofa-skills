import json
import os
import base64
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Mapping, Optional


Transport = Callable[
    [str, Dict[str, str], Dict[str, Any]],
    Dict[str, Any],
]

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_VERTEX_LOCATION = "us-central1"
GOOGLE_CLOUD_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def _post_json(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    request_headers = {"Content-Type": "application/json", **headers}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Model provider request failed with HTTP {exc.code}: {detail[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Model provider request failed: {exc.reason}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Model provider returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Model provider returned a non-object response.")
    return parsed


def _post_form(
    url: str,
    fields: Dict[str, str],
) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(fields).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Vertex token request failed with HTTP {exc.code}: {detail[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Vertex token request failed: {exc.reason}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Vertex token endpoint returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Vertex token endpoint returned a non-object response.")
    return parsed


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _load_service_account(credentials_ref: str) -> Dict[str, Any]:
    value = credentials_ref.strip()
    if value.startswith("{"):
        parsed = json.loads(value)
    else:
        with open(value, "r", encoding="utf-8") as fh:
            parsed = json.load(fh)
    if not isinstance(parsed, dict):
        raise ValueError("Vertex service account JSON must be an object.")
    for key in ("client_email", "private_key"):
        if not str(parsed.get(key) or "").strip():
            raise ValueError(f"Vertex service account JSON missing '{key}'.")
    parsed.setdefault("token_uri", "https://oauth2.googleapis.com/token")
    return parsed


def _vertex_base_url(location: str, override_base_url: Optional[str] = None) -> str:
    if override_base_url:
        return override_base_url.rstrip("/")
    if location == "global":
        return "https://aiplatform.googleapis.com/v1"
    return f"https://{location}-aiplatform.googleapis.com/v1"


def _service_account_access_token(service_account: Mapping[str, Any]) -> str:
    now = int(time.time())
    token_uri = str(
        service_account.get("token_uri") or "https://oauth2.googleapis.com/token"
    )
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": str(service_account["client_email"]),
        "scope": GOOGLE_CLOUD_SCOPE,
        "aud": token_uri,
        "exp": now + 3600,
        "iat": now,
    }
    signing_input = ".".join(
        [
            _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url(json.dumps(claims, separators=(",", ":")).encode("utf-8")),
        ]
    )
    with tempfile.NamedTemporaryFile(prefix="mofa-vertex-key.", delete=True) as fh:
        fh.write(str(service_account["private_key"]).encode("utf-8"))
        fh.flush()
        signature = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", fh.name],
            input=signing_input.encode("ascii"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if signature.returncode != 0:
        detail = signature.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Vertex service account signing failed: {detail[:500]}")
    jwt = f"{signing_input}.{_b64url(signature.stdout)}"
    token = _post_form(
        token_uri,
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt,
        },
    )
    access_token = str(token.get("access_token") or "").strip()
    if not access_token:
        raise RuntimeError("Vertex token endpoint did not return access_token.")
    return access_token


def _parse_json_text(text: str) -> Dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        end = value.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model response did not contain a JSON object.")
        parsed = json.loads(value[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model response JSON must be an object.")
    return parsed


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        transport: Transport = _post_json,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def generate(
        self,
        prompt: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        model = urllib.parse.quote(self.model, safe="")
        api_key = urllib.parse.quote(self.api_key, safe="")
        url = (
            f"{self.base_url}/models/{model}:generateContent"
            f"?key={api_key}"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": 0.1,
            },
        }
        response = self.transport(url, {}, payload)
        try:
            parts = response["candidates"][0]["content"]["parts"]
            text = "".join(
                str(part.get("text") or "")
                for part in parts
                if isinstance(part, dict)
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Gemini response did not contain generated content.") from exc
        if not text.strip():
            raise ValueError("Gemini response contained empty generated content.")
        return _parse_json_text(text)


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_OPENAI_MODEL,
        base_url: str = "https://api.openai.com/v1",
        transport: Transport = _post_json,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def generate(
        self,
        prompt: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "grounded_data_table",
                    "strict": False,
                    "schema": schema,
                },
            },
        }
        response = self.transport(
            f"{self.base_url}/chat/completions",
            {"Authorization": f"Bearer {self.api_key}"},
            payload,
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("OpenAI response did not contain generated content.") from exc
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenAI response contained empty generated content.")
        return _parse_json_text(content)


class VertexGeminiClient:
    def __init__(
        self,
        service_account: Mapping[str, Any],
        access_token_provider: Callable[[Mapping[str, Any]], str] = _service_account_access_token,
        model: str = DEFAULT_GEMINI_MODEL,
        location: str = DEFAULT_VERTEX_LOCATION,
        project: Optional[str] = None,
        base_url: Optional[str] = None,
        transport: Transport = _post_json,
    ):
        self.service_account = dict(service_account)
        self.access_token_provider = access_token_provider
        self.model = model
        self.location = location
        self.project = project or str(self.service_account.get("project_id") or "").strip()
        if not self.project:
            raise ValueError(
                "Vertex project is required. Set GOOGLE_CLOUD_PROJECT or include project_id in the service account JSON."
            )
        self.base_url = _vertex_base_url(location, base_url)
        self.transport = transport

    def generate(
        self,
        prompt: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        project = urllib.parse.quote(self.project, safe="")
        location = urllib.parse.quote(self.location, safe="")
        model = urllib.parse.quote(self.model, safe="")
        url = (
            f"{self.base_url}/projects/{project}/locations/{location}"
            f"/publishers/google/models/{model}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": 0.1,
            },
        }
        access_token = self.access_token_provider(self.service_account)
        response = self.transport(
            url,
            {"Authorization": f"Bearer {access_token}"},
            payload,
        )
        try:
            parts = response["candidates"][0]["content"]["parts"]
            text = "".join(
                str(part.get("text") or "")
                for part in parts
                if isinstance(part, dict)
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Vertex Gemini response did not contain generated content.") from exc
        if not text.strip():
            raise ValueError("Vertex Gemini response contained empty generated content.")
        return _parse_json_text(text)


def create_llm_client(
    args: Dict[str, Any],
    env: Optional[Mapping[str, str]] = None,
    transport: Transport = _post_json,
    access_token_provider: Callable[[Mapping[str, Any]], str] = _service_account_access_token,
):
    values = os.environ if env is None else env
    provider = str(
        args.get("provider") or values.get("MOFA_DATA_TABLE_PROVIDER") or ""
    ).strip().lower()
    gemini_key = str(values.get("GEMINI_API_KEY") or "").strip()
    openai_key = str(values.get("OPENAI_API_KEY") or "").strip()
    vertex_credentials = str(
        values.get("GOOGLE_APPLICATION_CREDENTIALS") or values.get("VERTEX_SA_JSON") or ""
    ).strip()
    vertex_access_token = str(
        values.get("VERTEX_ACCESS_TOKEN")
        or values.get("GOOGLE_OAUTH_ACCESS_TOKEN")
        or ""
    ).strip()
    if not provider:
        if gemini_key:
            provider = "gemini"
        elif openai_key:
            provider = "openai"
        elif vertex_credentials or vertex_access_token:
            provider = "vertex"
        else:
            raise ValueError(
                "No supported model credential is configured. "
                "Set GEMINI_API_KEY, OPENAI_API_KEY, GOOGLE_APPLICATION_CREDENTIALS, or VERTEX_SA_JSON."
            )
    if provider not in {"gemini", "openai", "vertex"}:
        raise ValueError(f"Unsupported data table model provider: {provider}")

    model_override = str(
        args.get("model") or values.get("MOFA_DATA_TABLE_MODEL") or ""
    ).strip()
    if provider == "gemini":
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is required for provider 'gemini'.")
        return GeminiClient(
            api_key=gemini_key,
            model=model_override or DEFAULT_GEMINI_MODEL,
            base_url=str(
                values.get("GEMINI_BASE_URL")
                or "https://generativelanguage.googleapis.com/v1beta"
            ),
            transport=transport,
        )
    if provider == "vertex":
        if vertex_access_token:
            service_account = {
                "client_email": "access-token@local",
                "private_key": "unused",
                "project_id": str(values.get("GOOGLE_CLOUD_PROJECT") or "").strip(),
            }
            token_provider = lambda _: vertex_access_token
        else:
            if not vertex_credentials:
                raise ValueError(
                    "GOOGLE_APPLICATION_CREDENTIALS or VERTEX_SA_JSON is required for provider 'vertex'."
                )
            service_account = _load_service_account(vertex_credentials)
            token_provider = access_token_provider
        return VertexGeminiClient(
            service_account=service_account,
            access_token_provider=token_provider,
            model=model_override or DEFAULT_GEMINI_MODEL,
            location=str(
                values.get("GOOGLE_CLOUD_LOCATION")
                or values.get("VERTEX_LOCATION")
                or DEFAULT_VERTEX_LOCATION
            ),
            project=str(values.get("GOOGLE_CLOUD_PROJECT") or "").strip() or None,
            base_url=str(values.get("VERTEX_BASE_URL") or "").strip() or None,
            transport=transport,
        )
    if not openai_key:
        raise ValueError("OPENAI_API_KEY is required for provider 'openai'.")
    return OpenAIClient(
        api_key=openai_key,
        model=model_override or DEFAULT_OPENAI_MODEL,
        base_url=str(values.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"),
        transport=transport,
    )
