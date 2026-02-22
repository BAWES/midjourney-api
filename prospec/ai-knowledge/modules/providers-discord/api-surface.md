# API Surface: providers-discord

<!-- prospec:auto-start -->

## Protocol

### `MidjourneyClient` (defined in `providers/protocol.py`)
```python
@runtime_checkable
class MidjourneyClient(Protocol):
    async def imagine(self, prompt: str, aspect_ratio: str, correlation_tag: str) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def set_callbacks(
        self,
        on_progress: Callable[..., Coroutine],
        on_complete: Callable[..., Coroutine],
        on_error: Callable[..., Coroutine],
    ) -> None: ...
```

## Classes

### `DiscordMidjourneyClient`
```python
class DiscordMidjourneyClient:
    def __init__(
        self,
        bot_token: str,
        user_token: str,
        channel_id: str,
        correlation: CorrelationManager | None = None,
    ) -> None: ...

    @property
    def correlation_manager(self) -> CorrelationManager: ...

    def set_callbacks(self, on_progress, on_complete, on_error) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def imagine(self, prompt: str, aspect_ratio: str, correlation_tag: str) -> None: ...
```

### `InteractionClient`
```python
class InteractionClient:
    def __init__(self, user_token: str, channel_id: str) -> None: ...

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def get_guild_id(self) -> str: ...
    async def get_imagine_command(self, force_refresh: bool = False) -> dict: ...
    async def send_imagine(self, prompt: str) -> int: ...
    def invalidate_command_cache(self) -> None: ...
```

### `GatewayMonitor`
```python
class GatewayMonitor:
    def __init__(
        self,
        bot_token: str,
        channel_id: int,
        correlation_manager: CorrelationManager,
    ) -> None: ...

    def set_callbacks(self, on_progress, on_complete, on_error) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

### `CorrelationManager`
```python
class CorrelationManager:
    def generate_tag(self) -> str: ...
    def embed_in_prompt(self, prompt: str, tag: str) -> str: ...
    def extract_tag(self, text: str) -> str | None: ...
    def register(self, tag: str, task_id: str) -> None: ...
    def lookup(self, tag: str) -> str | None: ...
    def unregister(self, tag: str) -> None: ...
    def reconstruct(self, tag_task_pairs: list[tuple[str, str]]) -> None: ...
```

## Functions

### Parser Functions
```python
def extract_progress(content: str) -> int | None: ...
def is_completed(message: Any) -> bool: ...
def extract_image_url(message: Any) -> str | None: ...
def parse_mj_message(message: Any) -> dict[str, Any]: ...
```

## Constants

```python
MJ_APP_ID = "936929561302675456"
MJ_BOT_ID = 936929561302675456
DISCORD_API = "https://discord.com/api/v10"
COMMAND_CACHE_TTL = 3600
TAG_PATTERN = re.compile(r"mjr-[a-f0-9]{16}")
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
