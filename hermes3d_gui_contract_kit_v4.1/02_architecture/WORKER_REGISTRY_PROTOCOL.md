# Worker Registry Protocol

Workers register with worker id, signed token, capability manifest, tool versions, GPU report, and tunnel URL. States: offline, connecting, online, busy, degraded, blocked, updating, error. Heartbeat every 10 seconds. Missing 30 seconds = degraded. Missing 60 seconds = offline.
