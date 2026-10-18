#!/usr/bin/env python3
"""Nový úkol ve Wordu podle šablony KISK.

  python3 _Systém/novy_ukol.py "<Předmět>" "<Název práce>" [--typ TEXT] [--termin RRRR-MM-DD] [--z-dokumentu cesta.docx]

Vytvoří <Předmět>/Úkoly/<UČO>-<Jméno> <KÓD> <Název>.docx s vyplněnou hlavičkou,
k tomu poznámku úkolu pro Obsidian (Domov i Neuro Roadmap ukážou termín) a otevře dokument ve Wordu.
S --z-dokumentu vloží text, obrázky, odkazy, číslování a poznámky pod čarou z hotové práce do šablony
(originál zůstane beze změny). Na výstup vypíše cestu k dokumentu a k poznámce (2 řádky).
Osobní údaje (jméno, UČO) se berou z _Systém/nastaveni.json.
"""
import argparse
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

SYSTEM = Path(__file__).resolve().parent
TREZOR = Path(os.environ.get("TREZOR") or SYSTEM.parent)
SABLONA = SYSTEM / "Word" / "Šablona KISK.dotx"
try:
    NASTAVENI = json.loads((SYSTEM / "nastaveni.json").read_text())
    PREFIX = f'{NASTAVENI["uco"]}-{NASTAVENI["jmeno_soubor"]}'
except (OSError, ValueError, KeyError, TypeError):
    sys.exit("_Systém/nastaveni.json: uco, jmeno_soubor?")
_TEXTY = json.loads((SYSTEM / "texty.json").read_text(encoding="utf8"))
T = {**_TEXTY["cs"], **_TEXTY.get(NASTAVENI.get("jazyk") or "cs", {})}  # texty v jazyce uživatele

REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
CT_DOC = "application/vnd.openxmlformats-officedocument.wordprocessingml."
CASTI = ("numbering", "footnotes", "endnotes")  # celé části, které přeneseme ze zdroje
MAX_ROZBALENO = 200_000_000  # max. celková velikost rozbaleného zdrojového .docx
MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "bmp": "image/bmp",
        "emf": "image/x-emf", "wmf": "image/x-wmf", "tif": "image/tiff", "tiff": "image/tiff", "svg": "image/svg+xml"}


def vlastnost(md, klic):
    m = re.search(rf"^{klic}:[ \t]*(.*)$", md, re.M)
    return m.group(1).strip().strip('"') if m else ""


def bez_ridicich(text):
    return re.sub(r"[\x00-\x1f\x7f]+", " ", text).strip()


def bezpecne(nazev, bajtu=200):
    """Název souboru: bez zakázaných a řídicích znaků, nejvýš `bajtu` v UTF-8 (macOS dovolí 255 i s příponou)."""
    nazev = bez_ridicich(re.sub(r'[\\/:*?"<>|#^\[\]]', "-", nazev))
    return nazev.encode("utf8")[:bajtu].decode("utf8", "ignore").strip()


def atributy(tag):
    return dict(re.findall(r'([\w:]+)="([^"]*)"', tag))


def pridej_typ(soubory, xml_tag):
    ct = soubory["[Content_Types].xml"].decode("utf8")
    klic = re.search(r'(?:PartName|Extension)="[^"]+"', xml_tag).group(0)
    if klic not in ct:
        soubory["[Content_Types].xml"] = ct.replace("</Types>", xml_tag + "</Types>").encode("utf8")


def bezpecna_cast(cesta):
    if not cesta.startswith("word/") or ".." in cesta.split("/"):
        sys.exit(T["chyba_mimo"].format(p=cesta))
    return cesta


def zkopiruj_obrazek(soubory, src, cesta):
    cesta = bezpecna_cast(cesta)
    if cesta not in src:
        sys.exit(T["chyba_obrazek"].format(p=cesta))
    soubory[cesta] = src[cesta]
    pripona = cesta.rsplit(".", 1)[-1].lower()
    pridej_typ(soubory, f'<Default Extension="{pripona}" ContentType="{MIME.get(pripona, "application/octet-stream")}"/>')


def zkopiruj_rels_casti(soubory, src, cast):
    """Přenese vztahy části (např. footnotes.xml) včetně obrázků, na které odkazuje."""
    rels = posixpath.join(posixpath.dirname(cast), "_rels", posixpath.basename(cast) + ".rels")
    if rels not in src:
        return
    soubory[rels] = src[rels]
    for tag in re.findall(r"<Relationship\b[^>]*/>", src[rels].decode("utf8")):
        a = atributy(tag)
        if a.get("TargetMode") != "External" and a.get("Type", "").endswith("/image"):
            zkopiruj_obrazek(soubory, src, posixpath.normpath(posixpath.join("word", a["Target"])))


