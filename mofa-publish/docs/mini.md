# Mac Mini Deploy

```
mofa publish --site-dir ./docs --target mini --slug my-site --mini-host mini1
```

**URL:** `https://crew.ominix.io/sites/<slug>/` (mini1) or `https://octos.ominix.io/sites/<slug>/` (mini3)

## Steps performed

1. Test SSH connectivity
2. `mkdir -p <remote_root>/sites/<slug>/` on remote
3. `scp -r <site_dir>/.` to remote directory so dotfiles are not skipped
4. Curl the live URL to verify

No Caddy config change needed — `file_server` already serves everything under the web root.

## Optional Mini-specific flags

- `--mini-user <user>` if the SSH username is not `cloud`
- `--ssh-key ~/.ssh/<key>` to force a specific identity and avoid agent/keychain auth spray
- `--ssh-password-env VAR` to use `sshpass` with the password stored in environment variable `VAR`
- `--ssh-port <port>` for non-standard SSH ports
- `--remote-root <path>` if the Caddy-served web root is not `/Users/<mini-user>/octos-web`

## Example with explicit SSH identity

```bash
bash mofa-publish/scripts/publish_site.sh \
  --site-dir ./docs \
  --target mini \
  --mini-host mini1 \
  --mini-user cloud \
  --ssh-key ~/.ssh/id_ed25519 \
  --slug my-site
```

## Example with password auth via `sshpass`

```bash
export MOFA_PUBLISH_SSH_PASSWORD='your-password'

bash mofa-publish/scripts/publish_site.sh \
  --site-dir ./docs \
  --target mini \
  --mini-host mini1 \
  --mini-user cloud \
  --ssh-password-env MOFA_PUBLISH_SSH_PASSWORD \
  --slug my-site
```

## Available Hosts

| Host  | IP           | Domain           | Web Root              |
|-------|--------------|------------------|-----------------------|
| mini1 | 69.194.3.128 | crew.ominix.io   | /Users/cloud/octos-web |
| mini3 | 69.194.3.203 | octos.ominix.io  | /Users/cloud/octos-web |

## SSH troubleshooting

If SSH fails before deployment:
- verify the username with `--mini-user`
- pass `--ssh-key` to force the exact private key the server accepts
- or pass `--ssh-password-env` if the host is configured for password auth
- if the server still rejects the key or password, the helper is working but the remote account setup is not

Mac Mini SSH credentials come from crew profiles, not hardcoded. No secrets stored in pipeline files.

## Onboarding

Required: `ssh`, `scp`, `curl`. Check before running:

```bash
ssh -V
```
