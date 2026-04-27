"""KLIPY GIF search (Tenor replacement).

Endpoint: ``GET https://api.klipy.com/api/v1/{api_key}/gifs/search?q=...``
Response is JSON (not Tenor-compatible); we normalize to a plain list of GIF URLs
so the rest of the app behaves like the old Tenor flow.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote, urlencode, urlparse

import requests

from .paths import SETTINGS_FILE

VALID_RATINGS = ("g", "pg", "pg-13", "r")

_DEFAULT_HEADERS = {
    "User-Agent": "divoom-gaming-gate/1.0 (Klipy GIF search; https://github.com/adiastra/divoom-gaming-gate)",
    "Accept": "application/json",
}


def _tenor_filter_to_rating(tenor_filter: str) -> str:
    """Map legacy Tenor content-filter labels to KLIPY ``rating`` values."""
    mapping = {"off": "g", "low": "g", "medium": "pg", "high": "pg-13"}
    return mapping.get((tenor_filter or "medium").lower(), "pg")


def get_klipy_settings() -> Tuple[str, str]:
    """Return ``(api_key, rating)`` from user settings.

    Falls back to legacy ``tenor_api_key`` / ``tenor_filter`` when KLIPY
    fields are missing.
    """
    if not os.path.exists(SETTINGS_FILE):
        return "", "pg"
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings: Dict[str, Any] = json.load(f)
    key = (settings.get("klipy_api_key") or settings.get("tenor_api_key") or "").strip()
    rating = (settings.get("klipy_rating") or "").strip().lower()
    if rating not in VALID_RATINGS:
        rating = _tenor_filter_to_rating(str(settings.get("tenor_filter", "medium")))
    if rating not in VALID_RATINGS:
        rating = "pg"
    return key, rating


def _klipy_error_message(body: Dict[str, Any]) -> str:
    err = body.get("errors") or {}
    msgs = err.get("message")
    if isinstance(msgs, list) and msgs:
        return "; ".join(str(m) for m in msgs)
    if isinstance(msgs, str):
        return msgs
    return json.dumps(body)[:500]


def normalize_media_url(s: str) -> Optional[str]:
    """Turn a Klipy/Tenor-style URL into an absolute ``https?://`` URL."""
    s = (s or "").strip()
    if not s:
        return None
    if s.startswith("//"):
        return "https:" + s
    if s.startswith(("http://", "https://")):
        return s
    return None


def _looks_like_gif_asset_url(u: str) -> bool:
    """Heuristic: string is probably a raster/animated asset URL (not a site landing page)."""
    low = u.lower()
    if ".gif" in low or ".webp" in low or ".png" in low or ".jpg" in low or ".jpeg" in low:
        return True
    if "format=gif" in low or "format=webp" in low:
        return True
    return False


