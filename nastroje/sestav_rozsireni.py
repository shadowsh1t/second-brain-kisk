#!/usr/bin/env python3
"""Sestaví druhý mozek pro adresář rozšíření Obsidianu (community.obsidian.md).

  python3 nastroje/sestav_rozsireni.py            # dist/main.js, dist/manifest.json, dist/styles.css
  python3 nastroje/sestav_rozsireni.py --koren    # navíc srovná manifest.json a versions.json v kořeni repozitáře

Verze z adresáře dostane od Obsidianu jen tyhle tři soubory. Systém pro trezor (skripty, šablony, jazykové balíčky,
pravidla pro AI) je proto přibalený přímo v main.js: při prvním spuštění ho rozbalí průvodce nastavením a po aktualizaci
rozšíření ho obnoví se stejnými pravidly jako nastroje/aktualizace.py (kód se zálohuje a nahradí, upravené poznámky zůstanou).
Verze z adresáře se sama neaktualizuje – to dělá Obsidian (pravidla adresáře).
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "nastroje"))
import aktualizace as A  # noqa: E402

ROZ = REPO / "trezor" / ".obsidian" / "plugins" / "druhy-mozek"
DIST = REPO / "dist"
ZNACKA_DISTRIBUCE = 'const DISTRIBUCE = "github";'
ZNACKA_BALIK = "const BALIK = null;"


def balik():
    manifest = json.loads((ROZ / "manifest.json").read_text(encoding="utf8"))
    soubory = {}
    jazykove = set(json.loads((A.ZDROJ / "_Systém/jazyky/cs.json").read_text(encoding="utf8"))["soubory"])
    for rel, (data, druh) in A.nove_soubory("cs").items():
        if rel.startswith(".obsidian/plugins/druhy-mozek/") or rel in jazykove:
            continue  # rozšíření dodá Obsidian; systémové poznámky se berou z jazykového balíčku podle jazyka trezoru
        soubory[rel] = {"druh": druh, "text": data.decode("utf8")}
    preklady = json.loads((ROZ / "preklady.json").read_text(encoding="utf8"))
    return {"verze": manifest["version"], "soubory": soubory, "preklady": preklady}


def js_literal(data):
    # JSON je platný JavaScript až na znaky U+2028/U+2029
    return json.dumps(data, ensure_ascii=False, sort_keys=True).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def sestav():
    zdroj = (ROZ / "main.js").read_text(encoding="utf8")
    assert zdroj.count(ZNACKA_DISTRIBUCE) == 1 and zdroj.count(ZNACKA_BALIK) == 1, "značky v main.js chybí"
    vystup = zdroj.replace(ZNACKA_DISTRIBUCE, 'const DISTRIBUCE = "obsidian";').replace(ZNACKA_BALIK, f"const BALIK = {js_literal(balik())};")
    DIST.mkdir(exist_ok=True)
    (DIST / "main.js").write_text(vystup, encoding="utf8")
    for n in ("manifest.json", "styles.css"):
        (DIST / n).write_bytes((ROZ / n).read_bytes())
    return DIST / "main.js"


def koren():
    """manifest.json v kořeni čte adresář Obsidianu; versions.json říká, která verze potřebuje jakou verzi Obsidianu."""
    manifest = json.loads((ROZ / "manifest.json").read_text(encoding="utf8"))
    (REPO / "manifest.json").write_bytes((ROZ / "manifest.json").read_bytes())
    p = REPO / "versions.json"
    verze = json.loads(p.read_text(encoding="utf8")) if p.exists() else {}
    verze[manifest["version"]] = manifest["minAppVersion"]
    p.write_text(json.dumps(dict(sorted(verze.items(), key=lambda x: tuple(map(int, x[0].split("."))))), indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    cesta = sestav()
    if "--koren" in sys.argv:
        koren()
    print(f"{cesta.relative_to(REPO)}: {cesta.stat().st_size // 1024} kB")
