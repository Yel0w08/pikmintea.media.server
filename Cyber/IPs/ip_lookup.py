#!/usr/bin/env python3
"""
ip_lookup.py — CLI lookup sur ip_ultimate.db
Usage :
  python ip_lookup.py 8.8.8.8
  python ip_lookup.py 8.8.8.8 1.1.1.1 185.220.101.1   (batch)
  python ip_lookup.py --cidr 8.8.8.0/24
  python ip_lookup.py --interactive
  python ip_lookup.py --top-tor 20
  python ip_lookup.py --top-countries 10
  python ip_lookup.py --db autre_chemin.db 8.8.8.8
"""

import argparse, sqlite3, sys, struct, socket, os, time

DB_DEFAULT = "ip_ultimate.db"

C = {
    "reset":"\033[0m","bold":"\033[1m","dim":"\033[2m",
    "green":"\033[92m","yellow":"\033[93m","red":"\033[91m",
    "cyan":"\033[96m","blue":"\033[94m","gray":"\033[90m","white":"\033[97m",
}
def c(t, *codes): return "".join(C[x] for x in codes) + t + C["reset"]

def ip_to_int(ip):
    try: return struct.unpack("!I", socket.inet_aton(ip.strip()))[0]
    except: return None

def int_to_ip(n):
    return socket.inet_ntoa(struct.pack("!I", n))

def flag(cc):
    if not cc or len(cc) != 2: return "  "
    try: return "".join(chr(ord(ch)+127397) for ch in cc.upper())
    except: return "  "

def connect(path):
    if not os.path.exists(path):
        print(c(f"✗ DB introuvable : {path}", "red", "bold"))
        print(c(f"  Lance d'abord : python ip2location_ultimate.py --token TON_TOKEN", "dim"))
        sys.exit(1)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn

# ── lookup une IP ──────────────────────────────────────────────────────────────

def lookup(conn, ip, verbose=True):
    n = ip_to_int(ip)
    if n is None:
        print(c(f"  ✗ IP invalide : {ip}", "red"))
        return None

    t0 = time.perf_counter()

    # Essaie d'abord la view complète (si elle existe)
    try:
        row = conn.execute("""
            SELECT * FROM view_ip_full
            WHERE ip_from <= ? AND ip_to >= ?
            LIMIT 1
        """, (n, n)).fetchone()
    except:
        row = None

    # Fallback sur les tables séparées
    geo = proxy = asn = None
    if row:
        geo   = row
        asn   = row
        proxy = row
    else:
        geo = conn.execute("""
            SELECT * FROM ip_ranges
            WHERE ip_from <= ? AND ip_to >= ?
            LIMIT 1
        """, (n, n)).fetchone()
        try:
            asn = conn.execute("""
                SELECT * FROM ip_asn
                WHERE ip_from <= ? AND ip_to >= ?
                LIMIT 1
            """, (n, n)).fetchone()
        except: pass
        try:
            proxy = conn.execute("""
                SELECT * FROM ip_proxy
                WHERE ip_from <= ? AND ip_to >= ?
                LIMIT 1
            """, (n, n)).fetchone()
        except: pass

    elapsed = (time.perf_counter() - t0) * 1000

    if not verbose:
        return {"ip": ip, "geo": geo, "asn": asn, "proxy": proxy}

    print()
    print(c("─" * 52, "dim"))
    print(c(f"  lookup ", "dim") + c(ip, "bold", "white") +
          c(f"  ({n})", "dim") +
          c(f"  [{elapsed:.1f}ms]", "dim"))
    print(c("─" * 52, "dim"))

    if not geo:
        print(c("  ✗ IP non trouvée dans la base", "red"))
        return None

    # Géo
    cc   = dict(geo).get("country_code", "") or ""
    cn   = dict(geo).get("country_name", "") or ""
    reg  = dict(geo).get("region", "") or ""
    city = dict(geo).get("city", "") or ""
    lat  = dict(geo).get("latitude", "")
    lon  = dict(geo).get("longitude", "")
    zip_ = dict(geo).get("zip_code", "") or ""
    tz   = dict(geo).get("timezone", "") or ""

    def row(k, v, col="white"):
        print(f"  {c(k.ljust(18), 'dim')} {c(str(v), col)}")

    print(c("  Géolocalisation", "cyan", "bold"))
    row("pays",     f"{flag(cc)} {cn} ({cc})")
    row("région",   reg)
    row("ville",    city)
    if lat: row("lat / lon", f"{lat}, {lon}")
    if zip_: row("code postal", zip_)
    if tz:   row("timezone",   tz)

    # ASN
    if asn:
        asn_d = dict(asn)
        asn_num  = asn_d.get("asn", "") or ""
        asn_name = asn_d.get("as_name", "") or ""
        cidr     = asn_d.get("cidr", "") or ""
        if asn_num or asn_name:
            print()
            print(c("  Réseau / ASN", "blue", "bold"))
            if asn_num:  row("ASN",       asn_num)
            if asn_name: row("opérateur", asn_name)
            if cidr:     row("CIDR",      cidr)

    # Proxy
    print()
    print(c("  Sécurité", "yellow", "bold"))
    proxy_type = None
    if proxy:
        pd = dict(proxy)
        proxy_type = pd.get("proxy_type") or pd.get("type") or ""
        is_proxy   = pd.get("is_proxy", 1 if proxy_type else 0)
        is_tor     = pd.get("is_tor",   1 if proxy_type=="TOR" else 0)
        is_vpn     = pd.get("is_vpn",   1 if proxy_type=="VPN" else 0)
        is_dch     = pd.get("is_datacenter", 1 if proxy_type=="DCH" else 0)
        usage      = pd.get("usage_type","") or ""
        threat     = pd.get("threat","") or ""
        provider   = pd.get("provider","") or pd.get("isp","") or ""

        if proxy_type:
            labels = {"TOR": ("TOR exit node", "red"), "VPN": ("VPN commercial", "yellow"),
                      "DCH": ("datacenter",     "blue"), "SES": ("search engine", "dim"),
                      "RES": ("résidentiel",    "dim")}
            label, col = labels.get(proxy_type, (proxy_type, "yellow"))
            row("proxy type",  f"[{proxy_type}] {label}", col)
        if usage:   row("usage",   usage,  "yellow")
        if threat and threat not in ("-",""):
                    row("menace",  threat, "red")
        if provider: row("provider", provider)
        if not proxy_type:
            row("statut", "✓ clean — aucun proxy détecté", "green")
    else:
        row("statut", "✓ clean (pas dans la table proxy)", "green")

    # Range
    ip_from = dict(geo).get("ip_from")
    ip_to   = dict(geo).get("ip_to")
    if ip_from and ip_to:
        print()
        print(c(f"  range : {int_to_ip(ip_from)} → {int_to_ip(ip_to)}", "dim"))

    print(c("─" * 52, "dim"))
    return {"ip": ip, "geo": geo, "asn": asn, "proxy": proxy}

