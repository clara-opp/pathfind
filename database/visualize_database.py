#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from datetime import datetime

def db_file():
    d = Path(__file__).parent
    for p in [d / "unified_country_database.db", d / "data" / "unified_country_database.db"]:
        if p.exists():
            return p
    raise FileNotFoundError("Database file not found.")

def sample_rows(cur, table, n=3):
    try:
        cur.execute(f"SELECT * FROM `{table}` LIMIT {n}")
        return cur.fetchall()
    except Exception:
        return []

def main():
    db = db_file()
    out = Path(__file__).parent / "schema_docs" / "schema.html"
    out.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    html = [f"""<!doctype html><html><head><meta charset="utf-8">
<title>DB Schema Overview</title>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f7fafd;margin:0;padding:32px;}}
h1{{color:#23437e;font-size:2.2em;margin-bottom:0.2em}}
.desc{{color:#567; margin:0.2em 0 2em;}}
.nav{{background:#f0f5ff;padding:10px 18px;border-radius:8px;margin-bottom:2em}}
.nav a{{margin-right:14px;color:#23437e;text-decoration:none;font-weight:500;}}
.nav a:hover{{text-decoration:underline;}}
.card{{background:#fff;border-radius:10px;box-shadow:0 2px 10px #dde3ee;margin-bottom:2.5em;padding:2em 1.7em;}}
.card h2{{font-size:1.17em;margin:.1em 0 .7em; color:#32599f}}
.pk{{color:#37a4a5;font-weight:bold}}
.s{{color:#555;font-size:.99em;}}
table{{border-collapse:collapse;width:100%;margin:1em 0 0 0;box-shadow:0 1px 2px #eaedf5}}
th,td{{border:1px solid #e6eaf0;padding:6px 11px;}}
th{{background:#eaf2fb;color:#1c3e6c;font-weight:600}}
tr:nth-child(even) td{{background:#f4f8fc;}}
tr:hover td{{background:#ddeafb !important;}}
.empty{{color:#aaa;margin:0.6em 0 1.5em 0}}
@media(max-width:980px){{.card,body{{padding:1em}} table,th,td{{font-size:.94em}}}}
</style></head><body>
<h1>DB schema</h1>
<div class="desc">File: <tt>{db}</tt>
<br>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
</div>
<div class="nav">
    {"".join(f'<a href="#{t}">{t}</a>' for t in tables)}
</div>
"""]
    for t in tables:
        cur.execute(f"PRAGMA table_info(`{t}`)")
        cols = cur.fetchall()
        names = [c[1] for c in cols]
        pk = [c[1] for c in cols if c[5]]
        samp = sample_rows(cur, t)
        html.append(f'<div class="card" id="{t}"><h2>{t}</h2>')
        html.append(f'<div class="s"><b>Primary key:</b> <span class="pk">{", ".join(pk) if pk else "—"}</span></div>')
        html.append(f'<div class="s"><b>Columns:</b> {", ".join(names)}</div>')
        if samp:
            html.append("<table><tr>" + "".join(f"<th>{n}</th>" for n in names) + "</tr>")
            for row in samp:
                html.append("<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>")
            html.append("</table>")
        else:
            html.append("<div class='empty'>(no rows)</div>")
        html.append("</div>")
    html.append("</body></html>")
    out.write_text("".join(html), encoding="utf-8")
    print(f"✅ Done: {out.absolute()}")

if __name__ == "__main__":
    main()
