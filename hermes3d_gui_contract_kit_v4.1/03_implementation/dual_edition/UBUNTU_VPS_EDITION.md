# Ubuntu VPS Control Server Edition

Recommended packaging: Docker Compose, Nginx or Caddy reverse proxy, TLS via Cloudflare or Let’s Encrypt, systemd services. Definition of done: deploys on Ubuntu VPS, auth required, worker registers through tunnel, VPS dispatches dry-run job to worker, proof bundle mirrors back, UI mirrors desktop worker state.