# ── batch ──────────────────────────────────────────────────────────────────────

def batch_lookup(conn, ips):
    print(f"\n  {c('IP'.ljust(18),'dim')} {c('Pays'.ljust(25),'dim')} {c('Ville'.ljust(20),'dim')} {c('ASN'.ljust(25),'dim')} {c('Proxy','dim')}")
    print(c("  " + "─"*90, "dim"))
    for ip in ips:
        n = ip_to_int(ip)
        if n is None:
            print(f"  {ip.ljust(18)} {c('IP invalide','red')}")
            continue
        try:
            row = conn.execute("""
                SELECT * FROM view_ip_full
                WHERE ip_from <= ? AND ip_to >= ? LIMIT 1
            """, (n, n)).fetchone()
        except:
            row = conn.execute("""
                SELECT * FROM ip_ranges
                WHERE ip_from <= ? AND ip_to >= ? LIMIT 1
            """, (n, n)).fetchone()

        if not row:
            print(f"  {ip.ljust(18)} {c('—','dim')}")
            continue

        d  = dict(row)
        cc = d.get("country_code","") or ""
        cn = d.get("country_name","") or ""
        ct = d.get("city","") or ""
        asn_name = d.get("as_name","") or ""
        pt = d.get("proxy_type","") or ""

        proxy_str = c(f"[{pt}]","red") if pt else c("clean","green")
        print(f"  {ip.ljust(18)} {(flag(cc)+' '+cn).ljust(25)} {ct.ljust(20)} {asn_name[:24].ljust(25)} {proxy_str}")

# ── CIDR scan ─────────────────────────────────────────────────────────────────

def cidr_scan(conn, cidr):
    base, bits = cidr.split("/")
    prefix = int(bits)
    base_n  = ip_to_int(base)
    mask    = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    net     = base_n & mask
    bcast   = net | (~mask & 0xFFFFFFFF)
    count   = bcast - net + 1

    print(f"\n  {c('CIDR scan','bold','cyan')} {cidr}")
    print(f"  réseau   : {int_to_ip(net)}  →  {int_to_ip(bcast)}")
    print(f"  adresses : {count:,}")
    print()

    rows = conn.execute("""
        SELECT country_code, country_name, city, COUNT(*) as n
        FROM ip_ranges
        WHERE ip_from >= ? AND ip_to <= ?
        GROUP BY country_code, city
        ORDER BY n DESC
        LIMIT 20
    """, (net, bcast)).fetchall()

    if not rows:
        print(c("  Aucune plage dans ce CIDR (ou CIDR trop large)", "dim"))
        return

    print(f"  {'Pays'.ljust(8)} {'Ville'.ljust(25)} {'Plages':>8}")
    print(c("  " + "─"*45, "dim"))
    for r in rows:
        d = dict(r)
        cc = d.get("country_code","") or ""
        cn = d.get("country_name","") or ""
        ct = d.get("city","") or ""
        n  = d.get("n", 0)
        print(f"  {(flag(cc)+cc).ljust(8)} {ct.ljust(25)} {n:>8,}")

# ── stats ──────────────────────────────────────────────────────────────────────

