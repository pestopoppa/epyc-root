# Private API isolation proof

The pinned native API reached `/health` with an inherited loopback listener after private-write and socket-creation denial checks. It shut down and its owned PID was absent; exit code 1 followed normal shutdown when seccomp denied Uvicorn’s signal re-raise. The health response was degraded with zero models loaded.

This is an isolation/lifecycle control, not an EvalTower result or an inference run. Denying new sockets also blocks the API’s dynamic backend HTTP connections; Landlock’s port rules alone do not prove destination-IP isolation. The B4c row is not ready until the actual API/backend/EvalTower lifecycle is isolated and qualified.
