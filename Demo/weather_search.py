# -*- coding: utf-8 -*-
"""
weather_search.py
-----------------
Monat + Ziel-Temperatur -> Top-Länder (basierend auf Berkeley Earth Country Monthly Averages)

Standard: kompakter, kuratierter Mirror (compgeolab), Lizenz CC-BY-NC.
Optional: direktes Original-ZIP von Berkeley Earth (USE_BERKELEY_ORIGINAL=1 setzen).

CLI:
    python weather_search.py July 24 10
    python weather_search.py März 18 8
"""

import io
import os
import re
import sys
import zipfile
import hashlib
import textwrap
from pathlib import Path
from typing import Optional, Tuple, List

import requests
import pandas as pd

# ------------------------------
# Konfiguration
# ------------------------------

USE_ORIGINAL = os.getenv("USE_BERKELEY_ORIGINAL", "0") == "1"

# 1) Original Berkeley Earth ZIP (größer, variableres Spaltenschema)
BE_ZIP_URL = "https://berkeley-earth-temperature.s3.us-west-1.amazonaws.com/Country_Monthly_Data.zip"
BE_MD5 = None  # kein offizieller MD5 publiziert

# 2) compgeolab Mirror (klein, einheitlichere CSVs; enthält monatliche country averages)
MIRROR_ZIP_URL = "https://github.com/compgeolab/temperature-data/releases/download/2025-02-11/temperature-data.zip"
MIRROR_MD5 = "d102212049af1695b686c94ae1eea233"

ZIP_URL = BE_ZIP_URL if USE_ORIGINAL else MIRROR_ZIP_URL
ZIP_MD5 = BE_MD5 if USE_ORIGINAL else MIRROR_MD5

CACHE_DIR = Path(".cache_tempdata"); CACHE_DIR.mkdir(exist_ok=True)
ZIP_PATH = CACHE_DIR / ("country_monthly_be.zip" if USE_ORIGINAL else "temperature-data-mirror.zip")

SOURCE_CREDIT = (
    "Data: Berkeley Earth (https://berkeleyearth.org/data/) "
    + ("[Original ZIP]" if USE_ORIGINAL else "via compgeolab/temperature-data [Mirror, CC-BY-NC]")
)

# ------------------------------
# Utilities
# ------------------------------

MONTH_NAME_TO_NUM = {
    # Englisch
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    # Deutsch
    "januar":1,"februar":2,"märz":3,"maerz":3,"april":4,"mai":5,"juni":6,
    "juli":7,"august":8,"september":9,"oktober":10,"november":11,"dezember":12,
}

def normalize_month(month_in) -> int:
    if isinstance(month_in, (int, float)) and int(month_in) == month_in and 1 <= int(month_in) <= 12:
        return int(month_in)
    s = str(month_in).strip().lower()
    if s not in MONTH_NAME_TO_NUM:
        raise ValueError(f"Unbekannter Monat: {month_in}")
    return MONTH_NAME_TO_NUM[s]

