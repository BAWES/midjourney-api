# add-auto-upscale — Archive Summary

- **Archived**: 2026-02-22
- **Original Created**: 2026-02-22
- **Quality Grade**: B (Fair)

## User Story

As an **API user**,
I want to specify how many images to upscale (1-4, default 1) when submitting `/imagine`,
So that I can flexibly control how many individual high-resolution images I receive.

## Affected Modules

| Module | Impact | Description |
|--------|--------|-------------|
| models | High | Added UPSCALING enum, image_urls JSON column, upscale_count column |
| services | High | Added UPSCALING transitions, update_image_urls method |
| core | High | Added on_grid_complete, on_upscale_result callbacks, UpscaleTracker, dual timeouts |
| providers-discord | High | Parser upscale detection, send_component_interaction, 5-callback set_callbacks |
| providers-mock | Medium | Simulated grid + N upscale lifecycle |
| api | Low | ImagineRequest upscale_count, TaskResponse image_urls |
| infra | Low | mj_upscale_timeout_seconds config |

## Requirements

| REQ ID | Status | Description |
|--------|--------|-------------|
| REQ-MODELS-003 | ADDED | UPSCALING task status enum value |
| REQ-MODELS-004 | ADDED | image_urls and upscale_count columns |
| REQ-DISCORD-004 | ADDED | Upscale button extraction and result detection |
| REQ-DISCORD-005 | ADDED | Discord component interaction (button click) |
| REQ-DISCORD-006 | ADDED | Callback separation design (5 callbacks) |
| REQ-CORE-001 | ADDED | Upscale orchestration and tracking |
| REQ-CORE-002 | ADDED | Upscale timeout and recovery |
| REQ-MOCK-001 | ADDED | Mock upscale simulation |
| REQ-TASK-001 | MODIFIED | Task lifecycle state machine (added UPSCALING) |

## Completion

- **Tasks**: 38/38 (100%)
- **Tests**: 122 passed (36 new upscale tests + 86 existing)
- **Commits**: 5 atomic commits (feat x2, test x1, fix x2)

## Knowledge Update

The following module documentation may need updating:
- `prospec/ai-knowledge/modules/models/README.md`
- `prospec/ai-knowledge/modules/core/README.md`
- `prospec/ai-knowledge/modules/providers-discord/README.md`
- `prospec/ai-knowledge/modules/providers-mock/README.md`
- `prospec/ai-knowledge/modules/services/README.md`
