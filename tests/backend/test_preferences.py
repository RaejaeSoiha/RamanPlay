def test_household_preferences_sync_favorites_and_viewing_settings(client):
    account = client.get("/api/account/me").json()
    payload = {
        "favorites": [3, 1, 3],
        "preferences": {"timezone": "America/Denver", "showFree": True, "league": "NBA"},
    }

    saved = client.put(
        "/api/account/preferences",
        json=payload,
        headers={"X-CSRF-Token": account["csrf_token"]},
    )

    assert saved.status_code == 200
    assert saved.json()["favorites"] == [1, 3]
    assert client.get("/api/account/preferences").json()["preferences"] == payload["preferences"]
