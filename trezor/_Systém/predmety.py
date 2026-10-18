#!/usr/bin/env python3
"""Předměty v trezoru: založení nových a vzhled v levém panelu (oranžový pruh + kód před názvem).

  python3 _Systém/predmety.py --pridat "ISKB02 Úvod do knihovnictví" "ISKB03 Informační služby a vyhledávání"
  python3 _Systém/predmety.py --css       # jen přegeneruje vzhled předmětů v levém panelu
  python3 _Systém/predmety.py --seznam    # vypíše předměty (JSON)

Předmět = složka v kořeni trezoru s přehledem <Název>/<Název>.md (typ: predmet). Nic se nemaže ani nepřepisuje –
existující předmět se přeskočí. Odebrání (přesun do koše) se dělá v Obsidianu (Nastavení → Second Brain for KISK → Předměty).
"""
import argparse
import datetime
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

TREZOR = Path(os.environ.get("TREZOR") or Path(__file__).resolve().parent.parent)
NASTAVENI = TREZOR / "_Systém" / "nastaveni.json"
CSS = TREZOR / ".obsidian" / "snippets" / "druhy-mozek-predmety.css"
ZACATEK = "/* >>> předměty – tuhle část generuje druhý mozek (📚 Přidat předmět), ručně ji neupravuj */"
KONEC = "/* <<< konec generované části – pod tenhle řádek můžeš psát vlastní CSS, zůstane zachované */"
HLAVICKA = ("/* Druhý mozek – vzhled tvých předmětů v levém panelu (oranžový pruh + kód předmětu před názvem).\n"
            "   Tenhle soubor je tvůj – aktualizace ho nepřepíše. */\n")
KOD = re.compile(r"^(?=.*\d)[A-Za-z0-9][A-Za-z0-9_.-]{1,14}$")
ZAKAZANE = set('/\\:*?"<>|#^[]')
UKAZKA = "Příklad předmětu/Příklad předmětu.md"
SEMESTR = {"cs": ("podzim", "jaro"), "sk": ("jeseň", "jar"), "en": ("autumn", "spring"), "uk": ("осінь", "весна")}


