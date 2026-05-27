# Dynamic Apps on Mini (Reverse Proxy)

The default Mini deploy assumes a static site under `/Users/cloud/octos-web/sites/<slug>/`, served directly by Caddy.

If the site is a dynamic app (Next.js `next start`, custom API server) instead of a static export, you need a different Mini setup:
- run the app as a long-lived process on a localhost port
- add a `reverse_proxy` rule in Caddy
- set `basePath` in the app if you want it mounted under `/sites/<slug>/`

## Recommended: dedicated subdomain

Run the app on the Mini, for example on `127.0.0.1:3100`, then add a Caddy block like:

```caddyfile
mofa.crew.ominix.io {
  reverse_proxy 127.0.0.1:3100
}
```

This is the cleanest option because the app can live at `/` and does not need path-prefix rewriting.

## Path proxy: mount under `/sites/<slug>/`

If you must keep the site under the shared domain path, Caddy needs a path handler:

```caddyfile
crew.ominix.io {
  handle_path /sites/mofa/* {
    reverse_proxy 127.0.0.1:3100
  }

  handle {
    root * /Users/cloud/octos-web
    file_server
  }
}
```

Requirements for the app in this mode:
- Next.js must set `basePath: '/sites/mofa'`
- assets and links must respect that base path
- static-export sites do not need proxying at all

## Process management

Proxy mode requires a process manager. On macOS Mini that usually means:
- `launchd` plist for `next start --hostname 127.0.0.1 --port 3100`
- logs redirected to a known file
- Caddy reloaded after config change

The repo does not contain the Mini Caddyfile itself, so this skill can document the shape but cannot apply the remote Caddy change from here.

## Static vs dynamic recommendation

- static exports (`quarto`, `astro build`, `next build` with `output: 'export'`) — keep the default `file_server` path; no proxy needed
- dynamic Node apps (`next start`, custom API server) — use a dedicated subdomain and reverse proxy

A sample Caddyfile lives at `examples/Caddyfile.proxy.example`.
