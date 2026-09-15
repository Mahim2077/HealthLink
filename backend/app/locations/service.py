from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.exceptions import HealthLinkError
from app.locations.schemas import BangladeshAreaOptions, DistrictOption, UpazilaOption


DATA_DIRECTORY = Path(__file__).resolve().parent


class BangladeshAreaNotFoundError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("Select a valid Bangladesh zila and upazila.", status_code=422)


@dataclass(frozen=True)
class AreaPoint:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class AreaRecord:
    code: str
    name: str
    name_bn: str
    point: AreaPoint
    district_code: str | None = None


@lru_cache(maxsize=1)
def _records() -> tuple[dict[str, AreaRecord], dict[str, AreaRecord]]:
    districts_payload = json.loads(
        (DATA_DIRECTORY / "all-district.json").read_text(encoding="utf-8")
    )
    upazilas_payload = json.loads(
        (DATA_DIRECTORY / "all-upazila.json").read_text(encoding="utf-8")
    )
    districts = {
        row["id"]: AreaRecord(
            code=row["id"],
            name=row["name"]["en"],
            name_bn=row["name"]["local"],
            point=AreaPoint(float(row["geo"]["lat"]), float(row["geo"]["lon"])),
        )
        for row in districts_payload
    }
    upazilas = {
        row["id"]: AreaRecord(
            code=row["id"],
            name=row["name"]["en"],
            name_bn=row["name"]["local"],
            point=AreaPoint(float(row["geo"]["lat"]), float(row["geo"]["lon"])),
            district_code=row["parent"]["id"],
        )
        for row in upazilas_payload
    }
    return districts, upazilas


def list_area_options() -> BangladeshAreaOptions:
    districts, upazilas = _records()
    return BangladeshAreaOptions(
        districts=[
            DistrictOption(code=row.code, name=row.name, name_bn=row.name_bn)
            for row in sorted(districts.values(), key=lambda item: item.name)
        ],
        upazilas=[
            UpazilaOption(
                code=row.code,
                district_code=row.district_code or "",
                name=row.name,
                name_bn=row.name_bn,
            )
            for row in sorted(
                upazilas.values(), key=lambda item: (item.district_code or "", item.name)
            )
        ],
    )


def resolve_area(district_code: str, upazila_code: str) -> tuple[AreaRecord, AreaRecord]:
    districts, upazilas = _records()
    district = districts.get(district_code)
    upazila = upazilas.get(upazila_code)
    if district is None or upazila is None or upazila.district_code != district.code:
        raise BangladeshAreaNotFoundError()
    return district, upazila
