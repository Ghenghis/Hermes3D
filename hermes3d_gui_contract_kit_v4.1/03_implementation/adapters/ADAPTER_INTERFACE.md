# Adapter Interface Contract

Each adapter must implement this behavior before UI wiring.

```python
class ToolAdapter:
    key: str
    display_name: str
    dangerous: bool = False

    def detect(self) -> dict: ...
    def capabilities(self) -> dict: ...
    def validate(self) -> dict: ...
    def launch(self, mode: str) -> dict: ...
    def status(self) -> dict: ...
    def dry_run(self, action: dict) -> dict: ...
    def execute(self, action: dict, confirmation: dict | None = None) -> dict: ...
```

## Required result envelope
```json
{
  "ok": true,
  "adapter": "moonraker",
  "mode": "read_only",
  "artifacts": [],
  "logs": [],
  "proof": {
    "timestamp": "UTC",
    "branch": "git-branch",
    "commit": "git-sha"
  }
}
```

## Dangerous actions
If `dangerous=true`, execute requires:
- user confirmation
- reason
- selected printer
- dry-run result
- log path
- rollback/emergency stop if possible
