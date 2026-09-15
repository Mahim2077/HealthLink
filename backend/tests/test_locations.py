from __future__ import annotations

from app.facilities.geocoding import GeocodedFacilityAddress

from test_facility_verification_routes import admin_headers, facility_payload


def test_bangladesh_area_options_expose_names_without_coordinates(client) -> None:
    response = client.get("/api/v1/locations/bangladesh")
    assert response.status_code == 200
    body = response.json()
    assert len(body["districts"]) == 64
    assert len(body["upazilas"]) == 495
    assert {"code", "name", "name_bn"} == set(body["districts"][0])
    assert "latitude" not in response.text
    assert "longitude" not in response.text


def test_only_admin_can_confirm_facility_location_without_coordinate_leak(
    client, db_session, monkeypatch
) -> None:
    headers, _ = admin_headers(client, db_session)
    payload = facility_payload(
        district_code="BD3026",
        upazila_code="BD30260072",
        address="Savar Health Campus, Savar",
    )
    facility = client.post("/api/v1/admin/facilities", headers=headers, json=payload).json()
    endpoint = f"/api/v1/admin/facilities/{facility['id']}/confirm-location"
    assert client.post(endpoint, json={}).status_code == 401

    monkeypatch.setattr(
        "app.facilities.service.geocode_facility_address",
        lambda **_: GeocodedFacilityAddress(
            latitude=23.88,
            longitude=90.281,
            matched_address="Savar Health Campus, Savar, Dhaka, Bangladesh",
        ),
    )
    response = client.post(endpoint, headers=headers, json={})
    assert response.status_code == 200, response.text
    assert response.json()["facility"]["location_status"] == "CONFIRMED"
    assert "latitude" not in response.text
    assert "longitude" not in response.text
