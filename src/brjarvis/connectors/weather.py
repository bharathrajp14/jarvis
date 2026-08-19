# connectors/weather.py — Weather Connector (Zero-Setup, No Auth)
"""
Free weather connector using Open-Meteo API.
No API key required. Supports current conditions and 7-day forecasts worldwide.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from .base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.Weather")

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

_WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherConnector(BaseConnector):
    @property
    def connector_id(self) -> str:
        return "weather"

    @property
    def display_name(self) -> str:
        return "Weather (Open-Meteo)"

    @property
    def description(self) -> str:
        return "Live weather & 7-day forecast for any city worldwide — no API key needed"

    @property
    def icon(self) -> str:
        return "🌤️"

    @property
    def requires_auth(self) -> bool:
        return False

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="current",
                description="Get current weather conditions for any city or location",
                parameters={
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "City or place name (e.g. 'Chennai', 'London', 'New York')",
                        },
                    },
                    "required": ["city"],
                },
            ),
            ConnectorTool(
                name="forecast",
                description="Get 7-day weather forecast for any city or location",
                parameters={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City or place name"},
                        "days": {"type": "integer", "description": "Number of forecast days (1-7)", "default": 7},
                    },
                    "required": ["city"],
                },
            ),
        ]

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        city = str(
            args.get("city") or args.get("location") or args.get("place") or args.get("query") or args.get("q") or ""
        ).strip()
        if not city:
            return "Please provide a city or location name."

        normalized_tool = tool_name.lower().replace("get_", "").replace("weather_", "")
        if normalized_tool in ("current", "now", "condition", "conditions"):
            return self._current(city)
        elif normalized_tool in ("forecast", "weekly", "days"):
            days = int(args.get("days") or args.get("num_days") or 7)
            return self._forecast(city, days)
        return f"Unknown tool: {tool_name}. Available tools: current, forecast"

    def _fetch(self, url: str) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-ConnectorHub/1.0"})
        with urllib.request.urlopen(req, timeout=8.0) as r:
            return json.loads(r.read().decode())

    def _geocode(self, city: str) -> tuple[float, float, str]:
        """Convert city name to lat/lon."""
        params = urllib.parse.urlencode({"name": city, "count": 1, "language": "en", "format": "json"})
        data = self._fetch(f"{_GEOCODE_URL}?{params}")
        results = data.get("results", [])
        if not results:
            raise ValueError(f"City not found: '{city}'")
        r = results[0]
        label = f"{r.get('name', city)}, {r.get('country', '')}"
        return r["latitude"], r["longitude"], label

    def _current(self, city: str) -> str:
        try:
            lat, lon, label = self._geocode(city)
            params = urllib.parse.urlencode(
                {
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weathercode,apparent_temperature",
                    "wind_speed_unit": "kmh",
                    "timezone": "auto",
                }
            )
            data = self._fetch(f"{_WEATHER_URL}?{params}")
            cur = data.get("current", {})
            temp = cur.get("temperature_2m", "?")
            feels = cur.get("apparent_temperature", "?")
            humidity = cur.get("relative_humidity_2m", "?")
            wind = cur.get("wind_speed_10m", "?")
            code = cur.get("weathercode", 0)
            condition = _WMO_CODES.get(code, "Unknown")

            return (
                f"🌤️ **Current Weather — {label}**\n"
                f"• Condition: {condition}\n"
                f"• Temperature: {temp}°C (feels like {feels}°C)\n"
                f"• Humidity: {humidity}%\n"
                f"• Wind Speed: {wind} km/h\n"
                f"*(Powered by Open-Meteo — free, no API key)*"
            )
        except Exception as e:
            return f"Weather error for '{city}': {e}"

    def _forecast(self, city: str, days: int = 7) -> str:
        try:
            lat, lon, label = self._geocode(city)
            days = max(1, min(days, 7))
            params = urllib.parse.urlencode(
                {
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "forecast_days": days,
                    "timezone": "auto",
                }
            )
            data = self._fetch(f"{_WEATHER_URL}?{params}")
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            codes = daily.get("weathercode", [])
            precip = daily.get("precipitation_probability_max", [])

            lines = [f"🌤️ **{days}-Day Weather Forecast — {label}**"]
            for i, d in enumerate(dates):
                cond = _WMO_CODES.get(codes[i] if i < len(codes) else 0, "Clear")
                hi = max_temps[i] if i < len(max_temps) else "?"
                lo = min_temps[i] if i < len(min_temps) else "?"
                rain = f" (🌧️ {precip[i]}%)" if i < len(precip) and precip[i] else ""
                lines.append(f"• **{d}**: {cond} | High: {hi}°C, Low: {lo}°C{rain}")

            lines.append("*(Powered by Open-Meteo — free, no API key)*")
            return "\n".join(lines)
        except Exception as e:
            return f"Forecast error for '{city}': {e}"

    def health_check(self) -> bool:
        try:
            self._fetch(f"{_WEATHER_URL}?latitude=0&longitude=0&current=temperature_2m")
            return True
        except Exception:
            return False
