#!/usr/bin/env python3
"""
BriefSteve
Cross-platform morning brief generator for Windows, Linux, and macOS.

Python 3.11+

Install:
    python3 -m pip install requests feedparser astral tzdata

Optional Google Calendar support:
    python3 -m pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

Run:
    python3 briefsteve.py --no-calendar
    python3: briefsteve.py --output morning-brief.md
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import math
import random
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import feedparser
import requests
from astral import Observer
from astral.moon import moonrise, moonset, phase


# =============================================================================
# Configuration
# =============================================================================

APP_NAME = "BriefSteve"
APP_VERSION = "2.0.0"

CITY = "Chapel Hill"
STATE = "NC"
LATITUDE = 35.9132
LONGITUDE = -79.0558
TIMEZONE_NAME = "America/New_York"

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

HTTP_TIMEOUT_SECONDS = 20

USER_AGENT = (
    f"{APP_NAME}/{APP_VERSION} "
    "(personal morning brief generator)"
)

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
]

NEWS_FEEDS = {
    "Global Security": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ],
    "General News": [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://feeds.npr.org/1001/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    ],
    "Tech/DevOps": [
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
        "https://github.blog/feed/",
        "https://www.nasa.gov/feed/",
    ],
}

SECURITY_KEYWORDS = {
    "war",
    "military",
    "missile",
    "attack",
    "conflict",
    "unrest",
    "ceasefire",
    "airstrike",
    "invasion",
    "troops",
    "defense",
    "security",
    "nuclear",
    "sanctions",
    "protest",
    "coup",
    "border",
    "terror",
    "hostage",
}

TECH_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "model",
    "openai",
    "anthropic",
    "gemini",
    "llama",
    "spacex",
    "starship",
    "ces",
    "devops",
    "docker",
    "kubernetes",
    "github",
    "python",
    "linux",
    "cloud",
    "security",
    "developer",
    "programming",
    "software",
}


# =============================================================================
# Time zone
# =============================================================================

def load_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(TIMEZONE_NAME)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(
            f"Time zone data for {TIMEZONE_NAME!r} is unavailable.\n"
            "Install it with:\n"
            "    python -m pip install tzdata"
        ) from exc


LOCAL_TIMEZONE = load_timezone()
UTC = ZoneInfo("UTC")


# =============================================================================
# Data classes
# =============================================================================

@dataclass(slots=True)
class DailyForecast:
    day: date
    minimum_f: float
    maximum_f: float
    weather_code: int
    precipitation_probability: int
    sunrise: datetime
    sunset: datetime


@dataclass(slots=True)
class WeatherReport:
    current_temperature_f: float
    apparent_temperature_f: float
    weather_code: int
    wind_speed_mph: float
    forecasts: list[DailyForecast]


@dataclass(slots=True)
class AirQualityReport:
    us_aqi: int | None
    pm25: float | None
    ozone: float | None


@dataclass(slots=True)
class LunarReport:
    phase_name: str
    illumination_percent: int
    moonrise: datetime | None
    moonset: datetime | None


@dataclass(slots=True)
class CalendarEvent:
    start: datetime
    end: datetime | None
    title: str
    all_day: bool


@dataclass(slots=True)
class NewsItem:
    title: str
    summary: str
    link: str
    published: datetime | None


# =============================================================================
# Exceptions
# =============================================================================

class BriefSteveError(RuntimeError):
    """Expected application error."""


# =============================================================================
# Formatting helpers
# =============================================================================

def format_date_long(value: date) -> str:
    """
    Cross-platform replacement for strftime('%B %-d, %Y').

    %-d is unsupported on Windows.
    """
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def format_clock(value: datetime | None) -> str:
    """
    Cross-platform replacement for strftime('%-I:%M %p').

    %-I is unsupported on Windows.
    """
    if value is None:
        return "Not available"

    local_value = value.astimezone(LOCAL_TIMEZONE)
    return local_value.strftime("%I:%M %p").lstrip("0")


def clean_html(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def shorten(text: str, limit: int = 220) -> str:
    cleaned = clean_html(text)

    if len(cleaned) <= limit:
        return cleaned

    shortened = cleaned[: limit - 1].rsplit(" ", 1)[0]
    return shortened + "…"


def escape_markdown(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


# =============================================================================
# HTTP
# =============================================================================

def get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(
            url,
            params=params,
            timeout=HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise BriefSteveError(
            f"Network request failed for {url}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise BriefSteveError(
            f"Invalid JSON returned by {url}"
        ) from exc

    if not isinstance(payload, dict):
        raise BriefSteveError(
            f"Unexpected response format from {url}"
        )

    return payload


# =============================================================================
# Weather
# =============================================================================

WEATHER_DESCRIPTIONS = {
    0: "clear",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "foggy with rime",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "freezing drizzle",
    57: "heavy freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light showers",
    81: "showers",
    82: "heavy showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorms",
    96: "thunderstorms with hail",
    99: "severe thunderstorms with hail",
}


def weather_description(code: int) -> str:
    return WEATHER_DESCRIPTIONS.get(
        code,
        "variable conditions",
    )


def parse_local_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TIMEZONE)

    return parsed.astimezone(LOCAL_TIMEZONE)


def fetch_weather() -> WeatherReport:
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE_NAME,
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "forecast_days": 7,
        "current": ",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "weather_code",
                "wind_speed_10m",
            ]
        ),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "sunrise",
                "sunset",
            ]
        ),
    }

    payload = get_json(WEATHER_URL, params)
    current = payload.get("current", {})
    daily = payload.get("daily", {})

    required_keys = [
        "time",
        "temperature_2m_min",
        "temperature_2m_max",
        "weather_code",
        "precipitation_probability_max",
        "sunrise",
        "sunset",
    ]

    for key in required_keys:
        if not daily.get(key):
            raise BriefSteveError(
                f"Weather response is missing daily field: {key}"
            )

    length = min(
        len(daily[key])
        for key in required_keys
    )

    forecasts: list[DailyForecast] = []

    for index in range(length):
        forecasts.append(
            DailyForecast(
                day=date.fromisoformat(daily["time"][index]),
                minimum_f=float(
                    daily["temperature_2m_min"][index]
                ),
                maximum_f=float(
                    daily["temperature_2m_max"][index]
                ),
                weather_code=int(
                    daily["weather_code"][index]
                ),
                precipitation_probability=int(
                    daily["precipitation_probability_max"][index] or 0
                ),
                sunrise=parse_local_datetime(
                    daily["sunrise"][index]
                ),
                sunset=parse_local_datetime(
                    daily["sunset"][index]
                ),
            )
        )

    if not forecasts:
        raise BriefSteveError(
            "Weather service returned no forecasts."
        )

    return WeatherReport(
        current_temperature_f=float(
            current.get("temperature_2m", 0)
        ),
        apparent_temperature_f=float(
            current.get("apparent_temperature", 0)
        ),
        weather_code=int(
            current.get("weather_code", 0)
        ),
        wind_speed_mph=float(
            current.get("wind_speed_10m", 0)
        ),
        forecasts=forecasts,
    )


def fetch_air_quality() -> AirQualityReport:
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE_NAME,
        "forecast_days": 1,
        "current": "us_aqi,pm2_5,ozone",
    }

    payload = get_json(AIR_QUALITY_URL, params)
    current = payload.get("current", {})

    return AirQualityReport(
        us_aqi=safe_int(current.get("us_aqi")),
        pm25=safe_float(current.get("pm2_5")),
        ozone=safe_float(current.get("ozone")),
    )


def aqi_label(aqi: int | None) -> str:
    if aqi is None:
        return "Unavailable"
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for sensitive groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very unhealthy"
    return "Hazardous"


def detected_advisories(
    weather: WeatherReport,
    air_quality: AirQualityReport,
) -> list[str]:
    advisories: list[str] = []
    today = weather.forecasts[0]

    if weather.apparent_temperature_f >= 105:
        advisories.append("dangerous heat conditions")
    elif weather.apparent_temperature_f >= 95:
        advisories.append("elevated heat risk")

    if today.weather_code in {95, 96, 99}:
        advisories.append("thunderstorm risk")

    if today.precipitation_probability >= 70:
        advisories.append("high rain probability")

    if weather.wind_speed_mph >= 30:
        advisories.append("strong winds")

    if air_quality.us_aqi is not None and air_quality.us_aqi > 100:
        advisories.append(
            "unhealthy air for sensitive groups"
        )

    return advisories


def activity_recommendations(
    weather: WeatherReport,
    air_quality: AirQualityReport,
) -> tuple[str, str]:
    today = weather.forecasts[0]

    commute: list[str] = []
    outdoor: list[str] = []

    if today.precipitation_probability >= 60:
        commute.append(
            "Allow extra travel time and carry rain gear"
        )
    else:
        commute.append(
            "Normal travel conditions are likely"
        )

    if today.weather_code in {95, 96, 99}:
        commute.append(
            "watch for lightning and avoid flooded roads"
        )

    if weather.apparent_temperature_f >= 95:
        commute.append(
            "do not leave people or pets in parked vehicles"
        )

    if weather.apparent_temperature_f >= 95:
        outdoor.append(
            "Exercise early, hydrate, and take cooling breaks"
        )
    else:
        outdoor.append(
            "Conditions are generally suitable for outdoor activity"
        )

    if today.precipitation_probability >= 50:
        outdoor.append(
            "keep an indoor backup plan"
        )

    if today.weather_code in {95, 96, 99}:
        outdoor.append(
            "go indoors when thunder is heard"
        )

    if air_quality.us_aqi is not None and air_quality.us_aqi > 100:
        outdoor.append(
            "sensitive groups should limit prolonged exertion"
        )

    return (
        "; ".join(commute) + ".",
        "; ".join(outdoor) + ".",
    )


# =============================================================================
# Lunar information
# =============================================================================

def moon_phase_name(phase_value: float) -> str:
    if phase_value < 1.75:
        return "New Moon"
    if phase_value < 5.25:
        return "Waxing Crescent"
    if phase_value < 8.75:
        return "First Quarter"
    if phase_value < 12.25:
        return "Waxing Gibbous"
    if phase_value < 15.75:
        return "Full Moon"
    if phase_value < 19.25:
        return "Waning Gibbous"
    if phase_value < 22.75:
        return "Last Quarter"
    if phase_value < 26.25:
        return "Waning Crescent"
    return "New Moon"


def approximate_illumination(phase_value: float) -> int:
    angle = 2 * math.pi * phase_value / 28
    fraction = (1 - math.cos(angle)) / 2
    return round(fraction * 100)


def fetch_lunar_report(
    target_date: date,
) -> LunarReport:
    observer = Observer(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        elevation=0,
    )

    phase_value = phase(target_date)

    try:
        rise = moonrise(
            observer=observer,
            date=target_date,
            tzinfo=LOCAL_TIMEZONE,
        )
    except ValueError:
        rise = None

    try:
        setting = moonset(
            observer=observer,
            date=target_date,
            tzinfo=LOCAL_TIMEZONE,
        )
    except ValueError:
        setting = None

    return LunarReport(
        phase_name=moon_phase_name(phase_value),
        illumination_percent=approximate_illumination(
            phase_value
        ),
        moonrise=rise,
        moonset=setting,
    )


# =============================================================================
# Religious calendar
# =============================================================================

EPISCOPAL_FIXED_OBSERVANCES = {
    (1, 18): "The Confession of Saint Peter the Apostle",
    (1, 25): "The Conversion of Saint Paul the Apostle",
    (2, 2): "The Presentation of Our Lord Jesus Christ",
    (3, 19): "Saint Joseph",
    (3, 25): "The Annunciation of Our Lord Jesus Christ",
    (4, 25): "Saint Mark the Evangelist",
    (5, 1): "Saint Philip and Saint James, Apostles",
    (5, 31): "The Visitation of the Blessed Virgin Mary",
    (6, 11): "Saint Barnabas the Apostle",
    (6, 24): "The Nativity of Saint John the Baptist",
    (6, 29): "Saint Peter and Saint Paul, Apostles",
    (7, 22): "Saint Mary Magdalene",
    (7, 25): "Saint James the Apostle",
    (8, 6): "The Transfiguration of Our Lord Jesus Christ",
    (8, 15): "Saint Mary the Virgin",
    (8, 24): "Saint Bartholomew the Apostle",
    (9, 14): "Holy Cross Day",
    (9, 21): "Saint Matthew, Apostle and Evangelist",
    (9, 29): "Saint Michael and All Angels",
    (10, 18): "Saint Luke the Evangelist",
    (10, 28): "Saint Simon and Saint Jude, Apostles",
    (11, 1): "All Saints’ Day",
    (11, 30): "Saint Andrew the Apostle",
    (12, 21): "Saint Thomas the Apostle",
    (12, 25): "The Nativity of Our Lord Jesus Christ",
    (12, 26): "Saint Stephen, Deacon and Martyr",
    (12, 27): "Saint John, Apostle and Evangelist",
    (12, 28): "The Holy Innocents",
}

CATHOLIC_FIXED_OBSERVANCES = {
    (1, 1): "Mary, the Holy Mother of God",
    (1, 25): "The Conversion of Saint Paul the Apostle",
    (2, 2): "The Presentation of the Lord",
    (2, 22): "The Chair of Saint Peter the Apostle",
    (3, 19): "Saint Joseph, Spouse of the Blessed Virgin Mary",
    (3, 25): "The Annunciation of the Lord",
    (4, 25): "Saint Mark, Evangelist",
    (5, 1): "Saint Joseph the Worker",
    (5, 3): "Saints Philip and James, Apostles",
    (5, 31): "The Visitation of the Blessed Virgin Mary",
    (6, 24): "The Nativity of Saint John the Baptist",
    (6, 29): "Saints Peter and Paul, Apostles",
    (7, 3): "Saint Thomas, Apostle",
    (7, 22): "Saint Mary Magdalene",
    (7, 25): "Saint James, Apostle",
    (8, 6): "The Transfiguration of the Lord",
    (8, 10): "Saint Lawrence, Deacon and Martyr",
    (8, 15): "The Assumption of the Blessed Virgin Mary",
    (8, 24): "Saint Bartholomew, Apostle",
    (9, 8): "The Nativity of the Blessed Virgin Mary",
    (9, 14): "The Exaltation of the Holy Cross",
    (9, 21): "Saint Matthew, Apostle and Evangelist",
    (9, 29): "Saints Michael, Gabriel and Raphael, Archangels",
    (10, 18): "Saint Luke, Evangelist",
    (10, 28): "Saints Simon and Jude, Apostles",
    (11, 1): "All Saints",
    (11, 2): "The Commemoration of All the Faithful Departed",
    (11, 30): "Saint Andrew, Apostle",
    (12, 8): "The Immaculate Conception of the Blessed Virgin Mary",
    (12, 25): "The Nativity of the Lord",
    (12, 26): "Saint Stephen, the First Martyr",
    (12, 27): "Saint John, Apostle and Evangelist",
    (12, 28): "The Holy Innocents, Martyrs",
}


def gregorian_easter(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 100
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    length = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * length) // 451
    month = (h + length - 7 * m + 114) // 31
    day = ((h + length - 7 * m + 114) % 31) + 1

    return date(year, month, day)


def first_advent_sunday(year: int) -> date:
    christmas = date(year, 12, 25)

    for days_before in range(22, 29):
        candidate = christmas - timedelta(
            days=days_before
        )

        if candidate.weekday() == 6:
            return candidate

    raise BriefSteveError(
        f"Could not calculate Advent for {year}."
    )


def liturgical_season(
    target_date: date,
) -> tuple[str, str]:
    easter = gregorian_easter(target_date.year)
    ash_wednesday = easter - timedelta(days=46)
    palm_sunday = easter - timedelta(days=7)
    pentecost = easter + timedelta(days=49)
    advent = first_advent_sunday(target_date.year)

    christmas = date(target_date.year, 12, 25)
    epiphany = date(target_date.year, 1, 6)

    if target_date >= christmas or target_date < epiphany:
        return "Christmas", "white"

    if epiphany <= target_date < ash_wednesday:
        return "Season after Epiphany / Ordinary Time", "green"

    if ash_wednesday <= target_date < palm_sunday:
        return "Lent", "purple"

    if palm_sunday <= target_date < easter:
        return "Holy Week", "red or purple"

    if easter <= target_date <= pentecost:
        if target_date == pentecost:
            return "Pentecost", "red"

        return "Easter", "white"

    if pentecost < target_date < advent:
        return "Season after Pentecost / Ordinary Time", "green"

    if advent <= target_date < christmas:
        return "Advent", "purple or blue"

    return "Ordinary Time", "green"


def religious_observances(
    target_date: date,
) -> dict[str, str]:
    season, normal_color = liturgical_season(
        target_date
    )

    key = (
        target_date.month,
        target_date.day,
    )

    episcopal = EPISCOPAL_FIXED_OBSERVANCES.get(
        key,
        f"Weekday in the {season}",
    )

    catholic = CATHOLIC_FIXED_OBSERVANCES.get(
        key,
        f"Weekday in {season}",
    )

    color = normal_color
    combined = f"{episcopal} {catholic}".lower()

    if any(
        word in combined
        for word in [
            "martyr",
            "apostle",
            "evangelist",
        ]
    ):
        color = "red"
    elif any(
        word in combined
        for word in [
            "mary",
            "joseph",
            "all saints",
            "presentation",
            "annunciation",
            "transfiguration",
            "nativity",
            "assumption",
        ]
    ):
        color = "white"

    return {
        "season": season,
        "episcopal": episcopal,
        "catholic": catholic,
        "color": color,
    }


# =============================================================================
# Google Calendar
# =============================================================================

def parse_google_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TIMEZONE)

    return parsed.astimezone(LOCAL_TIMEZONE)


def fetch_calendar_events(
    target_date: date,
    credentials_file: Path,
    token_file: Path,
) -> list[CalendarEvent]:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise BriefSteveError(
            "Google Calendar packages are not installed.\n"
            "Install them with:\n"
            "    python -m pip install "
            "google-api-python-client "
            "google-auth-httplib2 "
            "google-auth-oauthlib"
        ) from exc

    credentials = None

    if token_file.exists():
        try:
            credentials = (
                Credentials.from_authorized_user_file(
                    str(token_file),
                    GOOGLE_SCOPES,
                )
            )
        except (ValueError, json.JSONDecodeError) as exc:
            logging.warning(
                "Ignoring invalid token file %s: %s",
                token_file,
                exc,
            )

    if not credentials or not credentials.valid:
        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):
            credentials.refresh(Request())
        else:
            if not credentials_file.exists():
                raise BriefSteveError(
                    f"Google OAuth credentials file not found: "
                    f"{credentials_file}"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_file),
                GOOGLE_SCOPES,
            )

            credentials = flow.run_local_server(
                port=0
            )

        token_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        token_file.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    service = build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    day_start = datetime.combine(
        target_date,
        time.min,
        LOCAL_TIMEZONE,
    )

    day_end = day_start + timedelta(days=1)

    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events: list[CalendarEvent] = []

    for item in result.get("items", []):
        start_data = item.get("start", {})
        end_data = item.get("end", {})
        title = item.get(
            "summary",
            "(Untitled event)",
        )

        if "dateTime" in start_data:
            start_value = parse_google_datetime(
                start_data["dateTime"]
            )

            end_value = None

            if end_data.get("dateTime"):
                end_value = parse_google_datetime(
                    end_data["dateTime"]
                )

            all_day = False
        elif "date" in start_data:
            start_value = datetime.combine(
                date.fromisoformat(start_data["date"]),
                time.min,
                LOCAL_TIMEZONE,
            )

            end_value = None
            all_day = True
        else:
            logging.warning(
                "Skipping calendar event with no start date: %r",
                item,
            )
            continue

        events.append(
            CalendarEvent(
                start=start_value,
                end=end_value,
                title=title,
                all_day=all_day,
            )
        )

    events.sort(
        key=lambda event: event.start
    )

    return events


# =============================================================================
# News
# =============================================================================

def parse_feed_date(entry: Any) -> datetime | None:
    parsed = getattr(
        entry,
        "published_parsed",
        None,
    )

    if parsed is None:
        parsed = getattr(
            entry,
            "updated_parsed",
            None,
        )

    if parsed is None:
        return None

    try:
        return datetime(
            parsed.tm_year,
            parsed.tm_mon,
            parsed.tm_mday,
            parsed.tm_hour,
            parsed.tm_min,
            parsed.tm_sec,
            tzinfo=UTC,
        )
    except (AttributeError, TypeError, ValueError):
        return None


def fetch_feed_items(
    url: str,
) -> list[NewsItem]:
    parsed = feedparser.parse(
        url,
        request_headers={
            "User-Agent": USER_AGENT,
        },
    )

    if getattr(parsed, "bozo", False):
        logging.warning(
            "RSS issue for %s: %s",
            url,
            parsed.get("bozo_exception"),
        )

    items: list[NewsItem] = []

    for entry in parsed.entries[:30]:
        title = clean_html(
            entry.get("title", "Untitled")
        )

        summary = clean_html(
            entry.get("summary")
            or entry.get("description")
            or title
        )

        link = entry.get("link", "")

        items.append(
            NewsItem(
                title=title,
                summary=shorten(summary),
                link=link,
                published=parse_feed_date(entry),
            )
        )

    return items


def normalize_title(title: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        title.lower(),
    ).strip()


def deduplicate_news(
    items: list[NewsItem],
) -> list[NewsItem]:
    unique: list[NewsItem] = []
    seen: set[str] = set()

    for item in items:
        normalized = normalize_title(
            item.title
        )

        signature = " ".join(
            normalized.split()[:8]
        )

        if not signature or signature in seen:
            continue

        seen.add(signature)
        unique.append(item)

    return unique


def keyword_score(
    item: NewsItem,
    keywords: set[str],
) -> int:
    searchable = (
        f"{item.title} {item.summary}".lower()
    )

    return sum(
        1
        for keyword in keywords
        if keyword in searchable
    )


def published_sort_value(
    item: NewsItem,
) -> datetime:
    return item.published or datetime.min.replace(
        tzinfo=UTC
    )


def fetch_news() -> dict[str, list[NewsItem]]:
    result: dict[str, list[NewsItem]] = {}

    for section, feeds in NEWS_FEEDS.items():
        items: list[NewsItem] = []

        for feed_url in feeds:
            try:
                items.extend(
                    fetch_feed_items(feed_url)
                )
            except Exception as exc:
                logging.warning(
                    "Could not load RSS feed %s: %s",
                    feed_url,
                    exc,
                )

        items = deduplicate_news(items)

        if section == "Global Security":
            matching = [
                item
                for item in items
                if keyword_score(
                    item,
                    SECURITY_KEYWORDS,
                ) > 0
            ]

            matching.sort(
                key=lambda item: (
                    keyword_score(
                        item,
                        SECURITY_KEYWORDS,
                    ),
                    published_sort_value(item),
                ),
                reverse=True,
            )

            result[section] = matching[:3]

        elif section == "Tech/DevOps":
            items.sort(
                key=lambda item: (
                    keyword_score(
                        item,
                        TECH_KEYWORDS,
                    ),
                    published_sort_value(item),
                ),
                reverse=True,
            )

            result[section] = items[:5]

        else:
            items.sort(
                key=published_sort_value,
                reverse=True,
            )

            result[section] = items[:3]

    return result


# =============================================================================
# Coding tips
# =============================================================================

CODING_TIPS = [
    (
        "Python",
        "Use pathlib.Path instead of manually joining filesystem paths.",
        """
