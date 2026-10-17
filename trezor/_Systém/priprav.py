#!/usr/bin/env python3
"""Spořič dat pro druhý mozek.

Lokálně (zdarma, bez AI) projde materiály v trezoru, z nových nebo změněných
souborů vytáhne čistý text do _Systém/cache a sestaví frontu k zpracování.
AI pak čte jen tenhle text, ne celé PDF nebo prezentace.

Použití:
  python3 _Systém/priprav.py                 # aktualizuje cache a frontu, vypíše souhrn
  python3 _Systém/priprav.py --hotovo CESTA  # označí soubor jako zpracovaný
  python3 _Systém/priprav.py --preskoc CESTA # označí soubor jako přeskočený (vlastní práce, osnova…)
  python3 _Systém/priprav.py --presun SOUBOR PŘEDMĚT  # přesune soubor z _Inbox do složky předmětu
  python3 _Systém/priprav.py --zmenene 7     # poznámky změněné za posledních N dní
  python3 _Systém/priprav.py --ukoly         # otevřené úkoly s termíny

Bezpečné náhrady za mv/find, aby AI nepotřebovala obecné příkazy shellu.
"""
import fcntl
import hashlib
import html
import json
import plistlib
import shutil
import time
import re
import subprocess
import sys
import unicodedata
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

TREZOR = Path(__file__).resolve().parent.parent
SYS = TREZOR / "_Systém"
CACHE = SYS / "cache"
REGISTR = SYS / "registr.json"
FRONTA = SYS / "Fronta.md"

TEXTOVE = {".pdf", ".pptx", ".docx", ".doc", ".rtf", ".txt", ".webloc"}
OBRAZKY = {".png", ".jpg", ".jpeg", ".heic", ".webp"}
VYNECHAT = {"_Systém", "_Pojmy", "_Přehledy", "_Zdroje", "_Archiv", "Poznámky", ".obsidian", ".claude", ".trash"}
VELKE = 30_000  # odhad tokenů, od kterého se soubor zpracuje jen jako shrnutí
MAX_CAST = 50_000_000  # max. velikost jedné rozbalené části pptx/docx (ochrana proti zip bombě)
NASTAVENI = SYS / "nastaveni.json"
VLASTNI_PREFIX = (json.loads(NASTAVENI.read_text())["uco"] + "-") if NASTAVENI.exists() else None
ZAMEK = SYS / ".priprav.lock"

PDF_JXA = """
ObjC.import('PDFKit');
function run(argv) {
  const doc = $.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(argv[0]));
  if (!doc || doc.isNil()) return '';
  const out = [];
  for (let i = 0; i < doc.pageCount; i++) {
    const s = doc.pageAtIndex(i).string;
    out.push('=== strana ' + (i + 1) + ' ===\\n' + (s && !s.isNil() ? ObjC.unwrap(s) : ''));
  }
  return out.join('\\n');
}
"""


def nfc(s):
    return unicodedata.normalize("NFC", s)


def tokeny(text):
    # čeština se tokenizuje hůř než angličtina, ~3 znaky na token
    return len(text) // 3


def otisk(cesta):
    h = hashlib.sha256()
    with open(cesta, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def precti_cast(z, nazev):
    if z.getinfo(nazev).file_size > MAX_CAST:
        raise ValueError(f"část {nazev} je podezřele velká – přeskakuji")
    return z.read(nazev).decode("utf8", "ignore")


def xml_odstavce(xml, odstavec, text_tag):
    vysledek = []
    for p in re.split(rf"</{odstavec}>", xml):
        kusy = re.findall(rf"<{text_tag}(?: [^>]*)?>([^<]*)</{text_tag}>", p)
        radek = html.unescape("".join(kusy)).strip()
        if radek:
            vysledek.append(radek)
    return vysledek


def z_pptx(cesta):
    bloky = []
    with zipfile.ZipFile(cesta) as z:
        slajdy = sorted(
            (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)),
        )
        for i, n in enumerate(slajdy, 1):
            radky = xml_odstavce(precti_cast(z, n), "a:p", "a:t")
            rels = n.replace("slides/", "slides/_rels/") + ".rels"
            if rels in z.namelist():
                m = re.search(r'Target="\.\./notesSlides/(notesSlide\d+\.xml)"', precti_cast(z, rels))
                if m:
                    pozn = xml_odstavce(precti_cast(z, "ppt/notesSlides/" + m.group(1)), "a:p", "a:t")
                    pozn = [r for r in pozn if not r.isdigit()]
                    if pozn:
                        radky += ["[poznámky řečníka] " + " ".join(pozn)]
            bloky.append(f"=== slajd {i} ===\n" + "\n".join(radky))
    return bloky


