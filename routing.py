"""
Routing & Geocoding (OpenRouteService)
=====================================
Pulls REAL distance and drive-time data between ZIP codes.

This is the genuinely "real data" part of the tool.

Setup:
  1. Free API key: https://openrouteservice.org/dev/#/signup
  2. Set env var ORS_API_KEY=your_key  (or paste into the app sidebar)

Free tier: ~2,000 requests/day. Results are cached per session.

Requires: requests
"""

import os
import math
import requests

ORS_BASE = "https://api.openrouteservice.org"

_geocode_cache = {}
_route_cache = {}


def get_api_key(provided=None):
    return provided or os.environ.get("ORS_API_KEY", "")


def geocode_zip(zip_code, api_key, country="US"):
    zip_code = str(zip_code).strip()
    cache_key = f"{zip_code}-{country}"
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    url = f"{ORS_BASE}/geocode/search"
    params = {"api_key": api_key, "text": zip_code, "boundary.country": country, "size": 1}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        if not features:
            return None
        lon, lat = features[0]["geometry"]["coordinates"]
        result = (lat, lon)
        _geocode_cache[cache_key] = result
        return result
    except Exception as e:
        raise RuntimeError(f"Geocoding failed for ZIP {zip_code}: {e}")


def get_route_distance(origin_latlon, dest_latlon, api_key, profile="driving-car"):
    cache_key = f"{origin_latlon}-{dest_latlon}-{profile}"
    if cache_key in _route_cache:
        return _route_cache[cache_key]

    url = f"{ORS_BASE}/v2/directions/{profile}"
    headers = {"Authorization": api_key}
    body = {"coordinates": [[origin_latlon[1], origin_latlon[0]], [dest_latlon[1], dest_latlon[0]]]}
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        summary = data["routes"][0]["summary"]
        result = {
            "distance_miles": round(summary["distance"] / 1609.34, 2),
            "duration_min": round(summary["duration"] / 60, 1),
        }
        _route_cache[cache_key] = result
        return result
    except Exception as e:
        raise RuntimeError(f"Routing failed: {e}")


def straight_line_distance(origin_latlon, dest_latlon):
    """Great-circle distance in miles — used for DRONE routes (fly direct)."""
    lat1, lon1 = origin_latlon
    lat2, lon2 = dest_latlon
    R = 3958.8

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)
