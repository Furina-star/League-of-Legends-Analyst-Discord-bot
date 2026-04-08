import pytest
from unittest.mock import AsyncMock, patch
from riot_api import RiotAPIClient


# The @pytest.mark.asyncio tells pytest that this test uses async/await
@pytest.mark.asyncio
async def test_get_puuid_mocked():
    # Set up a client with a fake API key
    client = RiotAPIClient(api_key="FAKE_KEY")

    # Patch (Mock) the _fetch method so it never actually connects to the internet
    with patch.object(client, '_fetch', new_callable=AsyncMock) as mock_fetch:
        # Tell the fake server exactly what JSON to return
        mock_fetch.return_value = {"puuid": "fake-puuid-12345"}

        # Run the function
        result = await client.get_puuid("Hide on bush", "KR1")

        # Assert (Verify) the results!
        assert result == "fake-puuid-12345"
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_get_champion_mastery_bot_bouncer():
    client = RiotAPIClient(api_key="FAKE_KEY")

    # Test that passing 'None' (a bot) returns 0 mastery immediately without fetching
    with patch.object(client, '_fetch', new_callable=AsyncMock) as mock_fetch:
        result = await client.get_champion_mastery(None, 85)

        assert result == 0
        mock_fetch.assert_not_called()  # It should have bounced before fetching!