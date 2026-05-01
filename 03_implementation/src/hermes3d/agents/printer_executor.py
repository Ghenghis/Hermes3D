"""Read-only printer poll executor for Phase 3.1."""

from __future__ import annotations

from hermes3d.adapters.moonraker_readonly import MoonrakerReadonlyAdapter
from hermes3d.orchestration import CapabilityToken, Err, OfflineSupervisor, PollRequest, PollResult
from hermes3d.orchestration.types import PrinterMirror, Result

POLL_TOOL = "printer.poll"


class PrinterExecutor:
    """Executes read-only poll requests through the offline supervisor."""

    def __init__(self, *, supervisor: OfflineSupervisor, adapter: MoonrakerReadonlyAdapter) -> None:
        self.supervisor = supervisor
        self.adapter = adapter

    def poll(self, request: PollRequest, *, token: CapabilityToken | None) -> PollResult:
        if request.tool != POLL_TOOL:
            return PollResult(
                run_id=request.run_id,
                agent_id=request.agent_id,
                printer_id=request.printer_id,
                tool=request.tool,
                result=Err("method_not_allowed", "printer executor only accepts poll requests"),
                token_id=None if token is None else token.token_id,
            )
        return self.supervisor.dispatch_poll(request, token=token, handler=self._poll_adapter)

    def _poll_adapter(self, request: PollRequest) -> Result[PrinterMirror]:
        return self.adapter.poll_printer(request.printer_id)
