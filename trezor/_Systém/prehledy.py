#!/usr/bin/env python3
"""Poznámky a přehledy bez AI (lokálně, nic se nikam neposílá).

  python3 _Systém/prehledy.py --poznamka "Předmět/materiál.pdf"   # poznámka z šablony s vyplněným předmětem, kódem a zdrojem
  python3 _Systém/prehledy.py --tyden                              # týdenní přehled do _Přehledy
  python3 _Systém/prehledy.py --zkouska "Předmět"                  # shrnutí, pojmy a kartičky předmětu v jedné poznámce
  python3 _Systém/prehledy.py --kalendar                           # termíny do _Systém/Termíny.ics (import do kalendáře)
  python3 _Systém/prehledy.py --citace '{"typ": "kniha", ...}'     # citace ČSN ISO 690 + poznámka v _Zdroje

Vygenerovaný obsah je mezi značkami <!-- druhy-mozek … -->; při dalším generování se přepíše jen ten,
co uživatel napíše mimo značky, zůstane.
"""
import argparse
import datetime
import hashlib
import json
import re
import sys
import urllib.parse

sys.dont_write_bytecode = True
import priprav as P  # noqa: E402  (stejná složka – frontmatter, poznámky, materiály, texty)
import predmety  # noqa: E402

TREZOR = P.TREZOR
T = P.texty()
DNES = datetime.date.today()
ZACATEK = "<!-- druhy-mozek: začátek – generuje se -->"
KONEC = "<!-- druhy-mozek: konec -->"


def bezpecna(rel):
    return bool(rel) and not rel.startswith("/") and ".." not in rel.split("/")


def odkaz(rel, popis=None):
    cil = rel[:-3] if rel.endswith(".md") else rel
    return f"[[{cil}|{popis}]]" if popis else f"[[{cil}]]"


def zapis_generovane(cesta, hlavicka, telo, pod=""):
    """Zapíše vygenerovaný blok; existující text mimo značky zachová."""
    blok = f"{ZACATEK}\n> {T['generovano'].format(d=DNES.isoformat())}\n\n{telo.rstrip()}\n{KONEC}"
    if cesta.exists():
        puvodni = cesta.read_text(encoding="utf8")
        if ZACATEK in puvodni and KONEC in puvodni:
            pred, zbytek = puvodni.split(ZACATEK, 1)
            cesta.write_text(pred + blok + zbytek.split(KONEC, 1)[1], encoding="utf8")
            return
    cesta.parent.mkdir(parents=True, exist_ok=True)
    cesta.write_text(f"{hlavicka}\n{blok}\n{pod}", encoding="utf8")


def ukoly():
    for p, rel in P.poznamky():
        fm = P.frontmatter(p)
        if fm.get("typ") in ("ukol", "zkouska") and fm.get("stav") != "hotovo":
            try:
                termin = datetime.date.fromisoformat(fm.get("termin", "")[:10])
            except ValueError:
                termin = None
            yield rel, fm, termin


def kdy(termin):
    dni = (termin - DNES).days
    return T["dnes"] if dni == 0 else T["zitra"] if dni == 1 else T["za_dni"].format(n=dni) if dni > 0 else T["pred_dny"].format(n=-dni)


# ---------- 📝 poznámka k materiálu ----------