def z_docx(cesta):
    with zipfile.ZipFile(cesta) as z:
        xml = precti_cast(z, "word/document.xml")
    radky = []
    for p in xml.split("</w:p>"):
        text = html.unescape("".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", p))).strip()
        if not text:
            continue
        styl = re.search(r'<w:pStyle w:val="(?:Heading|Nadpis)(\d)"', p)
        radky.append(("#" * int(styl.group(1)) + " " if styl else "") + text)
    return ["\n".join(radky)]


def z_pdf(cesta):
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", PDF_JXA, str(cesta)],
                       capture_output=True, text=True, timeout=300)
    text = r.stdout.strip()
    return [b for b in re.split(r"(?==== strana \d+ ===)", text) if b.strip()]


def z_textutil(cesta):
    r = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(cesta)],
                       capture_output=True, text=True, timeout=120)
    return [r.stdout]


def z_webloc(cesta):
    with open(cesta, "rb") as f:
        return ["Odkaz: " + plistlib.load(f).get("URL", "")]


def vycisti(bloky):
    """Odstraní opakující se zápatí/záhlaví a prázdné řádky – to nejvíc šetří."""
    pocty = Counter(r.strip() for b in bloky for r in set(b.splitlines()[1:]) if r.strip())
    hranice = max(3, len(bloky) * 0.3)
    opakovane = {r for r, n in pocty.items() if n >= hranice and len(bloky) >= 4}
    ciste = []
    for b in bloky:
        radky = b.splitlines()
        hlava, telo = (radky[0], radky[1:]) if radky and radky[0].startswith("===") else ("", radky)
        telo = [re.sub(r"[ \t]+", " ", r).strip() for r in telo]
        telo = [r for r in telo if r and r not in opakovane and not re.fullmatch(r"\d{1,3}", r)]
        if telo:
            ciste.append((hlava + "\n" if hlava else "") + "\n".join(telo))
    return "\n\n".join(ciste), len(opakovane)


def extrahuj(cesta):
    pripona = cesta.suffix.lower()
    if pripona == ".pptx":
        return z_pptx(cesta), "prezentace"
    if pripona == ".docx":
        return z_docx(cesta), "dokument"
    if pripona == ".pdf":
        return z_pdf(cesta), "pdf"
    if pripona == ".webloc":
        return z_webloc(cesta), "odkaz"
    return z_textutil(cesta), "text"


def texty():
    """Texty pro Fronta.md a výpis v jazyce z nastaveni.json (cs, sk, en, uk); chybějící doplní čeština."""
    jazyk = "cs"
    try:
        jazyk = json.loads(NASTAVENI.read_text()).get("jazyk") or "cs"
    except Exception:
        pass
    data = json.loads((SYS / "texty.json").read_text(encoding="utf8"))
    return {**data["cs"], **data.get(jazyk, {})}


def podpis(p):
    st = p.stat()
    return {"velikost": st.st_size, "zmeneno": int(st.st_mtime)}


def nacti_registr():
    return json.loads(REGISTR.read_text()) if REGISTR.exists() else {}


def uloz_registr(reg):
    REGISTR.write_text(json.dumps(reg, ensure_ascii=False, indent=1, sort_keys=True))


def materialy():
    for p in sorted(TREZOR.rglob("*")):
        rel = p.relative_to(TREZOR)
        if not p.is_file() or set(rel.parts[:-1]) & VYNECHAT or p.name.startswith("."):
            continue
        if len(rel.parts) == 1:  # soubory v kořeni trezoru (Domov apod.)
            continue
        if p.name.startswith(("~$", ".~lock")):  # dočasné soubory otevřených dokumentů
            continue
        if VLASTNI_PREFIX and p.name.startswith(VLASTNI_PREFIX):  # vlastní práce vytvořené ze šablony
            continue
        if p.suffix.lower() in TEXTOVE | OBRAZKY:
            yield p, nfc(str(rel))


def oznac(cesta, stav):
    reg = nacti_registr()
    rel = nfc(str(Path(cesta).resolve().relative_to(TREZOR))) if Path(cesta).is_absolute() else nfc(cesta)
    p = TREZOR / rel
    if not p.exists():
        sys.exit(f"Soubor neexistuje: {rel}")
    reg[rel] = {"otisk": otisk(p), "stav": stav, "datum": date.today().isoformat(), **podpis(p)}
    uloz_registr(reg)
    print(f"{stav}: {rel}")


