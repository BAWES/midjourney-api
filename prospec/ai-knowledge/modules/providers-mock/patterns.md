# Patterns: providers-mock

<!-- prospec:auto-start -->

## Simulated Progress

4-step progress emission with proportional delay:

```python
async def _simulate_generation(self, correlation_tag):
    step_delay = self._delay / 4
    for pct in [25, 50, 75, 100]:
        await asyncio.sleep(step_delay)
        await self._on_progress(correlation_tag, pct)
    await self._on_complete(
        correlation_tag,
        f"https://cdn.midjourney.com/mock/{correlation_tag}.png",
    )
```

## Background Task Management

```python
async def imagine(self, prompt, aspect_ratio, correlation_tag):
    task = asyncio.create_task(self._simulate_generation(correlation_tag))
    self._tasks.append(task)

async def stop(self):
    for task in self._tasks:
        task.cancel()
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
