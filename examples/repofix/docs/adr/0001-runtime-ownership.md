# ADR-0001: Runtime ownership

- Status: accepted
- Date: 2026-07-17

Go owns Run state, cancellation, persistence and the Daytona lifecycle. Python owns the model decision loop. Python invokes sandbox capabilities through the Go Tool Gateway and never receives Daytona credentials. Go persists domain events and decides the final Run status.

The Python service exposes one full-run operation rather than a per-step `/next` operation. This keeps context and model-specific state inside Python while leaving resource ownership and recovery inside Go.