def nastaveni():
    try:
        data = json.loads(NASTAVENI.read_text(encoding="utf8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}  # pole nebo číslo místo objektu = jako bez nastavení


JAZYK = nastaveni().get("jazyk") if nastaveni().get("jazyk") in SEMESTR else "cs"
_TEXTY = json.loads((TREZOR / "_Systém" / "texty.json").read_text(encoding="utf8"))
T = {**_TEXTY["cs"], **_TEXTY.get(JAZYK, {})}


def rozdel(text):
    """'ISKB02 Úvod do knihovnictví' → ('ISKB02', 'Úvod do knihovnictví'); bez kódu → ('', text)."""
    casti = text.strip().split(None, 1)
    if len(casti) == 2 and KOD.match(casti[0]):
        return casti[0].upper(), casti[1].strip()
    return "", text.strip()


def platny_nazev(nazev):
    return (0 < len(nazev) <= 80 and not nazev.startswith((".", "_", "-")) and nazev not in (".", "..")
            and not (set(nazev) & ZAKAZANE) and nazev == nazev.strip() and all(c.isprintable() for c in nazev))


def vlastnost(text, klic):
    hlava = text.split("---", 2)[1] if text.startswith("---") else ""
    m = re.search(rf"^{klic}:[ \t]*(.*)$", hlava, re.M)
    return m.group(1).strip().strip('"') if m else ""


def seznam():
    """Předměty v kořeni trezoru (archiv a systémové složky se nepočítají)."""
    vysledek = []
    for d in sorted(TREZOR.iterdir(), key=lambda x: x.name):
        prehled = d / f"{d.name}.md"
        if d.is_dir() and not d.name.startswith((".", "_")) and prehled.is_file():
            text = prehled.read_text(encoding="utf8", errors="ignore")
            if vlastnost(text, "typ") == "predmet":
                # NFC: macOS/OneDrive vrací názvy rozložené (NFD), Obsidian v data-path složené – jinak CSS nesedí
                vysledek.append({"nazev": unicodedata.normalize("NFC", d.name),
                                 "kod": unicodedata.normalize("NFC", vlastnost(text, "kod"))})
    return sorted(vysledek, key=lambda p: (p["kod"] or "~", p["nazev"]))


def css_uvoz(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def obnov_css():
    radky = [ZACATEK]
    for p in seznam():
        n = css_uvoz(p["nazev"])
        radky.append(f'.nav-folder-title[data-path="{n}"] {{ border-left: 4px solid rgb(209, 130, 100); border-radius: 4px; font-weight: 600; }}')
        if p["kod"]:
            radky.append(f'.nav-folder-title[data-path="{n}"] .nav-folder-title-content::before '
                         f'{{ content: "{css_uvoz(p["kod"])} · "; opacity: .6; }}')
    radky.append(KONEC)
    puvodni = CSS.read_text(encoding="utf8") if CSS.exists() else ""
    if ZACATEK in puvodni and KONEC in puvodni:
        pred, zbytek = puvodni.split(ZACATEK, 1)
        za = zbytek.split(KONEC, 1)[1]
    else:  # starší soubor bez značek: vlastní CSS se zachová pod generovanou částí
        pred, za = HLAVICKA, ("\n" + puvodni if puvodni.strip() else "\n")
    novy = pred + "\n".join(radky) + za
    if CSS.is_symlink() or CSS.parent.is_symlink():  # zápis by šel mimo trezor
        return
    if novy != puvodni:
        CSS.parent.mkdir(parents=True, exist_ok=True)
        CSS.write_text(novy, encoding="utf8")


def sablona(kod, nazev):
    """Přehled předmětu z jazykového balíčku (ukázkový předmět bez rady, jak ho přejmenovat)."""
    balicek = json.loads((TREZOR / "_Systém" / "jazyky" / f"{JAZYK}.json").read_text(encoding="utf8"))
    vzor = balicek["soubory"][UKAZKA]
    hlava, telo = vzor.split("---", 2)[1:]
    nadpis_vzoru = vlastnost(vzor, "nazev")
    dnes = datetime.date.today()
    podzim, jaro = SEMESTR[JAZYK]
    semestr = (f"{podzim} {dnes.year}" if dnes.month >= 9 else f"{podzim} {dnes.year - 1}" if dnes.month == 1
               else f"{jaro} {dnes.year}")
    hlava = re.sub(r"^nazev:.*$", "nazev: " + json.dumps(nazev, ensure_ascii=False), hlava, flags=re.M)
    hlava = re.sub(r"^kod:.*$", f"kod: {kod}", hlava, flags=re.M)
    hlava = re.sub(r"^semestr:.*$", f"semestr: {semestr}", hlava, flags=re.M)
    telo = re.sub(r"\n> \[!tip\][^\n]*(\n>[^\n]*)*\n", "\n", telo, count=1)  # rada „jak z toho udělat svůj předmět“
    telo = telo.replace(f"# {nadpis_vzoru}", f"# {nazev}", 1).replace("ISKB00", kod)
    return f"---{hlava}---{telo}"


def pridej(polozky):
    chyby = 0
    for text in polozky:
        kod, nazev = rozdel(text)
        if not platny_nazev(nazev):
            print(T["predmet_neplatny"].format(p=text.strip()), file=sys.stderr)
            chyby += 1
            continue
        slozka = TREZOR / nazev
        prehled = slozka / f"{nazev}.md"
        if prehled.exists():
            print(T["predmet_existuje"].format(p=nazev))
            continue
        for podslozka in ("Poznámky", "Úkoly"):
            (slozka / podslozka).mkdir(parents=True, exist_ok=True)
        prehled.write_text(sablona(kod, nazev), encoding="utf8")
        print(T["predmet_pridan"].format(p=f"{kod} {nazev}".strip()))
    obnov_css()
    return 2 if chyby else 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--pridat", nargs="+", metavar="'KÓD Název'")
    a.add_argument("--css", action="store_true")
    a.add_argument("--seznam", action="store_true")
    arg = a.parse_args()
    if arg.seznam:
        print(json.dumps(seznam(), ensure_ascii=False))
        sys.exit(0)
    if arg.pridat:
        sys.exit(pridej(arg.pridat))
    obnov_css()