def poznamka(material):
    material = P.nfc(material)
    zdroj = TREZOR / material
    predmet = material.split("/")[0]
    seznam = {p["nazev"]: p["kod"] for p in predmety.seznam()}
    if not bezpecna(material) or not zdroj.is_file() or predmet not in seznam:
        sys.exit(T["chyba_material"].format(p=material))
    for p, rel in P.poznamky():  # k materiálu už poznámka je → nezakládat druhou
        if rel.startswith(predmet + "/") and P.frontmatter(p).get("zdroj", "").strip("[]").split("|")[0] in (material, zdroj.name):
            print(T["poznamka_existuje"].format(p=rel))
            print(rel)
            return rel
    kod = seznam[predmet]
    slozka = TREZOR / predmet / "Poznámky"
    slozka.mkdir(parents=True, exist_ok=True)
    cisla = [int(m.group(1)) for f in slozka.glob("*.md") if (m := re.match(rf"^{re.escape(kod)}\s*(\d+)\b", f.stem))] if kod else []
    nn = max(cisla, default=0) + 1
    nazev = re.sub(r"\s+", " ", re.sub(r"[_]+", " ", zdroj.stem)).strip()
    nazev = re.sub(r'[/\\:*?"<>|#^\[\]]', "-", nazev)[:80]
    jmeno = f"{kod} {nn:02d} – {nazev}" if kod else f"{nn:02d} – {nazev}"
    sablona = (TREZOR / "_Systém" / "Šablony" / "Přednáška.md").read_text(encoding="utf8")
    hlava, telo = sablona.split("---", 2)[1:]
    nastav = {"predmet": json.dumps(f"[[{predmet}]]", ensure_ascii=False), "kod": kod,
              "datum": DNES.isoformat(), "zdroj": json.dumps(f"[[{material}|{zdroj.name}]]", ensure_ascii=False)}
    for k, v in nastav.items():
        hlava = re.sub(rf"^{k}:.*$", lambda _: f"{k}: {v}", hlava, flags=re.M)  # lambda: \ v textu není escape
    telo = telo.replace("{{title}}", jmeno).replace("{{date}}", DNES.isoformat())
    cil = slozka / f"{jmeno}.md"
    cil.write_text(f"---{hlava}---{telo}", encoding="utf8")
    rel = P.nfc(str(cil.relative_to(TREZOR)))
    with open(P.ZAMEK, "w") as zamek:  # materiál má poznámku → ve frontě odškrtnout (stejný zámek jako priprav.py)
        P.fcntl.flock(zamek, P.fcntl.LOCK_EX)
        P.oznac(material, "hotovo")
    print(T["poznamka_hotovo"].format(p=rel))
    print(rel)
    return rel


# ---------- 🗓 týdenní přehled ----------

def tyden():
    rok, cislo, _ = DNES.isocalendar()
    od = DNES - datetime.timedelta(days=DNES.weekday())
    do = od + datetime.timedelta(days=6)
    terminy, po = [], []
    for rel, fm, termin in sorted(ukoly(), key=lambda x: x[2] or datetime.date.max):
        if termin is None:
            continue
        radek = f"- [ ] **{termin.isoformat()}** ({kdy(termin)}) · {fm.get('kod', '')} · {odkaz(rel)}"
        if termin < DNES:
            po.append(radek)
        elif (termin - DNES).days <= 14:
            terminy.append(radek)
    hranice = DNES - datetime.timedelta(days=7)
    nove = [f"- {odkaz(rel, rel.split('/')[-1])} · {rel.split('/')[0]}" for p, rel in P.materialy()
            if datetime.date.fromtimestamp(p.stat().st_mtime) >= hranice]
    napsano = [f"- {odkaz(rel)}" for p, rel in P.poznamky()
               if datetime.date.fromtimestamp(p.stat().st_mtime) >= hranice and not rel.startswith(("_Přehledy/", "00 ", "01 "))]
    try:
        fronta = len(json.loads((TREZOR / "_Systém" / "fronta.json").read_text()))
    except Exception:
        fronta = 0
    nic = T["nic"]
    telo = "\n".join([
        f"## {T['h_po_terminu']}", *(po or [nic]), "",
        f"## {T['h_terminy']}", *(terminy or [nic]), "",
        f"## {T['h_nove']}", *(nove or [nic]), "",
        f"## {T['h_napsano']}", *(napsano[:40] or [nic]), "",
        f"## {T['h_fronta']}", T["fronta_stav"].format(n=fronta),
    ])
    cil = TREZOR / "_Přehledy" / f"{T['tyden_soubor'].format(r=rok, t=f'{cislo:02d}')}.md"
    hlavicka = (f"---\ntyp: prehled\ndatum: {DNES.isoformat()}\ntags:\n  - prehled\n---\n"
                f"# {T['tyden_nadpis'].format(t=cislo, od=od.strftime('%d. %m.'), do=do.strftime('%d. %m. %Y'))}\n")
    zapis_generovane(cil, hlavicka, telo, f"\n## {T['h_moje']}\n\n\n## {T['h_pristi']}\n- [ ] \n")
    rel = P.nfc(str(cil.relative_to(TREZOR)))
    print(rel)
    return rel


