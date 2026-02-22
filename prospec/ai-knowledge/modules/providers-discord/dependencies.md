# Dependencies: providers-discord

<!-- prospec:auto-start -->

## Internal Imports

| From Module | What | Used In |
|-------------|------|---------|
| providers-discord | `CorrelationManager` | `client.py`, `gateway.py` |
| providers-discord | `InteractionClient` | `client.py` |
| providers-discord | `GatewayMonitor` | `client.py` |
| providers-discord | `parser.*` | `gateway.py` |

## Reverse Dependencies (Who Imports This Module)

| Module | What | Used For |
|--------|------|----------|
| services | `CorrelationManager` | Tag generation in ImagineService |
| core | `CorrelationManager` | Tag lookup in ConcurrencyLimiter |
| api | `CorrelationManager` | DI via set_dependencies |
| infra | `DiscordMidjourneyClient`, `CorrelationManager` | App lifespan startup |

## Third-Party Packages

| Package | Used For |
|---------|----------|
| `discord.py` | Gateway WebSocket client, Message parsing |
| `httpx` | Async HTTP client for Discord Interaction API |

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
