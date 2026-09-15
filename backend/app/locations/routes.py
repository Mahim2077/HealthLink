from fastapi import APIRouter

from app.locations.schemas import BangladeshAreaOptions
from app.locations.service import list_area_options


router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/bangladesh", response_model=BangladeshAreaOptions)
def get_bangladesh_areas() -> BangladeshAreaOptions:
    """Return names and stable codes only; geographic coordinates stay server-side."""

    return list_area_options()