# ---------- 🎓 příprava na zkoušku ----------

def sekce(text, nadpis):
    m = re.search(rf"^## {re.escape(nadpis)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def zkouska(predmet):
    seznam = {p["nazev"]: p["kod"] for p in predmety.seznam()}
    if predmet not in seznam:
        sys.exit(T["chyba_predmet"].format(p=predmet) if "chyba_predmet" in T else predmet)
    kod = seznam[predmet]
    # nadpisy sekcí podle šablony v jazyce trezoru: 0 shrnutí, 2 klíčové pojmy, 4 kartičky
    nadpisy = re.findall(r"^## (.+)$", (TREZOR / "_Systém/Šablony/Přednáška.md").read_text(encoding="utf8"), re.M)
    h_shrnuti, h_pojmy = nadpisy[0], nadpisy[2]
    poznamky = sorted((p, rel) for p, rel in P.poznamky()
                      if rel.startswith(predmet + "/") and P.frontmatter(p).get("typ") == "prednaska")
    shrnuti, pojmy, karticky = [], {}, []
    for p, rel in poznamky:
        text = p.read_text(encoding="utf8", errors="ignore")
        bez_kodu = re.sub(r"```.*?```", "", text, flags=re.S)
        s = sekce(bez_kodu, h_shrnuti)
        shrnuti += [f"### {odkaz(rel, p.stem)}", s or "–", ""]
        for poj in re.findall(r"\[\[([^\]|#]+)", sekce(bez_kodu, h_pojmy)):
            if poj.strip():
                pojmy.setdefault(poj.strip(), p.stem)
        karticky += [r.strip() for r in bez_kodu.splitlines() if "::" in r and not r.strip().startswith(("#", ">", "|"))]
    terminy = [f"- **{t.isoformat() if t else '—'}** · {odkaz(rel)}" for rel, fm, t in ukoly() if rel.startswith(predmet + "/")]
    telo = "\n".join([
        f"## {T['h_prehled']}", f"- {odkaz(f'{predmet}/{predmet}.md', predmet)} · {kod}", *terminy,
        f"- {T['zkouska_info'].format(n=len(poznamky))}" if poznamky else f"- {T['zkouska_zadne']}", "",
        f"## {T['h_shrnuti']}", *shrnuti, "",
        f"## {T['h_pojmy']}", *([f"- [[{k}]]" for k in sorted(pojmy)] or [T["nic"]]), "",
        f"## {T['h_karticky']} #flashcards/{kod or 'zkouska'}", *(karticky or [T["nic"]]),
    ])
    cil = TREZOR / predmet / f"{T['zkouska_prefix']}{predmet}.md"
    hlavicka = (f"---\ntyp: zkouska-pruvodce\npredmet: \"[[{predmet}]]\"\nkod: {kod}\ndatum: {DNES.isoformat()}\n"
                f"tags:\n  - zkouska\n---\n# {T['zkouska_nadpis'].format(p=predmet)}\n")
    zapis_generovane(cil, hlavicka, telo, f"\n## {T['h_otazky']}\n- \n")
    rel = P.nfc(str(cil.relative_to(TREZOR)))
    print(rel)
    return rel


# ---------- 📅 kalendář ----------

def ics_text(s):
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def kalendar():
    trezor = TREZOR.name
    radky = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Druhy mozek//KISK//CS", "CALSCALE:GREGORIAN",
             f"X-WR-CALNAME:{ics_text(T['ics_nazev'])}"]
    pocet = 0
    for rel, fm, termin in ukoly():
        if termin is None:
            continue
        uid = hashlib.sha1(rel.encode()).hexdigest()[:20] + "@druhy-mozek"
        nazev = re.sub(r"\.md$", "", rel.split("/")[-1])
        url = "obsidian://open?" + urllib.parse.urlencode({"vault": trezor, "file": rel[:-3] if rel.endswith(".md") else rel},
                                                          quote_via=urllib.parse.quote)
        radky += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}",
                  f"DTSTART;VALUE=DATE:{termin:%Y%m%d}", f"DTEND;VALUE=DATE:{termin + datetime.timedelta(days=1):%Y%m%d}",
                  f"SUMMARY:{ics_text((fm.get('kod', '') + ' – ' if fm.get('kod') else '') + nazev)}",
                  f"URL:{url}", f"DESCRIPTION:{ics_text(rel)}",
                  "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{ics_text(T['ics_pripominka'])}", "TRIGGER:-PT12H", "END:VALARM",
                  "END:VEVENT"]
        pocet += 1
    radky.append("END:VCALENDAR")
    cil = TREZOR / "_Systém" / "Termíny.ics"
    cil.write_text("\r\n".join(radky) + "\r\n", encoding="utf8")
    print(T["kalendar_hotovo"].format(n=pocet, p="_Systém/Termíny.ics"))
    print("_Systém/Termíny.ics")
    return pocet


