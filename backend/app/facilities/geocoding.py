from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.core.exceptions import HealthLinkError


class FacilityAddressNotFoundError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__(
            "We could not match this facility address. Check the address, zila, and upazila, then try again.",
            status_code=422,
        )


class FacilityGeocoderUnavailableError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__(
            "Address matching is temporarily unavailable. The facility details are safe; try confirming its location again later.",
            status_code=503,
        )


@dataclass(frozen=True)
class GeocodedFacilityAddress:
    latitude: float
    longitude: float
    matched_address: str


def geocode_facility_address(
    *,
    address: str,
    district: str,
    upazila: str,
    settings: Settings,
) -> GeocodedFacilityAddress:
    query = f"{address}, {upazila}, {district}, Bangladesh"
    try:
        with httpx.Client(
            base_url=settings.geocoder_base_url.rstrip("/"),
            headers={"User-Agent": settings.geocoder_user_agent},
            timeout=8.0,
        ) as client:
            response = client.get(
                "/search",
                params={
                    "q": query,
                    "format": "jsonv2",
                    "countrycodes": "bd",
                    "limit": 1,
                },
            )
            response.raise_for_status()
            matches = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise FacilityGeocoderUnavailableError() from exc

    if not isinstance(matches, list) or not matches:
        raise FacilityAddressNotFoundError()
    try:
        latitude = float(matches[0]["lat"])
        longitude = float(matches[0]["lon"])
        matched_address = str(matches[0]["display_name"]).strip()
    except (KeyError, TypeError, ValueError) as exc:
        raise FacilityGeocoderUnavailableError() from exc
    if not 20 <= latitude <= 27 or not 88 <= longitude <= 93:
        raise FacilityAddressNotFoundError()
    return GeocodedFacilityAddress(
        latitude=latitude,
        longitude=longitude,
        matched_address=matched_address,
    )
