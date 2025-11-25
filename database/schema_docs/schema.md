# Database Schema Documentation

*Generated: 2025-11-25 15:07:42*

---

## Tables

- [climate_monthly](#climate_monthly) (291 rows)
- [countries](#countries) (246 rows)
- [tugo_climate](#tugo_climate) (584 rows)
- [tugo_entry](#tugo_entry) (1,285 rows)
- [tugo_health](#tugo_health) (4,547 rows)
- [tugo_laws](#tugo_laws) (2,048 rows)
- [tugo_offices](#tugo_offices) (359 rows)
- [tugo_safety](#tugo_safety) (1,757 rows)
- [unesco_by_country](#unesco_by_country) (171 rows)
- [unesco_heritage_sites](#unesco_heritage_sites) (1,248 rows)

---

## climate_monthly

**Row Count:** 291

**Indexes:** idx_climate_country

### Columns

| Column | Type | Null | Key | Default |
|--------|------|------|-----|---------|
| country_name_climate | TEXT | ✓ |  |  |
| climate_avg_temp_c | REAL | ✓ |  |  |
| climate_avg_cloud_pct | REAL | ✓ |  |  |
| climate_total_precip_mm | REAL | ✓ |  |  |
| climate_avg_monthly_precip_mm | REAL | ✓ |  |  |
| climate_temp_month_1 | REAL | ✓ |  |  |
| climate_cloud_month_1 | REAL | ✓ |  |  |
| climate_precip_month_1 | REAL | ✓ |  |  |
| climate_temp_month_2 | REAL | ✓ |  |  |
| climate_cloud_month_2 | REAL | ✓ |  |  |
| climate_precip_month_2 | REAL | ✓ |  |  |
| climate_temp_month_3 | REAL | ✓ |  |  |
| climate_cloud_month_3 | REAL | ✓ |  |  |
| climate_precip_month_3 | REAL | ✓ |  |  |
| climate_temp_month_4 | REAL | ✓ |  |  |
| climate_cloud_month_4 | REAL | ✓ |  |  |
| climate_precip_month_4 | REAL | ✓ |  |  |
| climate_temp_month_5 | REAL | ✓ |  |  |
| climate_cloud_month_5 | REAL | ✓ |  |  |
| climate_precip_month_5 | REAL | ✓ |  |  |
| climate_temp_month_6 | REAL | ✓ |  |  |
| climate_cloud_month_6 | REAL | ✓ |  |  |
| climate_precip_month_6 | REAL | ✓ |  |  |
| climate_temp_month_7 | REAL | ✓ |  |  |
| climate_cloud_month_7 | REAL | ✓ |  |  |
| climate_precip_month_7 | REAL | ✓ |  |  |
| climate_temp_month_8 | REAL | ✓ |  |  |
| climate_cloud_month_8 | REAL | ✓ |  |  |
| climate_precip_month_8 | REAL | ✓ |  |  |
| climate_temp_month_9 | REAL | ✓ |  |  |
| climate_cloud_month_9 | REAL | ✓ |  |  |
| climate_precip_month_9 | REAL | ✓ |  |  |
| climate_temp_month_10 | REAL | ✓ |  |  |
| climate_cloud_month_10 | REAL | ✓ |  |  |
| climate_precip_month_10 | REAL | ✓ |  |  |
| climate_temp_month_11 | REAL | ✓ |  |  |
| climate_cloud_month_11 | REAL | ✓ |  |  |
| climate_precip_month_11 | REAL | ✓ |  |  |
| climate_temp_month_12 | REAL | ✓ |  |  |
| climate_cloud_month_12 | REAL | ✓ |  |  |
| climate_precip_month_12 | REAL | ✓ |  |  |

## countries

**Row Count:** 246

**Indexes:** idx_countries_iso3

### Columns

| Column | Type | Null | Key | Default |
|--------|------|------|-----|---------|
| iso3 | TEXT | ✓ |  |  |
| country_name | TEXT | ✓ |  |  |
| iso2 | TEXT | ✓ |  |  |
| numeric_code | INTEGER | ✓ |  |  |
| iso_3166_2 | TEXT | ✓ |  |  |
| pli_ppp | REAL | ✓ |  |  |
| pli_exchange_rate | REAL | ✓ |  |  |
| pli_PLI | REAL | ✓ |  |  |
| pli_EuroValue | REAL | ✓ |  |  |
| exchange_rate_1960 | REAL | ✓ |  |  |
| exchange_rate_1961 | REAL | ✓ |  |  |
| exchange_rate_1962 | REAL | ✓ |  |  |
| exchange_rate_1963 | REAL | ✓ |  |  |
| exchange_rate_1964 | REAL | ✓ |  |  |
| exchange_rate_1965 | REAL | ✓ |  |  |
| exchange_rate_1966 | REAL | ✓ |  |  |
| exchange_rate_1967 | REAL | ✓ |  |  |
| exchange_rate_1968 | REAL | ✓ |  |  |
| exchange_rate_1969 | REAL | ✓ |  |  |
| exchange_rate_1970 | REAL | ✓ |  |  |
| exchange_rate_1971 | REAL | ✓ |  |  |
| exchange_rate_1972 | REAL | ✓ |  |  |
| exchange_rate_1973 | REAL | ✓ |  |  |
| exchange_rate_1974 | REAL | ✓ |  |  |
| exchange_rate_1975 | REAL | ✓ |  |  |
| exchange_rate_1976 | REAL | ✓ |  |  |
| exchange_rate_1977 | REAL | ✓ |  |  |
| exchange_rate_1978 | REAL | ✓ |  |  |
| exchange_rate_1979 | REAL | ✓ |  |  |
| exchange_rate_1980 | REAL | ✓ |  |  |
| exchange_rate_1981 | REAL | ✓ |  |  |
| exchange_rate_1982 | REAL | ✓ |  |  |
| exchange_rate_1983 | REAL | ✓ |  |  |
| exchange_rate_1984 | REAL | ✓ |  |  |
| exchange_rate_1985 | REAL | ✓ |  |  |
| exchange_rate_1986 | REAL | ✓ |  |  |
| exchange_rate_1987 | REAL | ✓ |  |  |
| exchange_rate_1988 | REAL | ✓ |  |  |
| exchange_rate_1989 | REAL | ✓ |  |  |
| exchange_rate_1990 | REAL | ✓ |  |  |
| exchange_rate_1991 | REAL | ✓ |  |  |
| exchange_rate_1992 | REAL | ✓ |  |  |
| exchange_rate_1993 | REAL | ✓ |  |  |
| exchange_rate_1994 | REAL | ✓ |  |  |
| exchange_rate_1995 | REAL | ✓ |  |  |
| exchange_rate_1996 | REAL | ✓ |  |  |
| exchange_rate_1997 | REAL | ✓ |  |  |
| exchange_rate_1998 | REAL | ✓ |  |  |
| exchange_rate_1999 | REAL | ✓ |  |  |
| exchange_rate_2000 | REAL | ✓ |  |  |
| exchange_rate_2001 | REAL | ✓ |  |  |
| exchange_rate_2002 | REAL | ✓ |  |  |
| exchange_rate_2003 | REAL | ✓ |  |  |
| exchange_rate_2004 | REAL | ✓ |  |  |
| exchange_rate_2005 | REAL | ✓ |  |  |
| exchange_rate_2006 | REAL | ✓ |  |  |
| exchange_rate_2007 | REAL | ✓ |  |  |
| exchange_rate_2008 | REAL | ✓ |  |  |
| exchange_rate_2009 | REAL | ✓ |  |  |
| exchange_rate_2010 | REAL | ✓ |  |  |
| exchange_rate_2011 | REAL | ✓ |  |  |
| exchange_rate_2012 | REAL | ✓ |  |  |
| exchange_rate_2013 | REAL | ✓ |  |  |
| exchange_rate_2014 | REAL | ✓ |  |  |
| exchange_rate_2015 | REAL | ✓ |  |  |
| exchange_rate_2016 | REAL | ✓ |  |  |
| exchange_rate_2017 | REAL | ✓ |  |  |
| exchange_rate_2018 | REAL | ✓ |  |  |
| exchange_rate_2019 | REAL | ✓ |  |  |
| exchange_rate_2020 | REAL | ✓ |  |  |
| exchange_rate_2021 | REAL | ✓ |  |  |
| exchange_rate_2022 | REAL | ✓ |  |  |
| exchange_rate_2023 | REAL | ✓ |  |  |
| exchange_rate_2024 | REAL | ✓ |  |  |
| tugo_country_name | TEXT | ✓ |  |  |
| tugo_advisory_state | REAL | ✓ |  |  |
| tugo_advisory_text | TEXT | ✓ |  |  |
| tugo_has_warning | REAL | ✓ |  |  |
| tugo_has_regional | REAL | ✓ |  |  |
| tugo_published_date | TEXT | ✓ |  |  |
| tugo_recent_updates | TEXT | ✓ |  |  |
| tugo_advisories_desc | TEXT | ✓ |  |  |
| fo_content_id | REAL | ✓ |  |  |
| fo_title | TEXT | ✓ |  |  |
| fo_last_modified_iso | TEXT | ✓ |  |  |
| fo_effective_iso | TEXT | ✓ |  |  |
| fo_warning | REAL | ✓ |  |  |
| fo_partial_warning | REAL | ✓ |  |  |
| fo_situation_warning | REAL | ✓ |  |  |
| fo_situation_part_warning | REAL | ✓ |  |  |

## tugo_climate

**Row Count:** 584

**Indexes:** idx_tugo_climate_iso2

### Columns

| Column | Type | Null | Key | Default |
|--------|------|------|-----|---------|
| iso2 | TEXT | ✓ |  |  |
| country_name | TEXT | ✓ |  |  |
| category | TEXT | ✓ |  |  |
| description | TEXT | ✓ |  |  |

## tugo_entry

**Row Count:** 1,285

**Indexes:** idx_tugo_entry_iso2

### Columns

| Column | Type | Null | Key | Default |
|--------|------|------|-----|---------|
| iso2 | TEXT | ✓ |  |  |
| country_name | TEXT | ✓ |  |  |
| category | TEXT | ✓ |  |  |
| description | TEXT | ✓ |  |  |

## tugo_health

**Row Count:** 4,547

**Indexes:** idx_tugo_health_iso2

### Columns

| Column | Type | Null | Key | Default |
|--------|------|------|-----|---------|
| iso2 | TEXT | ✓ |  |  |
| country_name | TEXT | ✓ |  |  |
| disease_name | TEXT | ✓ |  |  |
| category | TEXT | ✓ |  |  |
| description | TEXT | ✓ |  |  |

## tugo_laws

**Row Count:** 2,048

**Indexes:** idx_tugo_laws_iso2

### Columns

| Column | Type | Null | Key | Default |
|--------|------|------|-----|---------|
| iso2 | TEXT | ✓ |  |  |
| country_name | TEXT | ✓ |  |  |
| category | TEXT | ✓ |  |  |
| description | TEXT | ✓ |  |  |

## tugo_offices

**Row Count:** 359

**Indexes:** idx_tugo_offices_iso2

### Columns

| Column | Type | Null | Key | Default |
|--------|------|------|-----|---------|
| iso2 | TEXT | ✓ |  |  |
| country_name | TEXT | ✓ |  |  |
| office_type | TEXT | ✓ |  |  |
| city | TEXT | ✓ |  |  |
| address | TEXT | ✓ |  |  |
| phone | TEXT | ✓ |  |  |
| email | TEXT | ✓ |  |  |
| website | TEXT | ✓ |  |  |

## tugo_safety

**Row Count:** 1,757

**Indexes:** idx_tugo_safety_iso2

### Columns

| Column | Type | Null | Key | Default |
|--------|------|------|-----|---------|
| iso2 | TEXT | ✓ |  |  |
| country_name | TEXT | ✓ |  |  |
| category | TEXT | ✓ |  |  |
| description | TEXT | ✓ |  |  |

## unesco_by_country

**Row Count:** 171

**Indexes:** idx_unesco_by_country_iso_code

### Columns

| Column | Type | Null | Key | Default |
|--------|------|------|-----|---------|
| country_name | TEXT | ✓ |  |  |
| iso_code | TEXT | ✓ |  |  |
| region | TEXT | ✓ |  |  |
| total_sites | INTEGER | ✓ |  |  |
| cultural_sites | INTEGER | ✓ |  |  |
| natural_sites | INTEGER | ✓ |  |  |
| mixed_sites | INTEGER | ✓ |  |  |
| danger_sites | INTEGER | ✓ |  |  |
| transboundary_sites | INTEGER | ✓ |  |  |
| site_names | TEXT | ✓ |  |  |
| site_ids | TEXT | ✓ |  |  |

## unesco_heritage_sites

**Row Count:** 1,248

**Indexes:** idx_unesco_id, idx_unesco_country_iso

### Columns

| Column | Type | Null | Key | Default |
|--------|------|------|-----|---------|
| id | TEXT | ✓ |  |  |
| name | TEXT | ✓ |  |  |
| name_fr | TEXT | ✓ |  |  |
| name_es | TEXT | ✓ |  |  |
| country | TEXT | ✓ |  |  |
| country_iso | TEXT | ✓ |  |  |
| region | TEXT | ✓ |  |  |
| category | TEXT | ✓ |  |  |
| short_description | TEXT | ✓ |  |  |
| description | TEXT | ✓ |  |  |
| justification | TEXT | ✓ |  |  |
| date_inscribed | TEXT | ✓ |  |  |
| secondary_dates | TEXT | ✓ |  |  |
| danger | TEXT | ✓ |  |  |
| danger_list | INTEGER | ✓ |  |  |
| area_hectares | REAL | ✓ |  |  |
| criteria_txt | TEXT | ✓ |  |  |
| cultural_criteria | TEXT | ✓ |  |  |
| natural_criteria | TEXT | ✓ |  |  |
| transboundary | TEXT | ✓ |  |  |
| components_count | INTEGER | ✓ |  |  |
| longitude | REAL | ✓ |  |  |
| latitude | REAL | ✓ |  |  |
| main_image_url | TEXT | ✓ |  |  |
| images_urls | TEXT | ✓ |  |  |