def show_stats(conn, kind, limit=10):
    queries = {
        "countries": (
            "Top pays par nombre de plages IP",
            """SELECT country_code, country_name, COUNT(*) as n
               FROM ip_ranges GROUP BY country_code ORDER BY n DESC LIMIT ?""",
            ["Code","Pays","Plages"]
        ),
        "tor": (
            "Exit nodes TOR",
            """SELECT ip_from, ip_to, country_name, city, isp
               FROM ip_proxy WHERE proxy_type='TOR' LIMIT ?""",
            ["De","À","Pays","Ville","ISP"]
        ),
        "asn": (
            "Top opérateurs par plages",
            """SELECT asn, as_name, COUNT(*) as n
               FROM ip_asn GROUP BY asn ORDER BY n DESC LIMIT ?""",
            ["ASN","Opérateur","Plages"]
        ),
        "vpn": (
            "VPN commerciaux connus",
            """SELECT ip_from, ip_to, country_name, city, provider, isp
               FROM ip_proxy WHERE proxy_type='VPN' LIMIT ?""",
            ["De","À","Pays","Ville","Provider","ISP"]
        ),
    }
    if kind not in queries:
        print(c(f"  Stats inconnues : {kind}. Choix : {', '.join(queries)}", "red"))
        return

    title, sql, cols = queries[kind]
    print(f"\n  {c(title, 'bold','cyan')}  (top {limit})\n")
    rows = conn.execute(sql, (limit,)).fetchall()
    if not rows:
        print(c("  Aucun résultat", "dim")); return

    col_w = [max(len(cols[i]), max(len(str(dict(r).get(r.keys()[i],"") or "")) for r in rows))+2
             for i in range(len(cols))]
    header = "  " + "".join(c(cols[i].ljust(col_w[i]), "dim") for i in range(len(cols)))
    print(header)
    print(c("  " + "─" * sum(col_w), "dim"))
    for row in rows:
        d = dict(row)
        vals = list(d.values())
        line = "  "
        for i, v in enumerate(vals):
            w = col_w[i] if i < len(col_w) else 15
            v_str = str(v) if v is not None else "—"
            if kind == "tor" and i == 0: v_str = int_to_ip(v) if v else "—"
            if kind == "tor" and i == 1: v_str = int_to_ip(v) if v else "—"
            line += v_str.ljust(w)
        print(line)

# ── interactive shell ──────────────────────────────────────────────────────────

def interactive(conn):
    print(f"\n  {c('IP2Location lookup interactif', 'bold','cyan')}")
    print(c("  Commandes : <ip>  |  batch <ip1> <ip2>  |  cidr <x.x.x.x/n>  |  tor|vpn|asn|countries  |  quit\n", "dim"))
    while True:
        try:
            line = input(c("  >>> ", "cyan","bold")).strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not line: continue
        if line in ("quit","exit","q"): break

        parts = line.split()
        cmd   = parts[0].lower()

        if cmd == "batch" and len(parts) > 1:
            batch_lookup(conn, parts[1:])
        elif cmd == "cidr" and len(parts) > 1:
            cidr_scan(conn, parts[1])
        elif cmd in ("tor","vpn","asn","countries"):
            lim = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 15
            show_stats(conn, cmd if cmd!="countries" else "countries", lim)
        elif cmd == "stats":
            k = parts[1] if len(parts)>1 else "countries"
            lim = int(parts[2]) if len(parts)>2 and parts[2].isdigit() else 10
            show_stats(conn, k, lim)
        else:
            # Traite comme une ou plusieurs IPs
            for ip in parts:
                lookup(conn, ip)

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="IP lookup sur ip_ultimate.db")
    ap.add_argument("ips",          nargs="*",       help="Une ou plusieurs IPs")
    ap.add_argument("--db",         default=DB_DEFAULT)
    ap.add_argument("--interactive",action="store_true", help="Shell interactif")
    ap.add_argument("--cidr",       metavar="CIDR",  help="Scan une plage CIDR")
    ap.add_argument("--batch",      nargs="+",       help="Lookup batch d'IPs")
    ap.add_argument("--top-countries", type=int,     metavar="N")
    ap.add_argument("--top-tor",    type=int,        metavar="N")
    ap.add_argument("--top-asn",    type=int,        metavar="N")
    ap.add_argument("--top-vpn",    type=int,        metavar="N")
    args = ap.parse_args()

    conn = connect(args.db)

    if args.interactive:
        interactive(conn)
    elif args.cidr:
        cidr_scan(conn, args.cidr)
    elif args.batch:
        batch_lookup(conn, args.batch)
    elif args.top_countries:
        show_stats(conn, "countries", args.top_countries)
    elif args.top_tor:
        show_stats(conn, "tor", args.top_tor)
    elif args.top_asn:
        show_stats(conn, "asn", args.top_asn)
    elif args.top_vpn:
        show_stats(conn, "vpn", args.top_vpn)
    elif args.ips:
        if len(args.ips) == 1:
            lookup(conn, args.ips[0])
        else:
            batch_lookup(conn, args.ips)
    else:
        interactive(conn)

    conn.close()

if __name__ == "__main__":
    main()
