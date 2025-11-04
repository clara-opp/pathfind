#!/usr/bin/env python3
"""
tw_meta_min.py  — CLEAN MINIMAL VERSION
Collect only meta fields from Auswärtiges Amt API (no HTML content, no Playwright).

Fields per row:
  content_id, title, country_name, country_code, iso3_country_code,
  last_modified_iso, effective_iso, warning, partial_warning,
  situation_warning, situation_part_warning
"""

from __future__ import annotations
import json, os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import requests

BASE_API = "https://www.auswaertiges-amt.de/opendata"
OUT_PATH = os.environ.get("AA_TW_JSON", "travelwarnings_snapshot.json")

S = requests.Session()
S.headers.update({
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "aa-travelwarning-minimal/0.3",
})

def ts_iso(ts: Optional[int]) -> Optional[str]:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except Exception:
        return None

def get_json(path: str, timeout: int = 30) -> Any:
    """Fetch JSON with redirects disabled. Raise if redirected or non-200."""
    url = f"{BASE_API}{path}"
    r = S.get(url, timeout=timeout, allow_redirects=False)
    if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
        raise RuntimeError(f"redirected: {url} -> {r.headers.get('Location','')}")
    r.raise_for_status()
    return r.json()

def collect(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    root = get_json("/travelwarning")
    if not isinstance(root, dict) or "response" not in root:
        raise RuntimeError("Unexpected payload from /travelwarning")

    resp = root["response"]
    items: List[Tuple[str, Dict[str, Any]]] = [
        (k, v) for k, v in resp.items() if isinstance(k, str) and k.isdigit()
    ]
    if limit:
        items = items[:limit]

    rows: List[Dict[str, Any]] = []
    for cid, meta in items:
        try:
            detail = get_json(f"/travelwarning/{cid}")
        except Exception as e:
            print(f"skip {cid}: {e}")
            continue

        country_name = (
            detail.get("countryName") or detail.get("country") or detail.get("state") or meta.get("countryName")
        )
        country_code = detail.get("countryCode") or meta.get("countryCode")
        iso3 = detail.get("iso3CountryCode") or meta.get("iso3CountryCode")
        title = detail.get("title") or detail.get("name") or meta.get("title")
        last_mod = ts_iso(detail.get("lastModified") or meta.get("lastModified"))
        effective = ts_iso(detail.get("effective"))
        warning = int(bool(detail.get("warning", meta.get("warning", False))))
        partial_warning = int(bool(detail.get("partialWarning", meta.get("partialWarning", False))))
        situation_warning = int(bool(detail.get("situationWarning", meta.get("situationWarning", False))))
        situation_part_warning = int(bool(detail.get("situationPartWarning", meta.get("situationPartWarning", False))))

        try:
            cid_for_row = int(cid)
        except Exception:
            cid_for_row = cid

        rows.append({
            "content_id": cid_for_row,
            "title": title,
            "country_name": country_name,
            "country_code": country_code,
            "iso3_country_code": iso3,
            "last_modified_iso": last_mod,
            "effective_iso": effective,
            "warning": warning,
            "partial_warning": partial_warning,
            "situation_warning": situation_warning,
            "situation_part_warning": situation_part_warning,
        })

    try:
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(rows)} rows → {OUT_PATH}")
    except Exception as e:
        print(f"Could not write {OUT_PATH}: {e}")

    return rows

if __name__ == "__main__":
    collect(limit=None)
