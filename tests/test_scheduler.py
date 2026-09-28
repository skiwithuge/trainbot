import pytest
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo
from telegram.ext import ContextTypes
from trainbot.config import Config
from trainbot.scheduler import (
    broadcast_commute_status,
    parse_time_string,
    setup_scheduler,
    WEEKDAYS,
)
from trainbot.sncf.client import SncfClient
from trainbot.sncf.models import CommuteDirection


def test_parse_time_string():
    tz = ZoneInfo("Europe/Paris")
    t1 = parse_time_string("07:00", tz)
    assert t1.hour == 7
    assert t1.minute == 0
    assert t1.tzinfo == tz

    t2 = parse_time_string("16:30", tz)
    assert t2.hour == 16
    assert t2.minute == 30


def test_setup_scheduler_registers_jobs():
    app = MagicMock()
    app.job_queue = MagicMock()

    config = Config(
        telegram_bot_token="test",
        sncf_api_key="test",
        allowed_user_ids=frozenset({1001}),
        timezone="Europe/Paris",
        morning_time="07:00",
        evening_time="16:00",
    )

    setup_scheduler(app, config)
    assert app.job_queue.run_daily.call_count == 2

    # Check that both calls targeted weekdays (1, 2, 3, 4, 5)
    calls = app.job_queue.run_daily.call_args_list
    assert calls[0].kwargs["days"] == WEEKDAYS
    assert calls[0].kwargs["name"] == "morning_commute_antibes_to_nice"
    assert calls[1].kwargs["days"] == WEEKDAYS
    assert calls[1].kwargs["name"] == "evening_commute_nice_to_antibes"


@pytest.mark.asyncio
async def test_broadcast_commute_status_sends_to_all_users():
    config = Config(
        telegram_bot_token="test",
        sncf_api_key="",
        allowed_user_ids=frozenset({1001, 1002}),
        timezone="Europe/Paris",
    )
    sncf_client = SncfClient(api_key="", mock_mode=True)

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot_data = {"config": config, "sncf_client": sncf_client}
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()

    await broadcast_commute_status(context, CommuteDirection.ANTIBES_TO_NICE)

    assert context.bot.send_message.await_count == 2
    sent_targets = {call.kwargs["chat_id"] for call in context.bot.send_message.await_args_list}
    assert sent_targets == {1001, 1002}