def prehled():
    CACHE.mkdir(parents=True, exist_ok=True)
    reg = nacti_registr()
    hotove_otisky = {v["otisk"]: k for k, v in reg.items() if v["stav"] in ("hotovo", "preskoceno")}
    fronta, uspora_puvodni, uspora_cista, videne = [], 0, 0, {}

    for p, rel in materialy():
        zaznam = reg.get(rel)
        stejny = zaznam and {k: zaznam.get(k) for k in ("velikost", "zmeneno")} == podpis(p)
        if stejny and zaznam["stav"] != "ceka":
            continue  # beze změny od minula – otisk není potřeba znovu počítat
        h = zaznam["otisk"] if stejny else otisk(p)
        if zaznam and zaznam["otisk"] == h and zaznam["stav"] != "ceka":
            zaznam.update(podpis(p))
            continue
        if h in hotove_otisky and hotove_otisky[h] != rel:
            reg[rel] = {"otisk": h, "stav": "duplicita", "datum": date.today().isoformat(),
                        "stejne_jako": hotove_otisky[h], **podpis(p)}
            continue
        if h in videne:  # stejný soubor podruhé pod jiným jménem
            reg[rel] = {"otisk": h, "stav": "duplicita", "datum": date.today().isoformat(),
                        "stejne_jako": videne[h], **podpis(p)}
            print(f"  ! duplicita: {rel} = {videne[h]}")
            continue
        videne[h] = rel

        pripona = p.suffix.lower()
        polozka = {"soubor": rel, "predmet": rel.split("/")[0], "velikost_mb": round(p.stat().st_size / 1e6, 1)}
        if pripona in OBRAZKY:
            polozka.update(typ="obrázek", tokeny=1600, slova=0, cache=None, poznamka="AI přečte obrázek přímo")
            uspora_puvodni += 1600
            uspora_cista += 1600
        else:
            cil = CACHE / f"{h[:16]}.md"
            if not cil.exists():
                try:
                    bloky, typ = extrahuj(p)
                except Exception as e:  # poškozený nebo zamčený soubor
                    bloky, typ = [], f"chyba: {e}"
                text, odstraneno = vycisti(bloky)
                cil.write_text(f"<!-- zdroj: {rel} | typ: {typ} | bloků: {len(bloky)} | "
                               f"odstraněno opakujících se řádků: {odstraneno} -->\n\n{text}\n")
            text = cil.read_text()
            hlava = text.split("\n", 1)[0]
            typ = re.search(r"typ: ([^|]+)", hlava).group(1).strip()
            bloku = int(re.search(r"bloků: (\d+)", hlava).group(1))
            t = tokeny(text)
            poznamka = ""
            if typ == "pdf" and bloku and len(text) / bloku < 80:
                poznamka = "SKEN – text chybí, číst obrazem jen vybrané strany"
            elif t > VELKE:
                poznamka = "VELKÉ – zpracovat jen jako shrnutí"
            # odhad, kolik by stálo čtení originálu (PDF/prezentace AI čte i jako obrázky)
            puvodni = t + (bloku * 1500 if typ in ("pdf", "prezentace") else 0)
            uspora_puvodni += puvodni
            uspora_cista += t
            polozka.update(typ=typ, tokeny=t, slova=len(text.split()), cache=str(cil.relative_to(TREZOR)), poznamka=poznamka)
        reg[rel] = {"otisk": h, "stav": "ceka", "datum": date.today().isoformat(), **podpis(p)}
        fronta.append(polozka)

    # záznamy smazaných souborů už nepotřebujeme
    existujici = {rel for _, rel in materialy()}
    for rel in [k for k in reg if k not in existujici]:
        del reg[rel]
    uloz_registr(reg)

    stavy = Counter(v["stav"] for v in reg.values())
    vyrizeno = stavy["hotovo"] + stavy["preskoceno"] + stavy["duplicita"]
    celkem = vyrizeno + len(fronta)
    T = texty()
    cislo = lambda n: f"{n:,}".replace(",", " ")
    # bez AI nemají tokeny smysl → místo nich odhad času čtení (~200 slov za minutu)
    try:
        bez_ai = json.loads(NASTAVENI.read_text()).get("ai") == "zadna"
    except Exception:
        bez_ai = False
    minuty = lambda f: max(1, round(f.get("slova", 0) / 200))
    # poznámky ve fronta.json zůstávají česky (čte je AI), do Fronta.md jdou v jazyce uživatele
    pozn_preklad = {"SKEN": T["pozn_sken"], "VELKÉ": T["pozn_velke"], "AI přečte": T["pozn_obrazek"]}
    preloz = lambda text: next((v for k, v in pozn_preklad.items() if text.startswith(k)), text)
    radky = [
        f"# {T['fronta_nadpis']}", "",
        f"## {T['souhrn']}",
        (T["ceka_rucne"].format(n=len(fronta), m=sum(minuty(f) for f in fronta)) if bez_ai
         else T["ceka"].format(n=len(fronta), t=cislo(sum(f["tokeny"] for f in fronta)))) if fronta else T["nic_neceka"],
        "",
        f'<progress value="{vyrizeno}" max="{max(celkem, 1)}"></progress> ' + T["zpracovano"].format(a=vyrizeno, b=celkem),
        "",
        f"## {T['seznam']}",
        T["aktualizovano"].format(d=date.today().isoformat()), "",
    ]
    if fronta:
        radky += [T["tabulka_rucne"] if bez_ai else T["tabulka"], "|---|---|---|---:|---|"]
        for f in fronta:
            typ = T.get("typ_" + f["typ"], f["typ"])
            mnozstvi = T["minuty"].format(n=minuty(f)) if bez_ai else cislo(f["tokeny"])
            pozn = "" if bez_ai and f["poznamka"].startswith(("VELKÉ", "AI přečte")) else preloz(f["poznamka"])
            radky.append(f"| {Path(f['soubor']).name.replace('|', '/')} | {f['predmet']} | {typ} | {mnozstvi} | {pozn} |")
    FRONTA.write_text("\n".join(radky) + "\n")
    (SYS / "fronta.json").write_text(json.dumps(fronta, ensure_ascii=False, indent=1))

    print(T["ve_fronte"].format(n=len(fronta), h=stavy["hotovo"], p=stavy["preskoceno"], d=stavy["duplicita"]))
    if fronta:
        print(T["odhad"].format(a=cislo(uspora_cista), b=cislo(uspora_puvodni)))
        for f in fronta:
            print(f"  - [{f['typ']}] {f['soubor']} (~{f['tokeny']} tok.) {f['poznamka']}")

