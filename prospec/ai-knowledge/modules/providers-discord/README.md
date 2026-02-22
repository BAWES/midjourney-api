# Module: providers-discord

> Discord provider — sends /imagine commands, monitors gateway events, correlates responses.

## Responsibilities

- Send Midjourney `/imagine` commands via Discord Interaction API (type 2)
- Monitor Discord Gateway (WebSocket) for Midjourney bot responses
- Correlate incoming messages to tasks via embedded correlation tags
- Parse message content for progress percentages, completion state, image URLs
- Manage command cache with TTL expiration
- Parse upscale button custom_ids from grid completion messages
- Send type 3 component interactions for button clicks

## Key Files

| File | Purpose |
|------|---------|
| `src/app/providers/discord/client.py` | DiscordMidjourneyClient — composes InteractionClient + GatewayMonitor |
| `src/app/providers/discord/interaction.py` | InteractionClient — HTTP interactions with Discord API |
| `src/app/providers/discord/gateway.py` | GatewayMonitor — WebSocket listener via discord.py |
| `src/app/providers/discord/parser.py` | Message parsing: progress extraction, completion detection, image URL, upscale button extraction |
| `src/app/providers/discord/correlation.py` | CorrelationManager — tag generation, embedding, lookup |

## Public Interfaces

- `DiscordMidjourneyClient` — implements `MidjourneyClient` Protocol
  - `upscale(message_id, custom_id) -> None` — sends a type 3 component interaction for a specific upscale button
  - `set_upscale_count(correlation_tag, count) -> None` — no-op (count managed by ConcurrencyLimiter)
- `CorrelationManager` — in-memory tag-to-task mapping
- `InteractionClient.send_imagine(prompt) -> int` — sends /imagine command
- `InteractionClient.send_component_interaction(message_id, custom_id) -> int` — sends type 3 component interaction for button clicks
- `GatewayMonitor` — discord.py-based WebSocket monitor
- Parser functions in `parser.py`:
  - `extract_upscale_buttons(message) -> list[dict]` — extract U1-U4 button custom_ids from a grid completion message
  - `is_grid_completion(message) -> bool` — primary discriminator; true when message contains upscale buttons and no progress indicator
  - `is_upscale_result(message) -> bool` — true when message is a single upscaled image (not a grid)
  - `extract_upscale_index(custom_id) -> int` — parse the 1-based index from a button custom_id

## Dependencies

- **Internal**: providers/protocol (MidjourneyClient Protocol)
- **External**: discord.py, httpx

## Design Decisions

- **Composition over inheritance**: Client composes InteractionClient (HTTP) + GatewayMonitor (WebSocket)
- **Correlation tag strategy**: Embeds `mjr-{16_hex}` tag in prompt text for response matching
- **Anti-detection**: Random delay (1-3s) before interaction requests
- **Command caching**: `/imagine` command metadata cached with 1-hour TTL
- **Channel filtering**: Gateway only processes messages from MJ bot in configured channel
- **is_grid_completion as primary discriminator**: Three-way message routing (progress update / grid completion / upscale result) is gated on `is_grid_completion` first, enabling clean separation of the upscale phase

<!-- prospec:user-start -->
<!-- prospec:user-end -->