# ---------- 📚 citace (ČSN ISO 690) ----------

def autori(text):
    lide = [a.strip() for a in re.split(r";", text or "") if a.strip()]
    def jmeno(a, prvni):
        if "," not in a:  # organizace nebo jedno jméno
            return a.upper() if prvni else a
        prijmeni, krestni = [x.strip() for x in a.split(",", 1)]
        return f"{prijmeni.upper()}, {krestni}" if prvni else f"{krestni} {prijmeni.upper()}"
    if not lide:
        return ""
    if len(lide) > 3:
        return f"{jmeno(lide[0], True)} et al."
    casti = [jmeno(a, i == 0) for i, a in enumerate(lide)]
    return casti[0] if len(casti) == 1 else ", ".join(casti[:-1]) + f" {T['c_a']} " + casti[-1]


def citace(d):
    g = lambda k: str(d.get(k) or "").strip()
    typ, aut = g("typ") or "kniha", autori(g("autori"))
    nazev = g("nazev") + (f": {g('podnazev')}" if g("podnazev") else "")
    cit = f"[{T['c_cit']} {g('cit_datum') or DNES.isoformat()}]"
    online = f" [{T['c_online']}]" if g("url") else ""
    vydani = f"{g('vydani')}. {T['c_vyd']}" if g("vydani").isdigit() else g("vydani")
    nakl = ": ".join(x for x in (g("misto"), g("nakladatel")) if x)
    konec = []
    if g("doi"):
        konec.append(f"DOI: {g('doi')}.")
    if g("url"):
        konec.append(f"{T['c_dostupne']}: {g('url')}")
    if typ == "clanek":
        cast = ", ".join(x for x in (g("rok"), f"{T['c_roc']} {g('rocnik')}" if g("rocnik") else "",
                                     f"{T['c_cis']} {g('cislo')}" if g("cislo") else "", f"{T['c_s']} {g('strany')}" if g("strany") else "") if x)
        s = f"{aut}. {nazev}. *{g('casopis')}*{online}. {cast}" + (f" {cit}" if g("url") else "") + "."
        s += f" ISSN {g('issn')}." if g("issn") else ""
    elif typ == "web":
        vyd = ", ".join(x for x in (nakl, g("rok")) if x)
        s = (f"{aut}. " if aut else "") + f"*{nazev}*{online or ' [' + T['c_online'] + ']'}. " + (f"{vyd} " if vyd else "") + f"{cit}."
    elif typ == "kapitola":
        ed = autori(g("editori"))
        s = (f"{aut}. {nazev}. {T['c_in']} " + (f"{ed}, {T['c_ed']} " if ed else "") + f"*{g('kniha')}*{online}. "
             + (f"{vydani}. " if vydani else "") + ", ".join(x for x in (nakl, g("rok"), f"{T['c_s']} {g('strany')}" if g("strany") else "") if x)
             + (f" {cit}" if g("url") else "") + ".")
        s += f" ISBN {g('isbn')}." if g("isbn") else ""
    else:  # kniha
        s = (f"{aut}. *{nazev}*{online}. " + (f"{vydani}. " if vydani else "") + ", ".join(x for x in (nakl, g("rok")) if x)
             + (f" {cit}" if g("url") else "") + ".")
        s += f" ISBN {g('isbn')}." if g("isbn") else ""
    s = re.sub(r"\.\.+", ".", re.sub(r"\s+", " ", " ".join([s, *konec]))).strip()
    return s