def presun(soubor, predmet):
    inbox = (TREZOR / "_Inbox").resolve()
    zdroj = (TREZOR / soubor).resolve()
    cilova = (TREZOR / predmet).resolve()
    if zdroj.parent != inbox or not zdroj.is_file():
        sys.exit("Přesouvat jde jen soubory přímo z _Inbox.")
    if cilova.parent != TREZOR.resolve() or not (cilova / f"{cilova.name}.md").exists():
        sys.exit(f"Neznámý předmět: {predmet}")
    cil = cilova / zdroj.name
    if cil.exists():
        sys.exit(f"V předmětu už soubor {zdroj.name} je – nepřepisuju ho.")
    shutil.move(str(zdroj), str(cil))
    print(f"přesunuto: {nfc(str(cil.relative_to(TREZOR.resolve())))}")


def frontmatter(p):
    text = p.read_text(errors="ignore")
    if not text.startswith("---"):
        return {}
    blok = text.split("---", 2)[1] if text.count("---") >= 2 else ""
    return {k.strip(): v.strip().strip('"') for k, v in re.findall(r"^([\w]+):[ \t]*(.*)$", blok, re.M)}


def poznamky():
    for p in sorted(TREZOR.rglob("*.md")):
        rel = p.relative_to(TREZOR)
        if rel.parts[0] not in ("_Systém", "_Archiv", ".obsidian", ".claude", ".trash"):
            yield p, nfc(str(rel))


def zmenene(dni):
    hranice = time.time() - dni * 86400
    for p, rel in poznamky():
        if p.stat().st_mtime >= hranice:
            print(rel)


def ukoly():
    for p, rel in poznamky():
        fm = frontmatter(p)
        if fm.get("typ") == "ukol" and fm.get("stav") != "hotovo":
            print(f"{fm.get('termin') or 'bez termínu'} | {fm.get('kod', '')} | {rel}")


if __name__ == "__main__":
    # jen jeden běh najednou (Obsidian i AI ho spouštějí souběžně) – jinak by se přepisoval registr
    zamek = open(ZAMEK, "w")
    fcntl.flock(zamek, fcntl.LOCK_EX)
    if len(sys.argv) == 3 and sys.argv[1] in ("--hotovo", "--preskoc"):
        oznac(sys.argv[2], "hotovo" if sys.argv[1] == "--hotovo" else "preskoceno")
    elif len(sys.argv) == 4 and sys.argv[1] == "--presun":
        presun(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3 and sys.argv[1] == "--zmenene":
        zmenene(int(sys.argv[2]))
    elif len(sys.argv) == 2 and sys.argv[1] == "--ukoly":
        ukoly()
    else:
        prehled()
