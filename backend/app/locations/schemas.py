from __future__ import annotations

from pydantic import BaseModel


class DistrictOption(BaseModel):
    code: str
    name: str
    name_bn: str


class UpazilaOption(BaseModel):
    code: str
    district_code: str
    name: str
    name_bn: str


class BangladeshAreaOptions(BaseModel):
    districts: list[DistrictOption]
    upazilas: list[UpazilaOption]