def _dedupe_urls(urls: List[str]) -> List[str]:
    """Drop duplicate URLs; normalize by scheme/host/path (ignore query) for CDN variants."""
    seen: Set[str] = set()
    out: List[str] = []
    for raw in urls:
        u = (raw or "").strip()
        if not u:
            continue
        p = urlparse(u)
        key = (p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"))
        if key in seen:
            continue
        seen.add(key)
        out.append(u)
    return out


def _klipy_file_best_url(item: dict) -> Optional[str]:
    """KLIPY search hits use ``file.{hd,sd,...}.{gif,webp}.url`` (see GIF Search API docs)."""
    f = item.get("file")
    if not isinstance(f, dict):
        return None
    for q in ("hd", "sd", "md", "lg", "sm"):
        node = f.get(q)
        if not isinstance(node, dict):
            continue
        gif_obj = node.get("gif")
        if isinstance(gif_obj, dict):
            u = normalize_media_url(str(gif_obj.get("url") or ""))
            if u:
                return u
    for q in ("hd", "sd", "md", "lg", "sm"):
        node = f.get(q)
        if not isinstance(node, dict):
            continue
        webp_obj = node.get("webp")
        if isinstance(webp_obj, dict):
            u = normalize_media_url(str(webp_obj.get("url") or ""))
            if u:
                return u
    return None


def _list_to_item_dicts(lst: List[Any]) -> List[Dict[str, Any]]:
    """If API returns a list of URL strings, wrap as dicts for the normal extractor."""
    if not lst:
        return []
    if all(isinstance(x, str) for x in lst):
        return [{"src": x} for x in lst if x.strip()]
    return [x for x in lst if isinstance(x, dict)]


def _extract_items(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect result objects from known KLIPY (and drift) JSON shapes."""
    data = body.get("data")
    # Prefer documented shape: { "data": { "data": [ ... ], "has_next": ... } }
    if isinstance(data, dict):
        for key in ("data", "gifs", "items", "results", "clips"):
            arr = data.get(key)
            if isinstance(arr, list) and arr:
                return _list_to_item_dicts(arr)
    if isinstance(data, list):
        return _list_to_item_dicts(data)
    for top in ("gifs", "results", "items"):
        arr = body.get(top)
        if isinstance(arr, list):
            return _list_to_item_dicts(arr)
    return []


def _coerce_bool(v: Any) -> Optional[bool]:
    """Parse API booleans that may be JSON bool, int, or string."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(int(v))
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes", "y"):
            return True
        if s in ("false", "0", "no", "n", ""):
            return False
    return None


def _extract_pagination(body: Dict[str, Any], page_requested: int) -> Tuple[bool, int]:
    data = body.get("data")
    if isinstance(data, dict):
        current = int(data.get("current_page") or page_requested)
        hn = _coerce_bool(data.get("has_next"))
        hm = _coerce_bool(data.get("has_more"))
        has_next = bool(hn) if hn is not None else bool(hm) if hm is not None else False
        if "next_page" in data:
            has_next = has_next or data.get("next_page") is not None
        total_pages = data.get("total_pages") or data.get("last_page")
        if isinstance(total_pages, int) and total_pages > 0:
            has_next = has_next or (current < total_pages)
        return has_next, current
    return False, page_requested


def gif_url_from_item(item: Any, _depth: int = 0) -> Optional[str]:
    """Best GIF/WebP URL from one search hit (nested dicts, protocol-relative URLs)."""
    if not isinstance(item, dict) or _depth > 6:
        return None
    klipy_u = _klipy_file_best_url(item)
    if klipy_u:
        return klipy_u
    priority_keys = (
        "src",
        "proxy_src",
        "gif",
        "url",
        "link",
        "file",
        "download",
        "webp",
        "hd",
        "sd",
        "preview",
        "thumbnail",
    )
    for key in priority_keys:
        val = item.get(key)
        if isinstance(val, str):
            u = normalize_media_url(val)
            if u and (key in ("src", "proxy_src", "gif") or _looks_like_gif_asset_url(u)):
                return u
    for nest_key in ("file", "media", "images", "original", "formats", "image", "files"):
        nested = item.get(nest_key)
        if isinstance(nested, dict):
            found = gif_url_from_item(nested, _depth + 1)
            if found:
                return found
        if isinstance(nested, list) and nested:
            for el in nested:
                found = gif_url_from_item(el, _depth + 1) if isinstance(el, dict) else None
                if not found and isinstance(el, str):
                    u = normalize_media_url(el)
                    if u and _looks_like_gif_asset_url(u):
                        return u
                if found:
                    return found
    for val in item.values():
        if isinstance(val, str):
            u = normalize_media_url(val)
            if u and _looks_like_gif_asset_url(u):
                return u
        if isinstance(val, dict):
            u = gif_url_from_item(val, _depth + 1)
            if u:
                return u
    return None


def _fallback_collect_gif_urls(obj: Any, out: List[str], seen: Set[str], depth: int = 0) -> None:
    """Last resort: walk JSON and collect strings that look like hosted GIF/WebP assets."""
    if depth > 14:
        return
    if isinstance(obj, dict):
        for v in obj.values():
            _fallback_collect_gif_urls(v, out, seen, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            _fallback_collect_gif_urls(v, out, seen, depth + 1)
    elif isinstance(obj, str):
        u = normalize_media_url(obj.strip())
        if u and _looks_like_gif_asset_url(u) and u not in seen:
            seen.add(u)
            out.append(u)


def klipy_search_gifs(
    api_key: str,
    query: str,
    *,
    page: int = 1,
    rating: str = "pg",
    per_page: int = 20,
    timeout: float = 15.0,
) -> Tuple[List[str], Optional[int]]:
    """Search KLIPY; returns ``(gif_urls, next_page)`` like the old Tenor picker expected."""
    rating = (rating or "pg").lower()
    if rating not in VALID_RATINGS:
        rating = "pg"
    q = (query or "").strip()
    if not q:
        return [], None

    key_in_path = quote(api_key.strip(), safe="")
    params: Dict[str, Any] = {
        "q": q,
        "page": max(1, int(page)),
        "per_page": max(8, min(50, int(per_page))),
        "rating": rating,
        "locale": "en_US",
    }
    url = f"https://api.klipy.com/api/v1/{key_in_path}/gifs/search?{urlencode(params)}"
    resp = requests.get(url, timeout=timeout, headers=_DEFAULT_HEADERS)
    resp.raise_for_status()
    body = resp.json()
    if body.get("result") is False:
        raise RuntimeError(_klipy_error_message(body))

    items = _extract_items(body)
    urls: List[str] = []
    for it in items:
        u = gif_url_from_item(it)
        if u:
            nu = normalize_media_url(u)
            if nu:
                urls.append(nu)

    if not urls:
        seen: Set[str] = set()
        fallback: List[str] = []
        _fallback_collect_gif_urls(body, fallback, seen)
        urls = fallback

    urls = _dedupe_urls(urls)

    cap = min(100, max(24, int(params["per_page"]) * 4))
    urls = urls[:cap]

    has_next, current_page = _extract_pagination(body, max(1, int(page)))
    if not has_next and len(urls) >= params["per_page"]:
        has_next = True
    next_page = (current_page + 1) if has_next else None
    return urls, next_page
