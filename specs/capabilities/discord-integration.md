# Capability Spec: Discord Integration

## Requirements

| REQ ID | Description | Status | Source |
|--------|-------------|--------|--------|
| REQ-DISCORD-001 | Trigger MJ /imagine via Discord Interaction API | Active | build-midjourney-relay-api |
| REQ-DISCORD-002 | Monitor MJ Bot responses via Discord Gateway | Active | build-midjourney-relay-api |
| REQ-DISCORD-003 | Message correlation via embedded tags (mjr-{16hex}) | Active | build-midjourney-relay-api |
| REQ-DISCORD-004 | Upscale button extraction (U1-U4 custom_ids) and result detection from MJ messages | Active | add-auto-upscale |
| REQ-DISCORD-005 | Discord component interaction (type 3) for clicking U1-U4 upscale buttons | Active | add-auto-upscale |
| REQ-DISCORD-006 | Callback separation: 5 callbacks (on_progress, on_complete, on_error, on_grid_complete, on_upscale_result) | Active | add-auto-upscale |

## Change History

| Date | Change | REQ IDs |
|------|--------|---------|
| 2026-02-22 | Initial creation from build-midjourney-relay-api | REQ-DISCORD-001 ~ 003 |
| 2026-02-22 | add-auto-upscale: Added upscale button parsing, component interactions, and 5-callback architecture | REQ-DISCORD-004~006 (ADDED) |
