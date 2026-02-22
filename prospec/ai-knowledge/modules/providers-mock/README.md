# Module: providers-mock

> Mock provider — simulates Midjourney generation for testing without Discord credentials.

## Responsibilities

- Simulate the MidjourneyClient interface without external dependencies
- Emit progress callbacks at 25/50/75/100% with configurable delay
- Generate deterministic mock image URLs for testing
- Support task cancellation via asyncio.Task management
- Simulate grid completion + configurable N upscale results lifecycle

## Key Files

| File | Purpose |
|------|---------|
| `src/app/providers/mock/client.py` | MockMidjourneyClient — full Protocol implementation with simulated lifecycle |

## Public Interfaces

- `MockMidjourneyClient(delay: float = 1.0)` — configurable simulation delay
- `imagine(prompt, aspect_ratio, correlation_tag) -> None` — spawns background simulation
- `set_callbacks(on_progress, on_complete, on_error, on_grid_complete, on_upscale_result) -> None` — registers all 5 lifecycle callbacks
- `set_upscale_count(correlation_tag, count) -> None` — sets expected number of upscale results to simulate for a given task; defaults to 1 if not set
- `upscale(message_id, custom_id) -> None` — no-op; upscale results are driven automatically by the simulation loop

## Dependencies

- **Internal**: providers/protocol (MidjourneyClient Protocol)
- **External**: asyncio (stdlib only)

## Design Decisions

- **No external dependencies**: Runs entirely in-process using asyncio
- **Deterministic URLs**: `https://cdn.midjourney.com/mock/{correlation_tag}.png` for test assertions
- **Proportional delay**: Total delay split across 4 progress steps
- **Graceful cancellation**: Tracks spawned tasks and cancels on `stop()`
- **Mock simulates grid + N upscale results**: After emitting `on_grid_complete`, the mock automatically fires `on_upscale_result` N times based on the count set via `set_upscale_count`; defaults to 1 if not set

<!-- prospec:user-start -->
<!-- prospec:user-end -->
