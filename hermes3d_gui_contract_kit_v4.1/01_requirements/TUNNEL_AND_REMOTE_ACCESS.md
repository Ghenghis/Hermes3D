# Tunnel and Remote Access Requirements

Supported tunnel modes: Tailscale preferred, Cloudflare Tunnel optional, WireGuard advanced.

Checks: VPS reaches worker health endpoint; worker authenticates VPS; WebSocket events flow both directions; job dispatch works without exposing the worker publicly; printer LAN endpoints are not exposed to public internet. Tunnels fail closed.