def download_zip_if_needed():
    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 0:
        return
    print(f"Downloading dataset …\n{ZIP_URL}\n-> {ZIP_PATH}")
    with requests.get(ZIP_URL, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(ZIP_PATH, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    if ZIP_MD5:
        md5 = hashlib.md5(ZIP_PATH.read_bytes()).hexdigest()
        if md5 != ZIP_MD5:
            raise RuntimeError(f"MD5 mismatch: got {md5}, expected {ZIP_MD5}")

def parse_country_from_name(fn: str) -> str:
    base = Path(fn).stem
    # Original hat oft Muster wie "Germany_TAVG_Trended" etc.
    base = re.sub(r"_TAVG.*$", "", base, flags=re.I)
    return base.replace("_", " ")

# ------------------------------
# Parser für CSV-Varianten
# ------------------------------

def load_one_csv(zf: zipfile.ZipFile, fn: str) -> Optional[pd.DataFrame]:
    """Liest eine CSV im ZIP und gibt DataFrame (country, year, month, temp_c) zurück."""
    # Ausfiltern von Nicht-CSV oder README/etc.
    if not fn.lower().endswith(".csv"):
        return None

    with zf.open(fn) as f:
        # Kommentare mit '#' ignorieren (bei Mirror üblich)
        df = pd.read_csv(io.TextIOWrapper(f, encoding="utf-8"), comment="#")

    # Spalten normalisieren (lowercase map)
    cols_map = {c.lower(): c for c in df.columns}
    country = parse_country_from_name(fn)

    # ---- Fall A: compgeolab Mirror: erwartet 'date' + 'temperature' (oder ähnlich)
    has_date = any(re.fullmatch(r"date", c, flags=re.I) for c in df.columns)
    has_temp_like = any(re.search(r"(temp|temperature|tavg)", c, flags=re.I) for c in df.columns)

    if has_date and has_temp_like:
        # Spaltennamen robust finden
        date_col = cols_map.get("date") or next(c for c in df.columns if re.fullmatch(r"date", c, flags=re.I))
        temp_col = None
        for cand in df.columns:
            if re.search(r"(temp|temperature|tavg)", cand, flags=re.I):
                temp_col = cand
                break
        if temp_col is None:
            return None

        s = df[date_col].astype(str)
        # Möglichst ohne Warning parsen: bevorzugt YYYY-MM
        dt = pd.to_datetime(s, format="%Y-%m", errors="coerce")
        # Fallback: YYYY-MM-DD
        if dt.isna().all():
            dt = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
        # Letzter Fallback: freie Erkennung
        if dt.isna().all():
            dt = pd.to_datetime(s, errors="coerce")

        out = pd.DataFrame({
            "country": country,
            "year": dt.dt.year.astype("Int64"),
            "month": dt.dt.month.astype("Int64"),
            "temp_c": pd.to_numeric(df[temp_col], errors="coerce")
        }).dropna(subset=["year", "month", "temp_c"])
        out = out[(out["month"] >= 1) & (out["month"] <= 12)]
        return out if not out.empty else None

    # ---- Fall B: Berkeley Original: 'Year', 'Month', und eine absolute Temperaturspalte
    # Häufige Temperaturspalten: "Monthly Absolute", "Absolute", oder "Temperature"
    if "year" in cols_map and "month" in cols_map:
        year_c = cols_map["year"]
        month_c = cols_map["month"]
        temp_candidates = [c for c in df.columns if re.search(r"(Monthly\s*Absolute|Absolute|Temperature|Temp)", c, flags=re.I)]
        if not temp_candidates:
            # Manche Original-CSV enthalten nur Anomalien → für unseren Zweck überspringen
            return None
        temp_c = temp_candidates[0]
        out = pd.DataFrame({
            "country": country,
            "year": pd.to_numeric(df[year_c], errors="coerce").astype("Int64"),
            "month": pd.to_numeric(df[month_c], errors="coerce").astype("Int64"),
            "temp_c": pd.to_numeric(df[temp_c], errors="coerce")
        }).dropna(subset=["year", "month", "temp_c"])
        out = out[(out["month"] >= 1) & (out["month"] <= 12)]
        return out if not out.empty else None

    # Anderes/unerwartetes Schema -> skip
    return None

def load_all_countries() -> pd.DataFrame:
    """Lädt ZIP, parst alle Länder-CSV zu einem DataFrame (country, year, month, temp_c)."""
    download_zip_if_needed()
    rows: List[pd.DataFrame] = []
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csvs:
            raise RuntimeError("ZIP enthält keine CSVs – ist der Download korrekt?")
        # Optional: ein paar offensichtliche Nicht-Länder rausfiltern (falls vorhanden)
        blacklist = {"README.csv", "LICENSE.csv"}
        for fn in csvs:
            if Path(fn).name in blacklist:
                continue
            df = load_one_csv(zf, fn)
            if df is not None and not df.empty:
                rows.append(df)

    if not rows:
        raise RuntimeError(
            "Konnte keine Länder-CSV parsen – möglicherweise anderes Format.\n"
            "Tipp: Setze USE_BERKELEY_ORIGINAL=1, oder zeige mir 1–2 Dateinamen + df.head() von einer CSV."
        )
    data = pd.concat(rows, ignore_index=True)
    # sanity: extreme Werte filtern (optional)
    data = data[(data["temp_c"] > -60) & (data["temp_c"] < 60)]
    return data

# ------------------------------
# Kernfunktion: Top-Länder finden
# ------------------------------

def find_top_countries_for_month_temp(
    df: pd.DataFrame,
    month,
    target_temp_c: float,
    top_k: int = 10,
    min_years: int = 10,
    agg: str = "mean"  # oder "median"
) -> pd.DataFrame:
    """
    Aggregiert je Land den gewünschten Monat über alle Jahre (mean/median),
    filtert Länder mit zu wenig History, sortiert nach |Temp - Wunsch|.
    """
    m = normalize_month(month)
    sub = df[df["month"] == m].copy()
    if sub.empty:
        raise ValueError("Keine Daten für diesen Monat im Datensatz.")

    aggfunc = "median" if agg.lower() == "median" else "mean"
    clim = (sub.groupby("country", as_index=False)["temp_c"]
              .agg(aggfunc)
              .rename(columns={"temp_c": "temp_c_clim"}))
    counts = sub.groupby("country")["temp_c"].count().reset_index(name="n_years")
    clim = clim.merge(counts, on="country", how="left")
    clim = clim[clim["n_years"] >= int(min_years)]

    clim["abs_diff"] = (clim["temp_c_clim"] - float(target_temp_c)).abs()
    clim["month"] = m
    clim = clim.sort_values(["abs_diff", "temp_c_clim"]).head(int(top_k))
    return clim[["country", "month", "temp_c_clim", "abs_diff", "n_years"]].reset_index(drop=True)

# ------------------------------
# CLI
# ------------------------------

def main():
    # CLI-Argumente
    month_in = sys.argv[1] if len(sys.argv) > 1 else "July"
    temp_in = float(sys.argv[2]) if len(sys.argv) > 2 else 24.0
    top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    print(f"Quelle: {SOURCE_CREDIT}")
    df = load_all_countries()
    res = find_top_countries_for_month_temp(df, month=month_in, target_temp_c=temp_in, top_k=top_k)
    # hübsch ausgeben
    print()
    print(f"Top {top_k} Länder für Monat='{month_in}' und Ziel={temp_in:.1f}°C")
    print(res.to_string(index=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        msg = textwrap.fill(str(e), width=90)
        print(f"\n[ERROR] {msg}\n", file=sys.stderr)
        sys.exit(1)