def vloz_dokument(soubory, zdroj):
    """Nahradí kostru těla šablony obsahem zdrojového dokumentu."""
    with zipfile.ZipFile(zdroj) as z:
        if sum(i.file_size for i in z.infolist()) > MAX_ROZBALENO:
            sys.exit(T["chyba_velky"])
        src = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    sxml = src["word/document.xml"].decode("utf8")

    zacatek = sxml.index(">", sxml.index("<w:body")) + 1
    posledni_oddil = re.search(r"(<w:sectPr\b(?:(?!<w:sectPr\b).)*?</w:sectPr>|<w:sectPr\s*/>)\s*</w:body>", sxml, re.S)
    konec = posledni_oddil.start() if posledni_oddil else sxml.rindex("</w:body>")
    telo = sxml[zacatek:konec]
    # vnitřní oddíly a komentáře zdroje zahodíme – platí záhlaví a okraje šablony
    telo = re.sub(r"<w:sectPr\b[\s\S]*?</w:sectPr>|<w:sectPr\s*/>", "", telo)
    telo = re.sub(r"<w:comment(?:RangeStart|RangeEnd|Reference)\b[^>]*/>", "", telo)

    pouzite = set(re.findall(r'r:\w+="([^"]+)"', telo))
    nove = []
    for tag in re.findall(r"<Relationship\b[^>]*/>", src.get("word/_rels/document.xml.rels", b"").decode("utf8")):
        a = atributy(tag)
        rid, typ, cil = a.get("Id"), a.get("Type", "").rsplit("/", 1)[-1], a.get("Target", "")
        externi = a.get("TargetMode") == "External"
        novy = f"rIdZ{rid}"
        if typ in CASTI and not externi:
            cesta = bezpecna_cast(posixpath.normpath(posixpath.join("word", cil)))
            if cesta not in src:
                continue
            soubory[cesta] = src[cesta]
            zkopiruj_rels_casti(soubory, src, cesta)
            pridej_typ(soubory, f'<Override PartName="/{cesta}" ContentType="{CT_DOC}{typ}+xml"/>')
        elif rid in pouzite and typ in ("image", "hyperlink"):
            if typ == "image" and not externi:
                zkopiruj_obrazek(soubory, src, posixpath.normpath(posixpath.join("word", cil)))
        elif rid in pouzite:
            sys.exit(T["chyba_prvek"].format(p=typ))
        else:
            continue
        rezim = ' TargetMode="External"' if externi else ""
        nove.append(f'<Relationship Id="{novy}" Type="{REL}{typ}" Target="{cil}"{rezim}/>')
        telo = re.sub(rf'(r:\w+=")({re.escape(rid)})(")', rf"\g<1>{novy}\3", telo)
    trels = soubory["word/_rels/document.xml.rels"].decode("utf8")
    soubory["word/_rels/document.xml.rels"] = trels.replace("</Relationships>", "".join(nove) + "</Relationships>").encode("utf8")

    txml = soubory["word/document.xml"].decode("utf8")
    kotva = txml.index('w:name="TeloPrace"')
    od = txml.rindex("<w:p>", 0, kotva)
    do = txml.rindex("<w:sectPr")
    # kořen dokumentu: jmenné prostory a mc:Ignorable zdroje + to, co potřebuje šablona
    s_koren = atributy(sxml[sxml.index("<w:document"):sxml.index(">", sxml.index("<w:document"))])
    t_konec = txml.index(">", txml.index("<w:document"))
    t_koren = atributy(txml[txml.index("<w:document"):t_konec])
    koren = {**s_koren, **{k: v for k, v in t_koren.items() if k not in s_koren}}
    zahlavi = "<w:document " + " ".join(f'{k}="{v}"' for k, v in koren.items())
    txml = txml[:txml.index("<w:document")] + zahlavi + txml[t_konec:od] + telo + txml[do:]
    soubory["word/document.xml"] = txml.encode("utf8")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("predmet")
    a.add_argument("nazev")
    a.add_argument("--termin", default="")
    a.add_argument("--typ", default="")
    a.add_argument("--z-dokumentu", dest="zdroj")
    a.add_argument("--jazyk", choices=sorted(_TEXTY), help="jazyk dokumentu ve Wordu (výchozí = nastavení jazyk_word)")
    a.add_argument("--neotvirat", action="store_true")
    arg = a.parse_args()

    slozka = TREZOR / arg.predmet
    prehled = slozka / f"{arg.predmet}.md"
    if "/" in arg.predmet or ".." in arg.predmet or not prehled.exists():
        sys.exit(T["chyba_predmet"].format(p=arg.predmet))
    termin = ""
    if arg.termin:
        try:
            termin = date.fromisoformat(arg.termin)
        except ValueError:
            sys.exit(T["chyba_termin"])
    md = prehled.read_text()
    kod = vlastnost(md, "kod")
    oficialni = vlastnost(md, "nazev") or arg.predmet
    arg.nazev, arg.typ = bez_ridicich(arg.nazev), bez_ridicich(arg.typ)
    nazev = bezpecne(arg.nazev, 150)
    if not nazev:
        sys.exit(T["chyba_nazev"])

    cil = slozka / "Úkoly" / f"{bezpecne(f'{PREFIX} {kod} {nazev}')}.docx"
    poznamka = cil.parent / f"{T['ukol_prefix']}{nazev}.md"
    if cil.exists():
        sys.exit(T["chyba_existuje"].format(p=cil.relative_to(TREZOR)))

    # jazyk dokumentů ve Wordu se volí předem v nastavení (jazyk_word); --jazyk je jen výjimka pro jeden úkol
    jazyk_word = NASTAVENI.get("jazyk_word") or NASTAVENI.get("jazyk") or "cs"
    TD = {**_TEXTY["cs"], **_TEXTY.get(arg.jazyk or jazyk_word, {})}
    sablona = SABLONA
    if arg.jazyk and arg.jazyk != jazyk_word:
        sablona = Path(tempfile.mkdtemp()) / "sablona.dotx"
        subprocess.run([sys.executable, str(SYSTEM / "Word" / "vytvor_sablonu.py"), str(sablona), "--jazyk", arg.jazyk],
                       check=True, capture_output=True)
    with zipfile.ZipFile(sablona) as z:
        soubory = {n: z.read(n) for n in z.namelist()}
    if sablona != SABLONA:
        shutil.rmtree(sablona.parent, ignore_errors=True)
    soubory["[Content_Types].xml"] = soubory["[Content_Types].xml"].replace(b"template.main+xml", b"document.main+xml")

    nahrady = {
        TD["ph_nazev"]: arg.nazev,
        TD["ph_predmet"]: f"{kod} {oficialni}".strip(),
    }
    if arg.typ:
        nahrady[TD["ph_typ"]] = arg.typ
    for cast in ("word/document.xml", "word/header1.xml"):
        x = soubory[cast].decode("utf8")
        for k, v in nahrady.items():
            x = x.replace(escape(k), escape(v))
        if not arg.typ:  # bez typu práce zůstane na titulní straně jen název
            x = re.sub(r"<w:p>(?:(?!<w:p>).)*?" + re.escape(escape(TD["ph_typ"])) + r".*?</w:p>", "", x)
        soubory[cast] = x.encode("utf8")

    if arg.zdroj:
        try:
            vloz_dokument(soubory, arg.zdroj)
        except (OSError, zipfile.BadZipFile, KeyError, ValueError, UnicodeDecodeError):
            sys.exit(T["chyba_zdroj"].format(p=bez_ridicich(arg.zdroj)))

    cil.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(cil, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", soubory.pop("[Content_Types].xml"))  # musí být první
        for n, data in soubory.items():
            z.writestr(n, data)

    if not poznamka.exists():
        tit = arg.nazev.replace('"', "'")
        poznamka.write_text(
            f"---\ntyp: ukol\npredmet: \"[[{arg.predmet}]]\"\nkod: {kod}\ntermin: {termin or ''}\nstav: otevreno\n"
            f"zdroj: \"[[{cil.name}]]\"\ntags:\n  - ukol\n---\n# {T['ukol_prefix']}{tit}\n\n"
            f"{T['dokument']} [[{cil.name}]]\n\n{T['zadani']}\n\n{T['postup']}\n- [ ] \n"
            + (f"- [ ] {T['odevzdat']} [due:: {termin}]\n" if termin else f"- [ ] {T['odevzdat']}\n")
            + f"\n{T['poznamky']}\n")

    print(cil.relative_to(TREZOR))
    print(poznamka.relative_to(TREZOR))
    if not arg.neotvirat:
        subprocess.run(["open", "-a", "Microsoft Word", str(cil)])


if __name__ == "__main__":
    main()
