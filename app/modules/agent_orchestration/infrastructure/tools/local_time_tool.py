"""Local time for a place — geocode (geopy) + IANA zone (timezonefinder), no web search."""

from __future__ import annotations

import logging
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.modules.agent_orchestration.infrastructure.tools.base_tool import ProjectBaseTool

if TYPE_CHECKING:
    from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)


class _LocalTimeInput(BaseModel):
    place: str = Field(
        description=(
            "City, region, or address to resolve (e.g. 'Tokyo', 'Austin, Texas, USA'). "
            "Add country for ambiguous names."
        )
    )


@lru_cache(maxsize=1)
def _timezone_finder() -> TimezoneFinder:
    from timezonefinder import TimezoneFinder as _TF

    return _TF()


class GetLocalTimeTool(ProjectBaseTool):
    """Resolves a place to coordinates, maps to IANA timezone, returns local time."""

    name: str = "get_local_time"
    description: str = (
        "Get the current local date and time for a geographic place. Uses offline timezone "
        "boundaries plus one geocoding lookup (not a web search). Prefer this over web_search "
        "for questions like 'what time is it in Paris?' or 'current time in Tokyo'."
    )
    args_schema: type[BaseModel] = _LocalTimeInput

    user_agent: str = Field(exclude=True, repr=False)

    def _execute(self, place: str, **_: Any) -> str:
        from geopy.exc import GeocoderServiceError, GeocoderTimedOut
        from geopy.geocoders import Nominatim

        place = place.strip()
        if not place:
            return "Provide a non-empty place name."

        geolocator = Nominatim(user_agent=self.user_agent, timeout=10)
        try:
            location = geolocator.geocode(place)
        except (GeocoderTimedOut, GeocoderServiceError) as exc:
            logger.warning("Geocoder error for place=%r: %s", place, exc)
            return (
                "Geocoding failed (service timeout or error). Try again, or spell the place "
                f"with region/country. Detail: {exc}"
            )

        if location is None:
            return (
                f"No coordinates found for {place!r}. Try a fuller address or add the country."
            )

        lat = float(location.latitude)
        lng = float(location.longitude)
        tz_name = _timezone_finder().timezone_at(lng=lng, lat=lat)

        if not tz_name:
            return (
                f"Resolved {location.address} to ({lat:.4f}, {lng:.4f}), but no IANA timezone "
                "covers that point (e.g. open ocean). Try a nearby city on land."
            )

        now = datetime.now(ZoneInfo(tz_name))
        label = location.address or place
        return (
            f"Place: {label}\n"
            f"Coordinates (WGS84): lat={lat:.6f}, lon={lng:.6f}\n"
            f"IANA timezone: {tz_name}\n"
            f"Local date/time: {now.isoformat(timespec='seconds')}"
        )
