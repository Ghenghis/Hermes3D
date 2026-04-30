# Windows + Ubuntu Test Matrix

Windows gates: Python, Node, GPU detection, Blender detection, slicer detection, Printrun detection, UI launch, dock/undock, worker API health, proof bundle.

Ubuntu gates: server install, auth, worker registry, tunnel status, remote job submission, artifact sync, UI mirrors worker status, proof bundle includes VPS and worker evidence.

Cross-edition gate: VPS detects Windows worker, submits read-only GPU capability job, receives artifact, displays result, builds proof bundle.
