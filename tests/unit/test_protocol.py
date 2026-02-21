import asyncio
from unittest.mock import AsyncMock

import pytest

from app.providers.protocol import MidjourneyClient
from app.providers.mock.client import MockMidjourneyClient


class TestMidjourneyClientProtocol:
    def test_mock_client_implements_protocol(self) -> None:
        client = MockMidjourneyClient()
        assert isinstance(client, MidjourneyClient)

    async def test_mock_client_start_stop(self) -> None:
        client = MockMidjourneyClient()
        await client.start()
        await client.stop()

    async def test_mock_client_set_callbacks(self) -> None:
        client = MockMidjourneyClient()
        on_progress = AsyncMock()
        on_complete = AsyncMock()
        on_error = AsyncMock()
        client.set_callbacks(
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
        )

    async def test_mock_client_imagine_calls_complete(self) -> None:
        client = MockMidjourneyClient(delay=0.01)
        on_progress = AsyncMock()
        on_complete = AsyncMock()
        on_error = AsyncMock()
        client.set_callbacks(
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
        )
        await client.start()
        await client.imagine(
            prompt="a cat",
            aspect_ratio="1:1",
            correlation_tag="mjr-test1234",
        )
        # Wait for mock processing to complete
        await asyncio.sleep(0.1)
        await client.stop()

        on_complete.assert_called_once()
        call_args = on_complete.call_args
        assert call_args[1]["correlation_tag"] == "mjr-test1234"
        assert call_args[1]["image_url"].startswith("https://")

    async def test_mock_client_imagine_calls_progress(self) -> None:
        client = MockMidjourneyClient(delay=0.01)
        on_progress = AsyncMock()
        on_complete = AsyncMock()
        on_error = AsyncMock()
        client.set_callbacks(
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
        )
        await client.start()
        await client.imagine(
            prompt="a dog",
            aspect_ratio="16:9",
            correlation_tag="mjr-test5678",
        )
        await asyncio.sleep(0.1)
        await client.stop()

        assert on_progress.call_count > 0
        # Progress should include correlation_tag and percentage
        for call in on_progress.call_args_list:
            assert "correlation_tag" in call[1]
            assert "progress" in call[1]

    async def test_mock_client_no_error_on_success(self) -> None:
        client = MockMidjourneyClient(delay=0.01)
        on_error = AsyncMock()
        client.set_callbacks(
            on_progress=AsyncMock(),
            on_complete=AsyncMock(),
            on_error=on_error,
        )
        await client.start()
        await client.imagine(
            prompt="a bird",
            aspect_ratio="1:1",
            correlation_tag="mjr-test9999",
        )
        await asyncio.sleep(0.1)
        await client.stop()

        on_error.assert_not_called()
