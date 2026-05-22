#!/usr/bin/env python3
"""
ip2location_ultimate.py
═══════════════════════
Le setup ULTIME IP2Location → SQLite
Combine DB11 + ASN + Proxy PX11 + noms multilingues

Tables finales :
  ip_ranges       — plages IP avec pays/région/ville/lat/lon/zip
  ip_asn          — opérateur / FAI / ASN
  ip_proxy        — type de proxy (VPN, TOR, DCH, SES...)
  cities_i18n     — noms de villes en plusieurs langues
  countries       — référentiel pays
  view_ip_full    — VIEW qui joint tout (parfait pour DataGrip)

Usage :
  pip install requests
  python ip2location_ultimate.py --token TON_TOKEN

Options :
  --token     TOKEN       Ton token IP2Location (obligatoire)
  --output    ip.db       Fichier SQLite (défaut: ip_ultimate.db)
  --no-proxy              Skip le téléchargement proxy (plus rapide)
  --no-asn                Skip ASN
  --csv-en    path.csv    CSV anglais uploadé (optionnel, enrichit cities_i18n)
  --csv-zhcn  path.csv    CSV chinois simplifié
  --csv-zhtw  path.csv    CSV chinois traditionnel
"""

import argparse, csv, io, os, sqlite3, sys, time, zipfile
import requests

BASE_URL = "https://www.ip2location.com/download/"

COLORS = {
    "reset": "\033[0m", "bold": "\033[1m",
    "green": "\033[92m", "yellow": "\033[93m",
    "red": "\033[91m",  "cyan": "\033[96m",
    "blue": "\033[94m", "gray": "\033[90m",
}
def c(text, color): return f"{COLORS[color]}{text}{COLORS['reset']}"

def progress(current, total, label=""):
    pct = 100 * current / max(total, 1)
    filled = int(38 * current / max(total, 1))
    bar = "█" * filled + "░" * (38 - filled)
    print(f"\r  {label} [{c(bar,'cyan')}] {c(f'{pct:.1f}%','bold')} {current:,}/{total:,}   ",
          end="", flush=True)

def download_zip(token, code):
    url = f"{BASE_URL}?token={token}&file={code}"
    print(f"  {c('↓','cyan')} {code}  ", end="", flush=True)
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    buf = io.BytesIO()
    dl = 0
    for chunk in r.iter_content(65536):
        buf.write(chunk); dl += len(chunk)
        if total:
            mb = dl / 1048576
            print(f"\r  {c('↓','cyan')} {code}  {mb:.1f} MB / {total/1048576:.1f} MB   ",
                  end="", flush=True)
    print(f"  {c('✓','green')}")
    buf.seek(0)
    return buf

def extract_csv_from_zip(zip_bytes):
    with zipfile.ZipFile(zip_bytes) as z:
        names = z.namelist()
        csv_name = next((n for n in names if n.upper().endswith(".CSV")), names[0])
        return z.read(csv_name).decode("utf-8", errors="replace")

def batch_insert(conn, sql, rows, batch=100000, label="Import"):
    total = len(rows)
    conn.execute("BEGIN")
    cur = conn.cursor()
    for i, row in enumerate(rows):
        try: cur.execute(sql, row)
        except: pass
        if (i+1) % batch == 0:
            conn.execute("COMMIT"); conn.execute("BEGIN")
            progress(i+1, total, label)
    conn.execute("COMMIT")
    progress(total, total, label)
    print()

# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous  = OFF;
PRAGMA cache_size   = 200000;
PRAGMA foreign_keys = ON;

-- ── Référentiel pays ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS countries (
    code        TEXT PRIMARY KEY,   -- "FR"
    numeric     TEXT,               -- "250"
    name_en     TEXT
);

-- ── Plages IP principales (DB11) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ip_ranges (
    ip_from         INTEGER NOT NULL,
    ip_to           INTEGER NOT NULL,
    country_code    TEXT,
    country_name    TEXT,
    region          TEXT,
    city            TEXT,
    latitude        REAL,
    longitude       REAL,
    zip_code        TEXT,
    timezone        TEXT
);

