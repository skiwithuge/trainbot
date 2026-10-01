"""Integration tests for Telegram bot handlers."""
from unittest.mock import AsyncMock, MagicMock
import pytest
from telegram import Update
from telegram.constants import ParseMode

from trainbot.bot.handlers import (
    bus_command,
    callback_handler,
    help_command,
    start_command,
    trains_command,
)
from trainbot.config import Config
from trainbot.envibus.client import EnvibusClient
from trainbot.sncf.client import SncfClient


@pytest.fixture
def mock_context():
    context = MagicMock()
    config = Config(
        telegram_bot_token="test_token",
        sncf_api_key="",
        allowed_user_ids=frozenset({12345}),
        timezone="Europe/Paris",
    )
    sncf_client = SncfClient(api_key="", mock_mode=True)
    envibus_client = EnvibusClient(mock_mode=True)

    context.bot_data = {
        "config": config,
        "sncf_client": sncf_client,
        "envibus_client": envibus_client,
    }
    return context


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    message = AsyncMock()
    waiting_msg = AsyncMock()
    message.reply_text.return_value = waiting_msg
    update.effective_message = message
    return update


@pytest.mark.asyncio
async def test_bus_command(mock_update, mock_context):
    await bus_command(mock_update, mock_context)
    waiting_msg = mock_update.effective_message.reply_text.return_value
    assert waiting_msg.edit_text.called
    args, kwargs = waiting_msg.edit_text.call_args
    assert "Envibus Ligne A" in args[0]
    assert kwargs["parse_mode"] == ParseMode.HTML
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_trains_command(mock_update, mock_context):
    await trains_command(mock_update, mock_context)
    waiting_msg = mock_update.effective_message.reply_text.return_value
    assert waiting_msg.edit_text.called
    args, kwargs = waiting_msg.edit_text.call_args
    # Contains both TER and Envibus
    assert "TER" in args[0]
    assert "Envibus Ligne A" in args[0]


@pytest.mark.asyncio
async def test_callback_handler_bus_actions(mock_context):
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.message = MagicMock()
    query.message.text_html = "old"

    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.callback_query = query

    # Test bus_refresh
    query.data = "bus_refresh:antibes_to_nice"
    await callback_handler(update, mock_context)
    assert query.edit_message_text.called
    args, _ = query.edit_message_text.call_args
    assert "Collège Bertone ➔ Pôle d'Échanges d'Antibes" in args[0]

    # Test bus_switch
    query.edit_message_text.reset_mock()
    query.data = "bus_switch:nice_to_antibes"
    await callback_handler(update, mock_context)
    assert query.edit_message_text.called
    args, _ = query.edit_message_text.call_args
    assert "Pôle d'Échanges d'Antibes ➔ Collège Bertone" in args[0]


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    await help_command(mock_update, mock_context)
    assert mock_update.effective_message.reply_text.called
    args, _ = mock_update.effective_message.reply_text.call_args
    assert "/bus" in args[0]
