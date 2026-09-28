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
            {
                # ZOU ! Train - should be included
                "nb_transfers": 0,
                "sections": [
                    {
                        "type": "public_transport",
                        "display_informations": {
                            "commercial_mode": "ZOU ! Train",
                            "network": "ZOU !",
                            "physical_mode": "Train",
                            "code": "86045",
                            "direction": "Nice-Ville",
                        },
                        "base_departure_date_time": "20260928T075000",
                        "departure_date_time": "20260928T075000",
                    }
                ],
            },
            {
                # Replacement Car ZOU! - should be excluded
                "nb_transfers": 0,
                "sections": [
                    {
                        "type": "public_transport",
                        "display_informations": {
                            "commercial_mode": "Car ZOU !",
                            "network": "ZOU !",
                            "physical_mode": "Bus",
                            "code": "BUS86047",
                            "direction": "Nice-Ville",
                        },
                        "base_departure_date_time": "20260928T080000",
                        "departure_date_time": "20260928T080000",
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

    assert len(status.departures) == 3  # TER + TER cancelled + ZOU! Train (TGV and Bus ignored)
    dep1 = status.departures[0]
    assert dep1.train_number == "86041"
    assert dep1.commercial_mode == "TER"
    assert dep1.delay_minutes == 10
    assert dep1.platform == "1"
    assert not dep1.is_cancelled

    dep2 = status.departures[1]
    assert dep2.train_number == "86043"
    assert dep2.is_cancelled is True

    dep3 = status.departures[2]
    assert dep3.train_number == "86045"
    assert dep3.commercial_mode == "ZOU ! Train"

    # Route-wide disruption is kept
    assert "Ralentissement important sur l'axe." in status.general_disruptions
    # Train-specific disruption is on dep1, NOT duplicated in general_disruptions
    assert "Retard de 10 min." in dep1.disruptions
    assert "Retard de 10 min." not in status.general_disruptions


def test_station_ids_and_stop_date_times_precedence():
    client = SncfClient(api_key="dummy", timezone="Europe/Paris")
    tz = ZoneInfo("Europe/Paris")
    query_time = datetime(2026, 9, 28, 7, 0, tzinfo=tz)

    assert CommuteDirection.ANTIBES_TO_NICE.origin_id == "stop_area:OCE:SA:87757674"
    assert CommuteDirection.ANTIBES_TO_NICE.destination_id == "stop_area:OCE:SA:87756056"

    # Simulate train that originated in Cannes earlier (e.g. 06:50), but departs Antibes at 07:15
    mock_data = {
        "journeys": [
            {
                "nb_transfers": 0,
                "sections": [
                    {
                        "type": "public_transport",
                        "display_informations": {
                            "commercial_mode": "TER",
                            "code": "86099",
                            "direction": "Nice-Ville",
                        },
                        "base_departure_date_time": "20260928T065000",  # Trip start in Cannes
                        "departure_date_time": "20260928T065000",
                        "stop_date_times": [
                            {
                                # Boarding stop call in Antibes
                                "stop_point": {"name": "Antibes", "platform_code": "2"},
                                "base_departure_date_time": "20260928T071500",
                                "departure_date_time": "20260928T072000",  # 5 min delay at Antibes
                            }
                        ],
                    }
                ],
            }
        ]
    }

    status = client._parse_journeys_response(
        mock_data,
        CommuteDirection.ANTIBES_TO_NICE,
        query_time,
        count=4,
    )
    assert len(status.departures) == 1
    dep = status.departures[0]
    # Must use Antibes boarding time (07:15 scheduled, 07:20 realtime), NOT Cannes 06:50
    assert dep.scheduled_departure.strftime("%H:%M") == "07:15"
    assert dep.realtime_departure.strftime("%H:%M") == "07:20"
    assert dep.delay_minutes == 5
    assert dep.platform == "2"
