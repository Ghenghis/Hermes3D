# Local Tailscale Setup for Hermes3D Inference

The VPS should never reach your local inference host through public port
forwarding. Use Tailscale as the private mesh between the Hostinger VPS and the
gaming PC that runs Ollama.

## Windows Host Setup

1. Install Tailscale on the Windows gaming PC from the official installer.
2. Authenticate into the same tailnet that the VPS will join.
3. In the Tailscale admin console, tag the PC as `tag:llm-host`.
4. Install Ollama 0.5 or newer.
5. Set `OLLAMA_HOST=0.0.0.0:11434` as a machine-level environment variable.
6. Restart Ollama so it binds to the Tailscale interface.
7. From the VPS, verify:

```bash
curl http://gaming-pc.tailnet-name.ts.net:11434/api/tags
```

Replace `gaming-pc.tailnet-name.ts.net` with the MagicDNS name assigned by
your own tailnet.

## Minimal ACL Snippet

This example allows the VPS tag to reach only Ollama on the LLM host tag.
Everything else remains denied by the rest of your tailnet policy.

```json
{
  "tagOwners": {
    "tag:vps": ["autogroup:admin"],
    "tag:llm-host": ["autogroup:admin"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["tag:vps"],
      "dst": ["tag:llm-host:11434"]
    }
  ]
}
```

Do not replace Tailscale with a public tunnel for inference traffic.
