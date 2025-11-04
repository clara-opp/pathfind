#!/usr/bin/env python3
# Download all TuGo TravelSafe country warnings as JSON files.

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# ... keep your imports/config ...

# --- Config / env ---
load_dotenv()
TUGO_API_KEY = os.getenv("tugo_api")
API_BASE = "https://api.tugo.com/v1/travelsafe"

def make_session(
    retries: int = 5,
    backoff: float = 0.8,
    status_forcelist: Tuple[int, ...] = (429, 500, 502, 503, 504),
) -> requests.Session:
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        status=retries,
        backoff_factor=backoff,
        status_forcelist=status_forcelist,
        allowed_methods=None,
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s = requests.Session()
    s.headers.update({
        "Accept": "application/json",
        "User-Agent": "tugo-travelsafe-dump/1.1 (+requests)",
        "X-Auth-API-Key": TUGO_API_KEY or "",
    })
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def get_country_list(session: requests.Session, timeout: Tuple[float, float]) -> List[str]:
    """
    Query TuGo for the list of countries. Returns ISO2 codes like ['GR','DE',...].
    Retries locally on ReadTimeout/ConnectionError with exponential backoff.
    """
    if not TUGO_API_KEY:
        raise RuntimeError("Missing API key. Add `tugo_api=...` to your .env or environment.")

    url = f"{API_BASE}/countries"
    attempts = 5
    delay = 1.5

    last_err: Optional[Exception] = None
    for i in range(1, attempts + 1):
        try:
            # Use a larger read timeout for this heavy endpoint
            # Prefer connect=10s, read=180s (overrides CLI if smaller)
            connect_to, read_to = timeout
            connect_to = max(connect_to, 10.0)
            read_to = max(read_to, 180.0)
            resp = session.get(url, timeout=(connect_to, read_to))
            resp.raise_for_status()
            data = resp.json()
            break
        except (requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ConnectionError) as e:
            last_err = e
            if i < attempts:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    else:
        # should not reach here because raise above, but keep mypy happy
        raise requests.RequestException(last_err)

    codes: List[str] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for k in ("code", "countryCode", "iso2", "iso"):
                    v = item.get(k)
                    if isinstance(v, str) and len(v) == 2:
                        codes.append(v.upper()); break
    elif isinstance(data, dict):
        for key in ("countries", "data", "result", "response"):
            lst = data.get(key)
            if isinstance(lst, list):
                for item in lst:
                    if isinstance(item, dict):
                        for k in ("code", "countryCode", "iso2", "iso"):
                            v = item.get(k)
                            if isinstance(v, str) and len(v) == 2:
                                codes.append(v.upper()); break
                break

    codes = sorted(set(codes))
    if not codes:
        raise RuntimeError("Could not extract country codes from /countries response.")
    return codes

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Download all TuGo TravelSafe country advisories as JSON files.")
    ap.add_argument("--outdir", default="tugo_warnings", help="Output directory (default: tugo_warnings)")
    # bump default; we will still override to read>=180s for /countries
    ap.add_argument("--timeout", type=float, default=60.0,
                    help="Per-try timeout seconds for connect & read. Default: 60 (countries call internally uses read>=180).")
    ap.add_argument("--retries", type=int, default=6, help="Retries on timeout/5xx/429. Default: 6")
    ap.add_argument("--backoff", type=float, default=0.8, help="Exponential backoff factor. Default: 0.8")
    ap.add_argument("--codes", default="",
                    help="Optional comma-separated ISO2 list to skip /countries (e.g. 'GR,DE,ES'). Use this if /countries times out.")
    args = ap.parse_args(argv[1:])

    if not TUGO_API_KEY:
        print("ERROR: Missing API key. Set tugo_api in your .env file.", file=sys.stderr)
        return 2

    outdir = Path(args.outdir)
    timeout_tuple: Tuple[float, float] = (args.timeout, args.timeout)

    session = make_session(retries=args.retries, backoff=args.backoff)

    if args.codes.strip():
        codes = [c.strip().upper() for c in args.codes.split(",") if c.strip()]
    else:
        print("Fetching country list…")
        codes = get_country_list(session, timeout_tuple)

    # ... keep the rest of your file unchanged ...


if __name__ == "__main__":
    sys.exit(main(sys.argv))
