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
        client.set_callbacks(
            on_progress=AsyncMock(),
            on_complete=AsyncMock(),
            on_error=AsyncMock(),
            on_grid_complete=AsyncMock(),
            on_upscale_result=AsyncMock(),
        )

    async def test_mock_client_imagine_calls_grid_complete(self) -> None:
        client = MockMidjourneyClient(delay=0.01)
        on_grid_complete = AsyncMock()
        on_upscale_result = AsyncMock()
        client.set_callbacks(
            on_progress=AsyncMock(),
            on_complete=AsyncMock(),
            on_error=AsyncMock(),
            on_grid_complete=on_grid_complete,
            on_upscale_result=on_upscale_result,
        )
        await client.start()
        await client.imagine(
            prompt="a cat",
            aspect_ratio="1:1",
            correlation_tag="mjr-test1234",
        )
        # Wait for mock processing to complete
        await asyncio.sleep(0.2)
        await client.stop()

        on_grid_complete.assert_called_once()
        call_args = on_grid_complete.call_args
        assert call_args[1]["correlation_tag"] == "mjr-test1234"
        assert call_args[1]["image_url"].startswith("https://")
        assert "message_id" in call_args[1]
        assert "upscale_buttons" in call_args[1]

        # Default upscale_count=1, so one upscale result
        on_upscale_result.assert_called_once()
        result_args = on_upscale_result.call_args
        assert result_args[1]["correlation_tag"] == "mjr-test1234"
        assert result_args[1]["upscale_index"] == 1

    async def test_mock_client_imagine_calls_progress(self) -> None:
        client = MockMidjourneyClient(delay=0.01)
        on_progress = AsyncMock()
        client.set_callbacks(
            on_progress=on_progress,
            on_complete=AsyncMock(),
            on_error=AsyncMock(),
            on_grid_complete=AsyncMock(),
            on_upscale_result=AsyncMock(),
        )
        await client.start()
        await client.imagine(
            prompt="a dog",
            aspect_ratio="16:9",
            correlation_tag="mjr-test5678",
        )
        await asyncio.sleep(0.2)
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
            on_grid_complete=AsyncMock(),
            on_upscale_result=AsyncMock(),
        )
        await client.start()
        await client.imagine(
            prompt="a bird",
            aspect_ratio="1:1",
            correlation_tag="mjr-test9999",
        )
        await asyncio.sleep(0.2)
        await client.stop()

        on_error.assert_not_called()

    async def test_mock_client_upscale_count_4(self) -> None:
        client = MockMidjourneyClient(delay=0.01)
        on_grid_complete = AsyncMock()
        on_upscale_result = AsyncMock()
        client.set_callbacks(
            on_progress=AsyncMock(),
            on_complete=AsyncMock(),
            on_error=AsyncMock(),
            on_grid_complete=on_grid_complete,
            on_upscale_result=on_upscale_result,
        )
        client.set_upscale_count("mjr-test4444", 4)
        await client.start()
        await client.imagine(
            prompt="a landscape",
            aspect_ratio="16:9",
            correlation_tag="mjr-test4444",
        )
        await asyncio.sleep(0.2)
        await client.stop()

        on_grid_complete.assert_called_once()
        assert on_upscale_result.call_count == 4
        indices = [call[1]["upscale_index"] for call in on_upscale_result.call_args_list]
        assert sorted(indices) == [1, 2, 3, 4]