def do_nazvu(text, delka):
    """Text do názvu souboru: bez lomítek, řídicích znaků a znaků, které Obsidian v názvu nesnese; nezačíná tečkou."""
    text = re.sub(r'[/\\:*?"<>|#^\[\]\x00-\x1f\x7f]', "-", str(text or ""))
    return text[:delka].strip().lstrip(".").strip()


def citace_poznamka(data):
    c = citace(data)
    prvni = do_nazvu(re.split(r"[;,]", str(data.get("autori") or ""))[0], 40)
    jmeno = " ".join(x for x in (prvni, do_nazvu(data.get("rok"), 10)) if x)
    titul = do_nazvu(data.get("nazev"), 70) or "zdroj"
    zdroje = TREZOR / "_Zdroje"
    cil = zdroje / f"{jmeno + ' – ' if jmeno else ''}{titul}.md"
    if cil.resolve().parent != zdroje.resolve():  # pojistka: poznámka ke zdroji vždy jen v _Zdroje
        sys.exit("_Zdroje?")
    if not cil.exists():
        sablona = (TREZOR / "_Systém" / "Šablony" / "Zdroj.md").read_text(encoding="utf8")
        hlava, telo = sablona.split("---", 2)[1:]
        autor = "autor: " + json.dumps(data.get("autori") or "", ensure_ascii=False)  # \u0001 apod. → přes lambda,
        odkaz = "odkaz: " + json.dumps(data.get("url") or "", ensure_ascii=False)     # jinak re.PatternError
        hlava = re.sub(r"^autor:.*$", lambda _: autor, hlava, flags=re.M)
        hlava = re.sub(r"^odkaz:.*$", lambda _: odkaz, hlava, flags=re.M)
        hlava = hlava.rstrip("\n") + "\ncitace: " + json.dumps(c, ensure_ascii=False) + "\n"
        telo = telo.replace("{{title}}", titul, 1)
        prvni_nadpis = telo.index("\n", telo.index("# ")) + 1
        telo = telo[:prvni_nadpis] + f"\n> [!quote] {T['c_nadpis_citace']}\n> {c}\n" + telo[prvni_nadpis:]
        cil.parent.mkdir(parents=True, exist_ok=True)
        cil.write_text(f"---{hlava}---{telo}", encoding="utf8")
    print(T["citace_hotovo"].format(c=c))
    print(P.nfc(str(cil.relative_to(TREZOR))))
    return c


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--poznamka", metavar="MATERIÁL")
    g.add_argument("--tyden", action="store_true")
    g.add_argument("--zkouska", metavar="PŘEDMĚT")
    g.add_argument("--kalendar", action="store_true")
    g.add_argument("--citace", metavar="JSON")
    arg = a.parse_args()
    if arg.poznamka is not None:  # i prázdný argument – jinak by spadl do --citace
        poznamka(arg.poznamka)
    elif arg.tyden:
        tyden()
    elif arg.zkouska is not None:
        zkouska(P.nfc(arg.zkouska))
    elif arg.kalendar:
        kalendar()
    elif arg.citace is not None:
        try:
            data = json.loads(arg.citace)
        except ValueError:
            sys.exit("JSON?")
        citace_poznamka(data if isinstance(data, dict) else {})
