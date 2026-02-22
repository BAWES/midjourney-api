# Patterns: providers-discord

<!-- prospec:auto-start -->

## Correlation Tag Strategy

Embed unique tag in prompt for request-response matching:

```python
# Generate: 16 hex chars via secrets.token_hex(8)
tag = f"mjr-{secrets.token_hex(8)}"  # e.g., "mjr-a1b2c3d4e5f67890"

# Embed in prompt
embedded = f"{prompt} {tag}"

# Extract from response via regex
TAG_PATTERN = re.compile(r"mjr-[a-f0-9]{16}")
match = TAG_PATTERN.search(message_content)
```

## Composition Pattern

DiscordMidjourneyClient composes two sub-clients:

```python
class DiscordMidjourneyClient:
    def __init__(self, bot_token, user_token, channel_id, correlation):
        self._interaction = InteractionClient(user_token, channel_id)
        self._gateway = GatewayMonitor(bot_token, int(channel_id), correlation)
```

## Discord Interaction Payload (Type 2: Application Command)

```python
payload = {
    "type": 2,
    "application_id": MJ_APP_ID,
    "channel_id": channel_id,
    "data": {
        "id": command_id,
        "name": "imagine",
        "type": 1,
        "options": [{"type": 3, "name": "prompt", "value": prompt}],
    },
    "nonce": str(random.randint(1, 2**53)),
}
```

## Command Cache with TTL

```python
if self._command_cache and (time.monotonic() - self._cache_time < COMMAND_CACHE_TTL):
    return self._command_cache
# Fetch fresh from Discord API
```

## Gateway Event Handling

```python
async def _handle_message(self, message):
    if message.channel.id != self._channel_id:
        return
    if message.author.id != MJ_BOT_ID:
        return
    tag = self._correlation.extract_tag(message.content or "")
    if not tag:
        return
    parsed = parse_mj_message(message)
    # Route to appropriate callback
```

## Message Parsing

Progress detection via regex:

```python
def extract_progress(content: str) -> int | None:
    match = re.search(r"\((\d+)%\)", content)
    return int(match.group(1)) if match else None
```

Completion detection via attachments:

```python
def is_completed(message) -> bool:
    return bool(message.attachments) and not extract_progress(message.content or "")
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
