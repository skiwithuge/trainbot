import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, User
from telegram.ext import ContextTypes
from trainbot.auth import restricted
from trainbot.config import Config


@pytest.mark.asyncio
async def test_restricted_decorator_blocks_unauthorized_user():
    config = Config(
        telegram_bot_token="fake",
        sncf_api_key="fake",
        allowed_user_ids=frozenset({12345}),
    )

    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 99999
    user.full_name = "Intruder User"
    user.username = "intruder"
    update.effective_user = user
    update.callback_query = None
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot_data = {"config": config}

    handler_called = False

    @restricted
    async def sample_handler(u, c):
        nonlocal handler_called
        handler_called = True

    await sample_handler(update, context)

    assert not handler_called
    update.effective_message.reply_text.assert_awaited_once()
    call_args = update.effective_message.reply_text.call_args[0][0]
    assert "99999" in call_args
    assert "Accès non autorisé" in call_args


@pytest.mark.asyncio
async def test_restricted_decorator_allows_authorized_user():
    config = Config(
        telegram_bot_token="fake",
        sncf_api_key="fake",
        allowed_user_ids=frozenset({12345}),
    )

    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 12345
    user.full_name = "Authorized User"
    update.effective_user = user
    update.callback_query = None
    update.effective_message = MagicMock()

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot_data = {"config": config}

    handler_called = False

    @restricted
    async def sample_handler(u, c):
        nonlocal handler_called
        handler_called = True

    await sample_handler(update, context)

    assert handler_called
    update.effective_message.reply_text.assert_not_called()