-- ── ASN / Opérateurs ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ip_asn (
    ip_from     INTEGER NOT NULL,
    ip_to       INTEGER NOT NULL,
    cidr        TEXT,
    asn         TEXT,
    as_name     TEXT
);

-- ── Proxies / VPN / TOR / Datacenter ─────────────────────────────────────────
-- proxy_type: VPN, TOR, DCH (datacenter), SES (search engine), RES (residential)
CREATE TABLE IF NOT EXISTS ip_proxy (
    ip_from         INTEGER NOT NULL,
    ip_to           INTEGER NOT NULL,
    proxy_type      TEXT,
    country_code    TEXT,
    country_name    TEXT,
    region          TEXT,
    city            TEXT,
    isp             TEXT,
    domain          TEXT,
    usage_type      TEXT,
    asn             TEXT,
    as_name         TEXT,
    last_seen       INTEGER,
    threat          TEXT,
    provider        TEXT
);

-- ── Noms multilingues des villes ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cities_i18n (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code    TEXT,
    country_numeric TEXT,
    country_name_en TEXT,
    region_code     TEXT,
    region_name_en  TEXT,
    city_name_en    TEXT,
    lang_code       TEXT,
    lang_name       TEXT,
    region_name_local TEXT,
    city_name_local TEXT
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ip_ranges_from ON ip_ranges(ip_from);
CREATE INDEX IF NOT EXISTS idx_ip_ranges_to   ON ip_ranges(ip_to);
CREATE INDEX IF NOT EXISTS idx_asn_from       ON ip_asn(ip_from);
CREATE INDEX IF NOT EXISTS idx_asn_to         ON ip_asn(ip_to);
CREATE INDEX IF NOT EXISTS idx_proxy_from     ON ip_proxy(ip_from);
CREATE INDEX IF NOT EXISTS idx_proxy_to       ON ip_proxy(ip_to);
CREATE INDEX IF NOT EXISTS idx_ranges_country ON ip_ranges(country_code);
CREATE INDEX IF NOT EXISTS idx_ranges_city    ON ip_ranges(city);
CREATE INDEX IF NOT EXISTS idx_asn_name       ON ip_asn(as_name);
CREATE INDEX IF NOT EXISTS idx_proxy_type     ON ip_proxy(proxy_type);
"""

VIEW = """
DROP VIEW IF EXISTS view_ip_full;
CREATE VIEW view_ip_full AS
SELECT
    r.ip_from,
    r.ip_to,
    -- IP lisibles
    printf('%d.%d.%d.%d',
        (r.ip_from >> 24) & 255, (r.ip_from >> 16) & 255,
        (r.ip_from >>  8) & 255,  r.ip_from        & 255) AS ip_from_str,
    printf('%d.%d.%d.%d',
        (r.ip_to   >> 24) & 255, (r.ip_to   >> 16) & 255,
        (r.ip_to   >>  8) & 255,  r.ip_to          & 255) AS ip_to_str,
    -- Géo
    r.country_code,
    r.country_name,
    r.region,
    r.city,
    r.latitude,
    r.longitude,
    r.zip_code,
    r.timezone,
    -- ASN
    a.asn,
    a.as_name,
    a.cidr,
    -- Proxy
    p.proxy_type,
    p.usage_type,
    p.threat,
    p.provider,
    p.isp,
    -- Flags pratiques
    CASE WHEN p.proxy_type IS NOT NULL THEN 1 ELSE 0 END AS is_proxy,
    CASE WHEN p.proxy_type = 'TOR'     THEN 1 ELSE 0 END AS is_tor,
    CASE WHEN p.proxy_type = 'VPN'     THEN 1 ELSE 0 END AS is_vpn,
    CASE WHEN p.proxy_type = 'DCH'     THEN 1 ELSE 0 END AS is_datacenter
FROM ip_ranges r
LEFT JOIN ip_asn   a ON a.ip_from <= r.ip_from AND a.ip_to >= r.ip_from
LEFT JOIN ip_proxy p ON p.ip_from <= r.ip_from AND p.ip_to >= r.ip_from;
"""

# ═══════════════════════════════════════════════════════════════════════════════

def import_db11(conn, token):
    print(f"\n{c('── DB11 (IP → Pays+Région+Ville+LatLon+ZIP)', 'bold')}")
    zb  = download_zip(token, "DB11LITECSV")
    raw = extract_csv_from_zip(zb)
    rows = []
    for row in csv.reader(io.StringIO(raw), quotechar='"'):
        if len(row) < 9: continue
        try:
            rows.append((int(row[0]), int(row[1]),
                         row[2], row[3], row[4], row[5],
                         float(row[6]) if row[6] not in ('-','') else None,
                         float(row[7]) if row[7] not in ('-','') else None,
                         row[8],
                         row[9] if len(row) > 9 else None))
        except: pass
    batch_insert(conn,
        "INSERT INTO ip_ranges VALUES(?,?,?,?,?,?,?,?,?,?)",
        rows, label="DB11  ")
    print(f"  {c(f'{len(rows):,} plages insérées', 'green')}")

def import_asn(conn, token):
    print(f"\n{c('── ASN (Opérateurs / FAI)', 'bold')}")
    zb  = download_zip(token, "DBASNLITE")
    raw = extract_csv_from_zip(zb)
    rows = []
    for row in csv.reader(io.StringIO(raw), quotechar='"'):
        if len(row) < 5: continue
        try: rows.append((int(row[0]), int(row[1]), row[2], row[3], row[4]))
        except: pass
    batch_insert(conn,
        "INSERT INTO ip_asn VALUES(?,?,?,?,?)",
        rows, label="ASN   ")
    print(f"  {c(f'{len(rows):,} entrées ASN insérées', 'green')}")

def import_proxy(conn, token):
    print(f"\n{c('── PX11 (Proxy / VPN / TOR / Datacenter)', 'bold')}")
    zb  = download_zip(token, "PX11LITECSV")
    raw = extract_csv_from_zip(zb)
    rows = []
    for row in csv.reader(io.StringIO(raw), quotechar='"'):
        if len(row) < 3: continue
        try:
            r = row + [''] * 15  # pad si colonnes manquantes
            rows.append((int(r[0]), int(r[1]),
                         r[2], r[3], r[4], r[5], r[6],
                         r[7], r[8], r[9], r[10], r[11],
                         int(r[12]) if r[12].isdigit() else None,
                         r[13], r[14]))
        except: pass
    batch_insert(conn,
        "INSERT INTO ip_proxy VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows, label="Proxy ")
    print(f"  {c(f'{len(rows):,} plages proxy insérées', 'green')}")

def import_csv_i18n(conn, path, lang_hint=""):
    if not path or not os.path.exists(path):
        print(f"  {c(f'Skip {path or lang_hint} (non trouvé)', 'gray')}")
        return
    print(f"  {c('↑','cyan')} Import {os.path.basename(path)} ({lang_hint})...")
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, quotechar='"')
        next(reader, None)  # skip header
        for row in reader:
            if len(row) < 10: continue
            rows.append(tuple(row[:10]))
    batch_insert(conn,
        "INSERT INTO cities_i18n(country_code,country_numeric,country_name_en,"
        "region_code,region_name_en,city_name_en,lang_code,lang_name,"
        "region_name_local,city_name_local) VALUES(?,?,?,?,?,?,?,?,?,?)",
        rows, label=f"i18n  ")
    print(f"  {c(f'{len(rows):,} lignes i18n insérées', 'green')}")

def populate_countries(conn):
    print(f"\n{c('── Référentiel pays (depuis ip_ranges)', 'bold')}")
    conn.execute("""
        INSERT OR IGNORE INTO countries(code, name_en)
        SELECT DISTINCT country_code, country_name FROM ip_ranges
        WHERE country_code != ''
    """)
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM countries").fetchone()[0]
    print(f"  {c(f'{n} pays référencés', 'green')}")

def print_summary(conn, path):
    tables = [
        ("ip_ranges",   "🌐 Plages IP géolocalisées"),
        ("ip_asn",      "🏢 Plages ASN / opérateurs"),
        ("ip_proxy",    "🔒 Plages proxy / VPN / TOR"),
        ("cities_i18n", "🌍 Noms de villes multilingues"),
        ("countries",   "🚩 Pays référencés"),
    ]
    print(f"\n{c('═'*52, 'cyan')}")
    print(f"{c('  RÉSUMÉ FINAL', 'bold')}")
    print(f"{c('═'*52, 'cyan')}")
    for table, label in tables:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {label:<35} {c(f'{n:>10,}', 'bold')}")
        except: pass
    size = os.path.getsize(path) / (1024**2)
    print(f"\n  📁 {c(path, 'yellow')}  ({size:.1f} MB)")
    print(f"{c('═'*52, 'cyan')}\n")

    print(f"{c('  REQUÊTES UTILES DANS DATAGRIP :', 'bold')}\n")
    queries = [
        ("Lookup IP 8.8.8.8 (Google DNS)",
         "SELECT * FROM view_ip_full\nWHERE ip_from <= 134744072 AND ip_to >= 134744072;"),
        ("Top 10 pays par nombre de plages",
         "SELECT country_code, country_name, COUNT(*) as ranges\nFROM ip_ranges GROUP BY country_code ORDER BY ranges DESC LIMIT 10;"),
        ("Tous les TOR exit nodes",
         "SELECT ip_from_str, ip_to_str, country_name, city\nFROM view_ip_full WHERE is_tor = 1;"),
        ("Plages AWS / Azure / GCP",
         "SELECT ip_from_str, ip_to_str, as_name, country_name\nFROM view_ip_full\nWHERE as_name LIKE '%Amazon%' OR as_name LIKE '%Microsoft%' OR as_name LIKE '%Google%';"),
        ("Villes en chinois simplifié",
         "SELECT city_name_en, city_name_local, region_name_local, country_code\nFROM cities_i18n WHERE lang_code = 'ZH-CN' LIMIT 20;"),
    ]
    for title, sql in queries:
        print(f"  {c('▸', 'cyan')} {title}")
        for line in sql.split("\n"):
            print(f"    {c(line, 'gray')}")
        print()

# ═══════════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token",   required=True)
    ap.add_argument("--output",  default="ip_ultimate.db")
    ap.add_argument("--no-proxy",action="store_true")
    ap.add_argument("--no-asn",  action="store_true")
    ap.add_argument("--csv-en",  default="IP2LOCATION-COUNTRY-REGION-CITY.CSV")
    ap.add_argument("--csv-zhcn",default="IP2LOCATION-COUNTRY-REGION-CITY-ZH-CN.CSV")
    ap.add_argument("--csv-zhtw",default="IP2LOCATION-COUNTRY-REGION-CITY-ZH-TW.CSV")
    args = ap.parse_args()

    print(f"""
{c('╔══════════════════════════════════════════════════╗', 'cyan')}
{c('║   🌐  IP2LOCATION ULTIMATE IMPORTER             ║', 'cyan')}
{c('║   DB11 + ASN + Proxy + i18n → SQLite            ║', 'cyan')}
{c('╚══════════════════════════════════════════════════╝', 'cyan')}
  Sortie   : {c(args.output, 'yellow')}
  Proxy    : {c('oui', 'green') if not args.no_proxy else c('skip', 'gray')}
  ASN      : {c('oui', 'green') if not args.no_asn  else c('skip', 'gray')}
""")

    t0 = time.time()
    conn = sqlite3.connect(args.output)
    conn.executescript(SCHEMA)
    conn.commit()

    import_db11(conn, args.token)
    if not args.no_asn:   import_asn(conn, args.token)
    if not args.no_proxy: import_proxy(conn, args.token)

    print(f"\n{c('── Noms multilingues (CSV locaux)', 'bold')}")
    import_csv_i18n(conn, args.csv_en,   "EN")
    import_csv_i18n(conn, args.csv_zhcn, "ZH-CN")
    import_csv_i18n(conn, args.csv_zhtw, "ZH-TW")

    populate_countries(conn)

    print(f"\n{c('── Création des index...', 'bold')}")
    conn.executescript(INDEXES)
    print(f"\n{c('── Création de la vue view_ip_full...', 'bold')}")
    conn.executescript(VIEW)
    conn.commit()

    elapsed = time.time() - t0
    print(f"\n  {c(f'⏱ Terminé en {elapsed:.0f}s', 'yellow')}")
    print_summary(conn, args.output)
    conn.close()

if __name__ == "__main__":
    main()
