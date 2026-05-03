# Hermes3D Deployment Bundle

This directory contains templates for the split deployment model:

- Hostinger VPS: public HTTPS entry point, Caddy reverse proxy, Hermes3D app,
  Postgres, Redis, Tailscale sidecar, and Restic backups to Backblaze B2.
- Local gaming PC: private Ollama inference host reachable only through
  Tailscale.

No secrets, IP addresses, or real hostnames are committed here. Copy the example
files, fill in your own values on the target machines, and keep the filled files
out of Git.

## Quick Start

1. Copy `vps/.env.vps.example` to `vps/.env` on the VPS and replace every
   placeholder.
2. Point your public DNS name at the VPS.
3. Join the local inference PC and VPS to the same Tailscale tailnet.
4. Follow `local/tailscale-setup.md` to expose Ollama only on the private mesh.
5. Start the VPS stack:

```bash
cd 06_release/deploy/vps
docker compose up -d
```

6. Confirm Caddy serves HTTPS for `HERMES_PUBLIC_DOMAIN`.
7. Install the Restic unit pair from `vps/restic-backup.timer.conf` and keep the
   B2 credentials in `/etc/hermes/restic.env`, not in Git.

## Security Notes

- Do not port-forward Ollama or any inference service.
- Do not use Cloudflare Tunnel for the inference path; Tailscale is the chosen
  mesh.
- Put basic auth or an equivalent access layer in front of Gradio before public
  exposure. Generate a Caddy password hash on the VPS:

```bash
caddy hash-password
```

Then add a `basicauth` block to the Gradio handler in `vps/Caddyfile`.

## Troubleshooting

- `docker compose config` should parse `vps/docker-compose.yml` before deploy.
- `caddy validate --config vps/Caddyfile --adapter caddyfile` should pass on
  the VPS.
- If the UI starts but inference fails, test the Tailscale Ollama URL from the
  VPS with `/api/tags`.
- If backups fail, run `restic snapshots` with the same environment file used by
  the systemd service.

## Restore From Backup

1. Reinstall Docker, Caddy, Tailscale, and Restic on a replacement VPS.
2. Restore `/etc/hermes` from your offline copy or Restic snapshot.
3. Export `B2_ACCOUNT_ID`, `B2_ACCOUNT_KEY`, `RESTIC_PASSWORD`, and
   `RESTIC_REPOSITORY`.
4. Run `restic restore latest --target /`.
5. Start the stack with `docker compose up -d` and verify Caddy plus Tailscale.
