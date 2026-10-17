#!/usr/bin/env python3
"""Aktualizace existujícího trezoru na novou verzi druhého mozku (volá ji Instalovat.command).

  python3 nastroje/aktualizace.py --cil <trezor>             # aktualizuje trezor ze složky trezor/ vedle
  python3 nastroje/aktualizace.py --cil <trezor> --jen-zapis  # jen zapíše _Systém/instalace.json (po nové instalaci)

Pravidla:
  • KÓD (skripty, rozšíření, jazykové balíčky, oprávnění a příkazy AI, systémové CSS) se vždy nahradí novou verzí.
  • SYSTÉMOVÉ POZNÁMKY (Domov, Návod, šablony, rozcestníky, tabulky, .claude/CLAUDE.md) se nahradí jen tehdy,
    když je uživatel neupravil. Upravené zůstanou a nová verze se uloží vedle s příponou „(nová verze)“.
  • VŠE OSTATNÍ se nemění: poznámky, materiály, _Systém/nastaveni.json, CSS předmětů, nastavení Obsidianu, data pluginů,
    ukázkový předmět.
  Před přepsáním se každý soubor zazálohuje do <trezor>/.druhy-mozek-zaloha/<datum>/ (Obsidian skryté složky nezobrazuje).
  Co bylo nainstalováno, eviduje _Systém/instalace.json (otisky SHA-256) – podle něj se pozná, co uživatel upravil.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ZDROJ = Path(__file__).resolve().parent.parent / "trezor"
EVIDENCE = "_Systém/instalace.json"
MANIFEST = ".obsidian/plugins/druhy-mozek/manifest.json"
PRIPONA = {"cs": " (nová verze)", "sk": " (nová verzia)", "en": " (new version)", "uk": " (нова версія)"}

# kód: vždy nahradit (uživatel ho nemá upravovat – hlídá ho i kontrola integrity v Obsidianu)
KOD = ["_Systém/priprav.py", "_Systém/novy_ukol.py", "_Systém/predmety.py", "_Systém/prehledy.py", "_Systém/Word/vytvor_sablonu.py", "_Systém/texty.json",
       "_Systém/nastaveni.priklad.json", "_Systém/jazyky/cs.json", "_Systém/jazyky/sk.json", "_Systém/jazyky/en.json",
       "_Systém/jazyky/uk.json", ".obsidian/plugins/druhy-mozek/main.js", MANIFEST,
       ".obsidian/plugins/druhy-mozek/styles.css", ".obsidian/plugins/druhy-mozek/preklady.json",
       ".obsidian/snippets/druhy-mozek.css", ".claude/settings.json"]
KOD_SLOZKY = [".claude/commands/"]
# upravitelné systémové soubory mimo jazykový balíček
UPRAVITELNE = [".claude/CLAUDE.md"]
# nikdy nepřepisovat (ani když chybí, kromě vytvoření)
UZIVATELSKE = [".obsidian/snippets/druhy-mozek-predmety.css"]
UKAZKA = "Příklad předmětu/"


def otisk(data):
    return hashlib.sha256(data).hexdigest()


def verze(manifest):
    try:
        return json.loads(Path(manifest).read_text(encoding="utf8")).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def cislo_verze(v):
    try:
        return tuple(int(x) for x in str(v).lstrip("v").split("."))
    except ValueError:
        return (0, 0, 0)


def bezpecna(rel):
    return not (rel.startswith("/") or ".." in rel.split("/"))


def nove_soubory(jazyk):
    """{rel: (bajty, druh)} – druh: kod / upravitelne / uzivatelske."""
    soubory = {}
    for p in sorted(ZDROJ.rglob("*")):
        if p.is_file() and p.name != ".DS_Store":
            rel = p.relative_to(ZDROJ).as_posix()
            if rel.startswith(UKAZKA):  # ukázkový předmět se při aktualizaci nevrací
                continue
            if rel in KOD or any(rel.startswith(s) for s in KOD_SLOZKY):
                soubory[rel] = (p.read_bytes(), "kod")
            elif rel in UPRAVITELNE:
                soubory[rel] = (p.read_bytes(), "upravitelne")
            elif rel in UZIVATELSKE or p.name == ".gitkeep":
                soubory[rel] = (p.read_bytes(), "uzivatelske")
    balicek = json.loads((ZDROJ / f"_Systém/jazyky/{jazyk}.json").read_text(encoding="utf8"))["soubory"]
    for rel, obsah in balicek.items():
        if bezpecna(rel) and not rel.startswith(UKAZKA):
            soubory[rel] = (obsah.encode("utf8"), "upravitelne")
    return soubory


def zapis_evidenci(cil, soubory, ver, jazyk):
    """Zaeviduje jen soubory, jejichž obsah v trezoru odpovídá nainstalované verzi."""
    evidence = {rel: otisk(data) for rel, (data, _) in soubory.items()
                if (cil / rel).is_file() and (cil / rel).read_bytes() == data}
    (cil / EVIDENCE).write_text(json.dumps({"verze": ver, "jazyk": jazyk, "soubory": evidence},
                                           ensure_ascii=False, indent=1) + "\n", encoding="utf8")


def aktualizuj(cil, jen_zapis=False):
    cil = Path(cil).resolve()
    if not (cil / "_Systém/nastaveni.json").is_file() or not (cil / MANIFEST).is_file():
        raise SystemExit(f"CHYBA: {cil} nevypadá jako trezor s druhým mozkem (chybí _Systém/nastaveni.json nebo rozšíření).")
    nastaveni = json.loads((cil / "_Systém/nastaveni.json").read_text(encoding="utf8"))
    jazyk = nastaveni.get("jazyk") if nastaveni.get("jazyk") in PRIPONA else "cs"
    nova, stara = verze(ZDROJ.parent / "trezor" / MANIFEST), verze(cil / MANIFEST)
    soubory = nove_soubory(jazyk)
    if jen_zapis:
        zapis_evidenci(cil, soubory, nova, jazyk)
        return {"verze": nova}
    if cislo_verze(stara) > cislo_verze(nova):
        raise SystemExit(f"CHYBA: v trezoru je novější verze ({stara}) než v tomto balíčku ({nova}) – stáhni nejnovější vydání.")

    try:
        evidence = json.loads((cil / EVIDENCE).read_text(encoding="utf8")).get("soubory", {})
    except Exception:
        evidence = {}
    try:  # starý jazykový balíček v trezoru: neupravené systémové poznámky jsou s ním shodné
        stary_balicek = json.loads((cil / f"_Systém/jazyky/{jazyk}.json").read_text(encoding="utf8"))["soubory"]
    except Exception:
        stary_balicek = {}

    if (cil / ".druhy-mozek-zaloha").is_symlink():
        raise SystemExit("CHYBA: .druhy-mozek-zaloha je symbolický odkaz – z bezpečnostních důvodů nepokračuji.")
    zaloha = cil / ".druhy-mozek-zaloha" / datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S")
    vysledek = {"verze": nova, "puvodni": stara, "nove": [], "nahrazeno": [], "ponechano": [], "zaloha": str(zaloha)}

    def zalohuj(rel):
        z = zaloha / rel
        z.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cil / rel, z)

    def mimo_trezor(p):
        """Symbolický odkaz kdekoli na cestě nebo cíl mimo trezor → nesahat (zápis by šel jinam)."""
        cast = p
        while cast != cil:
            if cast.is_symlink():
                return True
            cast = cast.parent
        return not str(p.resolve()).startswith(str(cil) + os.sep)

    try:
        for rel, (data, druh) in soubory.items():
            if not bezpecna(rel):
                continue
            p = cil / rel
            if mimo_trezor(p):
                vysledek.setdefault("preskoceno", []).append(rel)
                continue
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
                vysledek["nove"].append(rel)
                continue
            if druh == "uzivatelske":
                continue
            soucasny = p.read_bytes()
            if soucasny == data:
                continue
            neupraveno = (evidence.get(rel) == otisk(soucasny)
                          or (rel in stary_balicek and stary_balicek[rel].encode("utf8") == soucasny))
            if druh == "kod" or neupraveno:
                zalohuj(rel)
                p.write_bytes(data)
                vysledek["nahrazeno"].append(rel)
            else:  # uživatel soubor upravil → nechat a novou verzi uložit vedle
                vedle = p.with_name(p.stem + PRIPONA[jazyk] + p.suffix)
                vedle.write_bytes(data)
                vysledek["ponechano"].append(rel)
    except Exception:
        # aktualizace se nepovedla uprostřed → vrátit všechno do původního stavu
        for rel in vysledek["nahrazeno"]:
            shutil.copy2(zaloha / rel, cil / rel)
        for rel in vysledek["nove"]:  # soubory, které tahle aktualizace právě vytvořila
            (cil / rel).unlink(missing_ok=True)
        raise

    # záznam pro „↩️ Vrátit poslední aktualizaci“ v Obsidianu
    if vysledek["nahrazeno"] or vysledek["nove"]:
        zaloha.mkdir(parents=True, exist_ok=True)
        (zaloha / "aktualizace.json").write_text(json.dumps(
            {"z": stara, "na": nova, "nahrazeno": vysledek["nahrazeno"], "nove": vysledek["nove"]},
            ensure_ascii=False, indent=1) + "\n", encoding="utf8")

    zapis_evidenci(cil, soubory, nova, jazyk)
    # vzhled předmětů v levém panelu podle předmětů v trezoru (starší verze ho měly v druhy-mozek.css)
    subprocess.run([sys.executable, str(cil / "_Systém/predmety.py"), "--css"], cwd=cil,
                   env={**os.environ, "TREZOR": str(cil)}, capture_output=True, timeout=60)
    return vysledek


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--cil", required=True)
    a.add_argument("--jen-zapis", action="store_true")
    a.add_argument("--json", action="store_true", help="výsledek jako JSON")
    a.add_argument("--pro-instalator", action="store_true", help="1. řádek souhrn, další řádky ponechané soubory")
    arg = a.parse_args()
    v = aktualizuj(arg.cil, arg.jen_zapis)
    if arg.json:
        print(json.dumps(v, ensure_ascii=False))
    elif arg.pro_instalator:
        print(f"{v['puvodni']} → {v['verze']} ({len(v['nahrazeno'])} / +{len(v['nove'])})")
        for rel in v["ponechano"]:
            print("•", rel)
    elif not arg.jen_zapis:
        print(f"Verze {v['puvodni']} → {v['verze']}: nových {len(v['nove'])}, nahrazeno {len(v['nahrazeno'])}, "
              f"ponecháno upravených {len(v['ponechano'])}")
        for rel in v["ponechano"]:
            print("  ponecháno (nová verze vedle):", rel)
    sys.exit(0)
