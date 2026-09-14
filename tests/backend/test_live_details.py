from types import SimpleNamespace

from app.services.live_details import ESPNLiveDetailsProvider


def test_live_details_normalizes_espn_summary_without_exposing_raw_provider_data():
    payload = {
        "header": {
            "competitions": [{
                "status": {"period": 3, "displayClock": "04:22", "type": {"detail": "3rd Quarter"}},
                "competitors": [
                    {"id": "1", "team": {"abbreviation": "AAA"}},
                    {"id": "2", "team": {"abbreviation": "BBB"}},
                ],
            }]
        },
        "situation": {
            "possession": "2",
            "downDistanceText": "2nd & 4",
            "lastPlay": {"text": "Pass complete for 6 yards."},
        },
    }

    assert ESPNLiveDetailsProvider.normalize(payload) == {
        "status_detail": "3rd Quarter",
        "period": 3,
        "clock": "04:22",
        "possession": "BBB",
        "down_distance": "2nd & 4",
        "last_play": "Pass complete for 6 yards.",
    }


def test_live_details_returns_empty_for_unsupported_league_without_a_network_request():
    game = SimpleNamespace(league="UFC", external_id="espn-ufc-1")
    assert ESPNLiveDetailsProvider().get(game) == {}