from pathlib import Path

config_file = Path.home() / ".config" / "briefsteve" / "config.json"
config_file.parent.mkdir(parents=True, exist_ok=True)
""",
    ),
    (
        "Bash",
        "Use strict mode so automation failures do not pass silently.",
        """
#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "Failed on line $LINENO" >&2' ERR
""",
    ),
    (
        "Python",
        "Always give network requests an explicit timeout.",
        """
response = requests.get(
    "https://example.com/api",
    timeout=20,
)
response.raise_for_status()
""",
    ),
    (
        "DevOps",
        "Write generated files atomically so partial output is not left behind.",
        """
from pathlib import Path

output_file = Path("brief.md")
temporary_file = output_file.with_suffix(".tmp")

temporary_file.write_text(rendered_brief, encoding="utf-8")
temporary_file.replace(output_file)
""",
    ),
]


def coding_tip(
    target_date: date,
) -> tuple[str, str, str]:
    generator = random.Random(
        target_date.toordinal()
    )

    return generator.choice(
        CODING_TIPS
    )


# =============================================================================
# Rendering
# =============================================================================

def render_weather(
    weather: WeatherReport,
    air_quality: AirQualityReport,
) -> str:
    today = weather.forecasts[0]
    commute, outdoor = activity_recommendations(
        weather,
        air_quality,
    )

    advisories = detected_advisories(
        weather,
        air_quality,
    )

    advisory_text = (
        ", ".join(advisories).capitalize()
        if advisories
        else "No automated hazards detected"
    )

    forecast_line = " · ".join(
        (
            f"**{forecast.day.strftime('%a')}**: "
            f"{forecast.minimum_f:.0f}–"
            f"{forecast.maximum_f:.0f}°F, "
            f"{weather_description(forecast.weather_code)}"
        )
        for forecast in weather.forecasts
    )

    aqi_text = aqi_label(
        air_quality.us_aqi
    )

    if air_quality.us_aqi is not None:
        aqi_text += (
            f" — AQI {air_quality.us_aqi}"
        )

    return "\n".join(
        [
            "## Weather & Outlook",
            "",
            (
                f"**Summary:** "
                f"{weather_description(today.weather_code).capitalize()}, "
                f"**{today.minimum_f:.0f}–"
                f"{today.maximum_f:.0f}°F**. "
                f"Currently "
                f"{weather.current_temperature_f:.0f}°F; "
                f"feels like "
                f"{weather.apparent_temperature_f:.0f}°F."
            ),
            "",
            f"**Sunrise:** {format_clock(today.sunrise)}  ",
            f"**Sunset:** {format_clock(today.sunset)}",
            "",
            (
                f"**Air quality:** {aqi_text}. "
                f"**Advisories:** {advisory_text}."
            ),
            "",
            f"**Commute:** {commute}",
            "",
            f"**Outdoor activity:** {outdoor}",
            "",
            f"**Upcoming week:** {forecast_line}",
        ]
    )


def render_lunar(
    lunar: LunarReport,
) -> str:
    return "\n".join(
        [
            "## Lunar Status",
            "",
            f"**Phase:** {lunar.phase_name}  ",
            (
                f"**Illumination:** approximately "
                f"{lunar.illumination_percent}%  "
            ),
            f"**Moonrise:** {format_clock(lunar.moonrise)}  ",
            f"**Moonset:** {format_clock(lunar.moonset)}",
        ]
    )


def render_religious(
    target_date: date,
) -> str:
    report = religious_observances(
        target_date
    )

    return "\n".join(
        [
            "## Religious Calendar",
            "",
            (
                f"**Liturgical season:** "
                f"{report['season']}"
            ),
            "",
            (
                f"**Episcopal:** "
                f"{report['episcopal']}"
            ),
            "",
            (
                f"**Roman Catholic:** "
                f"{report['catholic']}"
            ),
            "",
            (
                f"**Liturgical color:** "
                f"{report['color'].capitalize()}"
            ),
            "",
            (
                "_Local, diocesan, national, transferred, and "
                "movable observances may supersede this "
                "built-in calendar._"
            ),
        ]
    )


def render_calendar(
    events: list[CalendarEvent] | None,
    calendar_error: str | None,
) -> str:
    lines = [
        "## Calendar",
        "",
    ]

    if calendar_error:
        lines.append(
            f"Calendar unavailable: {calendar_error}"
        )
        return "\n".join(lines)

    if not events:
        lines.append(
            "Your calendar is clear today."
        )
        return "\n".join(lines)

    for event in events:
        if event.all_day:
            when = "All day"
        elif event.end is not None:
            when = (
                f"{format_clock(event.start)}–"
                f"{format_clock(event.end)}"
            )
        else:
            when = format_clock(event.start)

        lines.append(
            f"- **{when}:** "
            f"{escape_markdown(event.title)}"
        )

    return "\n".join(lines)


def render_news(
    news: dict[str, list[NewsItem]],
) -> str:
    lines = [
        "## News Digest",
        "",
    ]

    for section in [
        "Global Security",
        "General News",
        "Tech/DevOps",
    ]:
        lines.append(
            f"### {section}"
        )
        lines.append("")

        items = news.get(
            section,
            [],
        )

        if not items:
            lines.append(
                "- **No matching headlines were available.**"
            )
        else:
            for item in items:
                title = escape_markdown(
                    item.title
                )

                summary = escape_markdown(
                    shorten(item.summary)
                )

                if item.link:
                    lines.append(
                        f"- **[{title}]({item.link})** — "
                        f"{summary}"
                    )
                else:
                    lines.append(
                        f"- **{title}** — {summary}"
                    )

        lines.append("")

    return "\n".join(lines).rstrip()


def render_tip(
    target_date: date,
) -> str:
    category, explanation, example = coding_tip(
        target_date
    )

    language = {
        "Python": "python",
        "Bash": "bash",
        "DevOps": "python",
    }.get(category, "text")

    return "\n".join(
        [
            "## Tech Recommendations",
            "",
            (
                f"**Coding Tip of the Day — "
                f"{category}:** {explanation}"
            ),
            "",
            f"```{language}",
            example.strip(),
            "```",
        ]
    )


def build_brief(
    target_date: date,
    weather: WeatherReport,
    air_quality: AirQualityReport,
    lunar: LunarReport,
    calendar_events: list[CalendarEvent] | None,
    calendar_error: str | None,
    news: dict[str, list[NewsItem]],
) -> str:
    sections = [
        (
            "# Your daily morning brief for "
            f"{format_date_long(target_date)}"
        ),
        render_weather(
            weather,
            air_quality,
        ),
        render_lunar(lunar),
        render_religious(target_date),
        render_calendar(
            calendar_events,
            calendar_error,
        ),
        render_news(news),
        render_tip(target_date),
    ]

    return "\n\n---\n\n".join(
        sections
    ) + "\n"


# =============================================================================
# Command-line arguments
# =============================================================================

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a BriefSteve-style "
            "daily morning brief."
        )
    )

    parser.add_argument(
        "--date",
        help=(
            "Brief date in YYYY-MM-DD format. "
            "Defaults to today."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Write the brief to a Markdown file "
            "instead of standard output."
        ),
    )

    parser.add_argument(
        "--no-calendar",
        action="store_true",
        help="Disable Google Calendar.",
    )

    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("credentials.json"),
        help=(
            "Google OAuth desktop credentials file."
        ),
    )

    parser.add_argument(
        "--token",
        type=Path,
        default=Path("token.json"),
        help="Google OAuth token cache file.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable diagnostic logging.",
    )

    return parser.parse_args()


def parse_target_date(
    value: str | None,
) -> date:
    if value is None:
        return datetime.now(
            LOCAL_TIMEZONE
        ).date()

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise BriefSteveError(
            f"Invalid date {value!r}. "
            "Use YYYY-MM-DD."
        ) from exc


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=(
            logging.DEBUG
            if args.verbose
            else logging.WARNING
        ),
        format="%(levelname)s: %(message)s",
    )

    try:
        target_date = parse_target_date(
            args.date
        )

        weather = fetch_weather()
        air_quality = fetch_air_quality()
        lunar = fetch_lunar_report(
            target_date
        )

        calendar_events: list[CalendarEvent] | None = None
        calendar_error: str | None = None

        if not args.no_calendar:
            try:
                calendar_events = fetch_calendar_events(
                    target_date=target_date,
                    credentials_file=args.credentials,
                    token_file=args.token,
                )
            except BriefSteveError as exc:
                calendar_error = str(exc)

        news = fetch_news()

        brief = build_brief(
            target_date=target_date,
            weather=weather,
            air_quality=air_quality,
            lunar=lunar,
            calendar_events=calendar_events,
            calendar_error=calendar_error,
            news=news,
        )

        if args.output is not None:
            args.output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temporary_file = (
                args.output.parent
                / f"{args.output.name}.tmp"
            )

            temporary_file.write_text(
                brief,
                encoding="utf-8",
            )

            temporary_file.replace(
                args.output
            )

            print(
                f"Wrote {args.output.resolve()}"
            )
        else:
            try:
                print(brief, end="")
            except UnicodeEncodeError:
                encoded = brief.encode(
                    sys.stdout.encoding or "utf-8",
                    errors="replace",
                )
                sys.stdout.buffer.write(encoded)

        return 0

    except BriefSteveError as exc:
        logging.error("%s", exc)
        return 1

    except KeyboardInterrupt:
        logging.error("Interrupted.")
        return 130

    except Exception:
        logging.exception(
            "Unexpected failure."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
