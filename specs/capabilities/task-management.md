# Capability Spec: Task Management

## Requirements

| REQ ID | Description | Status | Source |
|--------|-------------|--------|--------|
| REQ-TASK-001 | Task lifecycle state machine (QUEUED → PROCESSING → UPSCALING → SUCCESS/FAILED) | Active | build-midjourney-relay-api, add-auto-upscale |
| REQ-TASK-002 | Concurrency control via asyncio.Semaphore (default 3) | Active | build-midjourney-relay-api |
| REQ-MODELS-003 | UPSCALING task status enum value for tracking upscale phase | Active | add-auto-upscale |
| REQ-MODELS-004 | image_urls (JSON) and upscale_count (int) columns on Task model | Active | add-auto-upscale |
| REQ-CORE-001 | Upscale orchestration via on_grid_complete/on_upscale_result with UpscaleTracker | Active | add-auto-upscale |
| REQ-CORE-002 | Dual timeout (PROCESSING + UPSCALING) and UPSCALING recovery on restart | Active | add-auto-upscale |
| REQ-MOCK-001 | Mock client simulates grid + N upscale lifecycle with separated callbacks | Active | add-auto-upscale |

## Change History

| Date | Change | REQ IDs |
|------|--------|---------|
| 2026-02-22 | Initial creation from build-midjourney-relay-api | REQ-TASK-001 ~ 002 |
| 2026-02-22 | add-auto-upscale: Added UPSCALING status, image_urls/upscale_count fields, upscale orchestration, dual timeouts, mock simulation | REQ-TASK-001 (MODIFIED), REQ-MODELS-003~004, REQ-CORE-001~002, REQ-MOCK-001 (ADDED) |
