import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from trainbot.sncf.client import SncfClient
from trainbot.sncf.models import CommuteDirection


@pytest.mark.asyncio
async def test_sncf_client_mock_mode():
    client = SncfClient(api_key="", timezone="Europe/Paris", mock_mode=True)
    status = await client.get_next_trains(CommuteDirection.ANTIBES_TO_NICE, count=4)

    assert status.direction == CommuteDirection.ANTIBES_TO_NICE
    assert len(status.departures) == 4
    # Ensure delay calculations exist
    assert any(d.delay_minutes > 0 for d in status.departures)
    assert any(d.is_cancelled for d in status.departures)


def test_sncf_response_parsing():
    client = SncfClient(api_key="dummy", timezone="Europe/Paris")
    tz = ZoneInfo("Europe/Paris")
    query_time = datetime(2026, 9, 28, 7, 0, tzinfo=tz)

    mock_raw_data = {
        "disruptions": [
            {"messages": [{"text": "Ralentissement important sur l'axe."}]}
        ],
        "journeys": [
            {
                "nb_transfers": 0,
                "status": "",
                "sections": [
                    {
                        "type": "public_transport",
                        "display_informations": {
                            "commercial_mode": "TER",
                            "code": "86041",
                            "direction": "Nice-Ville",
                        },
                        "base_departure_date_time": "20260928T071500",
                        "departure_date_time": "20260928T072500",  # 10 min delay
                        "from": {"stop_point": {"platform_code": "1"}},
                        "disruptions": [{"messages": [{"text": "Retard de 10 min."}]}],
                    }
                ],
            },
            {
                "nb_transfers": 0,
                "status": "NO_SERVICE",
                "sections": [
                    {
                        "type": "public_transport",
                        "display_informations": {
                            "commercial_mode": "TER",
                            "code": "86043",
                            "direction": "Vintimille",
                        },
                        "base_departure_date_time": "20260928T073000",
                        "departure_date_time": "20260928T073000",
                    }
                ],
            },
            {
                # TGV INOUI - should be filtered out
                "nb_transfers": 0,
                "sections": [
                    {
                        "type": "public_transport",
                        "display_informations": {
                            "commercial_mode": "TGV INOUI",
                            "code": "6801",
                            "direction": "Nice-Ville",
                        },
                        "base_departure_date_time": "20260928T074000",
                        "departure_date_time": "20260928T074000",
                    }
                ],
            },
        ],
    }

    status = client._parse_journeys_response(
        mock_raw_data,
        CommuteDirection.ANTIBES_TO_NICE,
        query_time,
        count=4,
    )

    assert len(status.departures) == 2  # Only 2 TER trains, TGV was ignored
    dep1 = status.departures[0]
    assert dep1.train_number == "86041"
    assert dep1.delay_minutes == 10
    assert dep1.platform == "1"
    assert not dep1.is_cancelled

    dep2 = status.departures[1]
    assert dep2.train_number == "86043"
    assert dep2.is_cancelled is True

    assert "Ralentissement important sur l'axe." in status.general_disruptions
