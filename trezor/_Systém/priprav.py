#!/usr/bin/env python3
"""Spořič dat pro druhý mozek.

Lokálně (zdarma, bez AI) projde materiály v trezoru, z nových nebo změněných
souborů vytáhne čistý text do _Systém/cache a sestaví frontu k zpracování.
AI pak čte jen tenhle text, ne celé PDF nebo prezentace.

Použití:
  python3 _Systém/priprav.py                 # aktualizuje cache a frontu, vypíše souhrn
  python3 _Systém/priprav.py --hotovo CESTA [POZNÁMKA]  # označí soubor jako zpracovaný (jen po úplné kontrole)
  python3 _Systém/priprav.py --kontrola CESTA [POZNÁMKA] [--kapitola N]  # kontrola úplnosti (celá, nebo jedna kapitola)
  python3 _Systém/priprav.py --vynech CESTA ID[,ID] DŮVOD  # položka kontroly záměrně v poznámce není
  python3 _Systém/priprav.py --k-overeni CESTA TEXT  # nejisté místo z druhého čtení (ukáže se ve Frontě)
  python3 _Systém/priprav.py --preskoc CESTA # označí soubor jako přeskočený (vlastní práce, osnova…)
  python3 _Systém/priprav.py --znovu CESTA   # vrátí zpracovaný materiál do fronty (přečte se znovu)
  python3 _Systém/priprav.py --presun SOUBOR PŘEDMĚT [NÁZEV]  # zařadí soubor do <Předmět>/Učivo
  python3 _Systém/priprav.py --pridej-ukol SOUBOR PŘEDMĚT NÁZEV [TERMÍN]  # úkol z nalezeného zadání
  python3 _Systém/priprav.py --ignoruj KLÍČ  # návrh úkolu nebo „hotovo“ už nenabízet
  python3 _Systém/priprav.py --navrh SOUBOR  # navrhne předmět a název podle textu (JSON)
  python3 _Systém/priprav.py --nechat A B    # dvojice možných duplicit: nechat obě, příště neukazovat
  python3 _Systém/priprav.py --zmenene 7     # poznámky změněné za posledních N dní
  python3 _Systém/priprav.py --ukoly         # otevřené úkoly s termíny

Bezpečné náhrady za mv/find, aby AI nepotřebovala obecné příkazy shellu.
"""
import fcntl
import hashlib
import html
import itertools
import json
import os
import plistlib
import posixpath
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
VELKE = 30_000  # odhad tokenů, od kterého se materiál dělí na kapitoly (AI se zeptá, jak ho zpracovat)
KAPITOLA = 15_000  # tokenů nejvýš na jednu kapitolu velkého materiálu
DAVKA = 8  # položek na jedno /zpracuj (stejné číslo je v .claude/commands/zpracuj.md)
VYSTUP = 4_000  # odhad tokenů na napsání poznámky, pojmů a kartiček k jedné položce
MAX_CAST = 50_000_000  # max. velikost jedné rozbalené části pptx/docx (ochrana proti zip bombě)
INBOX = "_Vkládání učiva"
NASTAVENI = SYS / "nastaveni.json"
UKOLY_IGNOROVAT = SYS / "ukoly_ignorovat.json"  # návrhy, které uživatel odmítl
PRACE_SLOV = 200  # dokument ze šablony s méně slovy je ještě prázdný
ZADANI = re.compile(r"(?:vaším úkolem bude|zadání\s+(?:\w+\s+){0,2}úkolu(?:\s+č\.?\s*\d+)?|(?:povinný\s+)?domácí\s+úkol(?:\s+č\.?\s*\d+)?|"
                    r"povinný\s+úkol(?:\s+č\.?\s*\d+)?|zadání\s+portfolia|odpovědník\s+na\s+\d+\s+otázk\w*|termín\s+odevzdání|your\s+assignment|assignment\s+brief)", re.I)
ODEVZDANI = re.compile(r"odevzd|nejpozději|deadline|termín|submit|due\b", re.I)
DATUM = re.compile(r"\b(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)\b")
MESICE = {m: i for i, ms in enumerate(("ledna januára", "února februára", "března marca", "dubna apríla", "května mája", "června júna", "července júla",
                                       "srpna augusta", "září septembra", "října októbra", "listopadu novembra", "prosince decembra"), 1) for m in ms.split()}
DATUM_SLOVEM = re.compile(r"\b(\d{1,2})\.\s*(" + "|".join(MESICE) + r")(?:\s+(20\d\d))?", re.I)
DUPLICITY_NECHAT = SYS / "duplicity_nechat.json"  # dvojice otisků, které si uživatel nechává
PODOBNOST_SLOV = 50_000  # víc slov z jednoho souboru se neporovnává
PODOBNOST_MIN = 30  # kratší text (titulní strana) by dával falešné shody
try:
    _UCO = str(json.loads(NASTAVENI.read_text()).get("uco") or "")
except Exception:  # chybějící nebo poškozené nastavení – skripty běží dál, jen nepoznají vlastní práce podle UČO
    _UCO = ""
VLASTNI_PREFIX = _UCO + "-" if _UCO else None
ZAMEK = SYS / ".priprav.lock"
CACHE_VERZE = 3  # při změně extrakce zvýšit – čekající položky se přegenerují, hotové ne
MALO_TEXTU = 80  # znaků: slajd/strana s menším množstvím textu je „hlavně obrázek“
OCR_ROZPOCET = 150  # s na jeden běh (Obsidian čeká na skript max. 5 min); zbytek se dočte příště
OCR_MAX_STRAN = 60  # stran jednoho PDF
OCR_MAX_OBRAZKU = 10  # obrázků z jedné prezentace
OCR_MIN_VELIKOST = 20_000  # menší obrázky (loga, ikony) se nečtou
OBRAZKY_OCR = {".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".bmp", ".heic", ".webp"}
ZACATEK = time.monotonic()
KONTROLA = SYS / "kontrola"  # výsledky kontroly úplnosti, jeden soubor na materiál (<otisk>.json)
KONTROLA_VERZE = 1
NEVYZNAMNA = set("pro jak ale nebo jsou byl byla bylo byli jeho jeji ktery ktera ktere kteri tak jako pri pod nad mezi take tez pak jen "
                 "neni bude budou jiz uz the and for with that this from are was were".split())
ODRAZKA = re.compile(r"^(?:[•▪◦‣∙·*\-–—]|\d{1,2}[.)]|[a-z][)])\s+")
CISLO = re.compile(r"(?<![\w.,])\d+(?:[  ]\d{3})*(?:[.,]\d+)?(?![\w])")
URL = re.compile(r"https?://[^\s|<>\"')\]]+")
ISO_DATUM = re.compile(r"\b((?:19|20)\d\d)-(\d{1,2})-(\d{1,2})\b")
K_DATUM = re.compile(r"\b(\d{1,2})\.\s*(\d{1,2})\.\s*((?:19|20)\d\d)\b")  # jako DATUM, ale i minulé století (zákony)
K_DATUM_SLOVEM = re.compile(r"\b(\d{1,2})\.\s*(" + "|".join(MESICE) + r")(?:\s+((?:19|20)\d\d))?", re.I)
VYNECH_MAX = 300  # znaků důvodu vynechání nebo místa k ověření
K_OVERENI_MAX = 50  # míst k ověření u jednoho materiálu

# Text z PDF (PDFKit) a rozpoznání textu v obrázcích (macOS Vision) – lokálně, bez AI a bez internetu.
# „pdf“: [{t: text, o: 0 bez OCR | 1 OCR | 2 došel čas | 3 nad limit stran}], „obrazky“: [text | null = došel čas]
OCR_JXA = """
ObjC.import('PDFKit'); ObjC.import('Vision'); ObjC.import('AppKit');
function precti(handler, jazyky) {
  const r = $.VNRecognizeTextRequest.alloc.init;
  r.recognitionLevel = 0; r.usesLanguageCorrection = true;
  try {
    const umi = ObjC.deepUnwrap(r.supportedRecognitionLanguagesAndReturnError(null)) || [];
    const j = jazyky.filter((l) => umi.indexOf(l) >= 0);
    if (j.length) r.recognitionLanguages = $(j);
  } catch (e) {}
  if (!handler.performRequestsError($([r]), null)) return '';
  const v = r.results, out = [];
  for (let i = 0; i < v.count; i++) {
    const c = v.objectAtIndex(i).topCandidates(1);
    if (c.count) out.push(ObjC.unwrap(c.objectAtIndex(0).string));
  }
  return out.join('\\n');
}
function run(argv) {
  const termin = Number(argv[1]), jazyky = argv[2] ? argv[2].split(',') : [];
  if (argv[0] === 'obrazky') return JSON.stringify(argv.slice(3).map((p) => {
    if (Date.now() > termin) return null;
    try { return precti($.VNImageRequestHandler.alloc.initWithURLOptions($.NSURL.fileURLWithPath(p), $({})), jazyky); }
    catch (e) { return ''; }
  }));
  const doc = $.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(argv[3]));
  if (!doc || doc.isNil()) return '[]';
  const out = [];
  let precteno = 0;
  for (let i = 0; i < doc.pageCount; i++) {
    const strana = doc.pageAtIndex(i), s = strana.string;
    let t = s && !s.isNil() ? ObjC.unwrap(s) : '', o = 0;
    if (t.replace(/\\s/g, '').length < 30) {
      if (precteno >= Number(argv[4])) o = 3;
      else if (Date.now() > termin) o = 2;
      else {
        try {
          const b = strana.boundsForBox(0), k = 2000 / Math.max(b.size.width, b.size.height, 1);
          const img = strana.thumbnailOfSizeForBox($.NSMakeSize(b.size.width * k, b.size.height * k), 0);
          const png = $.NSBitmapImageRep.imageRepWithData(img.TIFFRepresentation)
            .representationUsingTypeProperties($.NSBitmapImageFileTypePNG, $({}));
          t = precti($.VNImageRequestHandler.alloc.initWithDataOptions(png, $({})), jazyky);
          o = 1; precteno++;
        } catch (e) { o = 0; }
      }
    }
    out.push({ t: t, o: o });
  }
  return JSON.stringify(out);
}
"""
OCR_JAZYKY = {"cs": ["cs-CZ", "sk-SK", "en-US", "uk-UA"], "sk": ["sk-SK", "cs-CZ", "en-US", "uk-UA"],
              "en": ["en-US", "cs-CZ", "sk-SK", "uk-UA"], "uk": ["uk-UA", "en-US", "cs-CZ", "sk-SK"]}


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


def vztahy(z, cast):
    """Vztahy části (rels): {Id: (typ, cesta v ZIPu nebo URL, externí?)}."""
    adresar, jmeno = posixpath.split(cast)
    rels = f"{adresar}/_rels/{jmeno}.rels"
    if rels not in z.namelist():
        return {}
    vysledek = {}
    for atributy in re.findall(r"<Relationship\b([^>]*)>", precti_cast(z, rels)):
        a = dict(re.findall(r'(\w+)="([^"]*)"', atributy))
        cil = html.unescape(a.get("Target", ""))
        externi = a.get("TargetMode") == "External"
        if not externi:
            cil = cil.lstrip("/") if cil.startswith("/") else posixpath.normpath(posixpath.join(adresar, cil))
        vysledek[a.get("Id")] = (a.get("Type", "").rsplit("/", 1)[-1], cil, externi)
    return vysledek


def odkazy(rel):
    """Řádek s webovými odkazy (bez duplicit, jen http/https/mailto – ne cesty k souborům)."""
    urls = list(dict.fromkeys(c for t, c, ext in rel.values()
                              if ext and t == "hyperlink" and re.match(r"(https?:|mailto:)", c, re.I)))
    return ["[odkazy] " + " · ".join(urls)] if urls else []


def tabulka_md(radky):
    """Seznam řádků (seznamů buněk) → tabulka v Markdownu; první řádek je záhlaví."""
    radky = [[re.sub(r"\s+", " ", b).strip().replace("|", "\\|") for b in r] for r in radky]
    radky = [r for r in radky if any(r)]
    if not radky:
        return ""
    sloupcu = max(len(r) for r in radky)
    radky = [r + [""] * (sloupcu - len(r)) for r in radky]
    md = ["| " + " | ".join(radky[0]) + " |", "|" + "---|" * sloupcu]
    return "\n".join(md + ["| " + " | ".join(r) + " |" for r in radky[1:]])


def pptx_tabulky(xml):
    tabulky = []
    for tbl in re.findall(r"<a:tbl\b[^>]*>(.*?)</a:tbl>", xml, re.S):
        radky = [[" ".join(xml_odstavce(tc, "a:p", "a:t")) for tc in re.findall(r"<a:tc\b[^>]*>(.*?)</a:tc>", tr, re.S)]
                 for tr in re.findall(r"<a:tr\b[^>]*>(.*?)</a:tr>", tbl, re.S)]
        tabulky.append(tabulka_md(radky))
    return [t for t in tabulky if t]


def docx_kusy(xml):
    """Rozdělí tělo dokumentu na text a tabulky v pořadí dokumentu (vnořené tabulky zůstanou v buňce)."""
    hloubka, zacatek, posledni = 0, 0, 0
    for m in re.finditer(r"<(/?)w:tbl(?=[ >])[^>]*>", xml):
        if not m.group(1):
            if hloubka == 0:
                zacatek = m.start()
            hloubka += 1
        elif hloubka:
            hloubka -= 1
            if hloubka == 0:
                yield xml[posledni:zacatek], False
                yield xml[zacatek:m.end()], True
                posledni = m.end()
    yield xml[posledni:], False


def docx_tabulka(xml):
    radky, radek, hloubka, bunka = [], None, 0, 0
    for m in re.finditer(r"<(/?)w:(tbl|tr|tc)(?=[ >])[^>]*>", xml):
        konec, tag = m.group(1), m.group(2)
        if tag == "tbl":
            hloubka += -1 if konec else 1
        elif hloubka != 1:
            continue  # řádky a buňky vnořené tabulky
        elif tag == "tr":
            if konec and radek is not None:
                radky.append(radek)
            radek = None if konec else []
        elif not konec:
            bunka = m.end()
        elif radek is not None:
            obsah = xml[bunka:m.start()]
            vlastnosti = re.match(r"\s*<w:tcPr>(.*?)</w:tcPr>", obsah, re.S)
            text = [html.unescape("".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", p))).strip() for p in obsah.split("</w:p>")]
            radek.append(" ".join(t for t in text if t))
            span = re.search(r'<w:gridSpan w:val="(\d+)"', vlastnosti.group(1)) if vlastnosti else None
            radek += [""] * (min(int(span.group(1)), 50) - 1 if span else 0)
    return tabulka_md(radky)


def graf(z, cast):
    """Data grafu (ppt/charts, word/charts) z uložené cache hodnot → tabulka."""
    if cast not in z.namelist():
        return []
    xml = precti_cast(z, cast)
    nazev = re.search(r"<c:title>(.*?)</c:title>", xml.split("<c:plotArea", 1)[0], re.S)
    nazev = " ".join(xml_odstavce(nazev.group(1), "a:p", "a:t")) if nazev else ""
    body = lambda x: {int(i): html.unescape(v) for i, v in re.findall(r'<c:pt idx="(\d+)"[^>]*>\s*<c:v>([^<]*)</c:v>', x or "")}
    rady = []
    for ser in re.findall(r"<c:ser>(.*?)</c:ser>", xml, re.S):
        tx = re.search(r"<c:tx>(.*?)</c:tx>", ser, re.S)
        jmeno = (" ".join(re.findall(r"<c:v>([^<]*)</c:v>", tx.group(1))) or " ".join(xml_odstavce(tx.group(1), "a:p", "a:t"))) if tx else ""
        kat = re.search(r"<c:(cat|xVal)>(.*?)</c:\1>", ser, re.S)
        hod = re.search(r"<c:(val|yVal)>(.*?)</c:\1>", ser, re.S)
        rady.append((html.unescape(jmeno) or f"řada {len(rady) + 1}", body(kat and kat.group(2)), body(hod and hod.group(2))))
    if not rady:
        return []
    kategorie = {}
    for _, kat, _ in rady:
        for i, v in kat.items():
            kategorie.setdefault(i, v)
    indexy = sorted(set(kategorie) | {i for _, _, hod in rady for i in hod})[:200]
    tabulka = [[""] + [r[0] for r in rady]] + [[kategorie.get(i, str(i + 1))] + [r[2].get(i, "") for r in rady] for i in indexy]
    return [f"[graf: {nazev}]" if nazev else "[graf]", tabulka_md(tabulka)]


def z_pptx(cesta, info, slozka):
    bloky, kandidati = [], []
    with zipfile.ZipFile(cesta) as z:
        jmena = set(z.namelist())
        slajdy = sorted(
            (n for n in jmena if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)),
        )
        for i, n in enumerate(slajdy, 1):
            xml = precti_cast(z, n)
            rel = vztahy(z, n)
            nadpis = ""
            for m in re.finditer(r"<p:sp(?:\s[^>]*)?>.*?</p:sp>", xml, re.S):
                if re.search(r'<p:ph\b[^>]*type="(?:title|ctrTitle)"', m.group(0)):
                    nadpis = " ".join(xml_odstavce(m.group(0), "a:p", "a:t"))
                    xml = xml[:m.start()] + xml[m.end():]
                    break
            radky = xml_odstavce(re.sub(r"<a:tbl\b.*?</a:tbl>", "", xml, flags=re.S), "a:p", "a:t")
            textu = len("".join(radky))
            radky += pptx_tabulky(xml)
            for rid in re.findall(r'<dgm:relIds\b[^>]*\br:dm="([^"]+)"', xml):  # SmartArt
                if rid in rel and rel[rid][1] in jmena:
                    radky += xml_odstavce(precti_cast(z, rel[rid][1]), "a:p", "a:t")
            for rid in re.findall(r'<c:chart\b[^>]*\br:id="([^"]+)"', xml):
                if rid in rel:
                    radky += graf(z, rel[rid][1])
            for typ, cil, _ in rel.values():
                if typ == "notesSlide" and cil in jmena:
                    pozn = [r for r in xml_odstavce(precti_cast(z, cil), "a:p", "a:t") if not r.isdigit()]
                    if pozn:
                        radky += ["[poznámky řečníka]"] + pozn
            radky += odkazy(rel)
            if "<p:pic" in xml and textu < MALO_TEXTU:
                info["obrazove"].append(i)
                for rid in re.findall(r'<a:blip\b[^>]*\br:embed="([^"]+)"', xml):
                    cil = rel.get(rid, ("", "", True))[1]
                    if cil in jmena and posixpath.splitext(cil)[1].lower() in OBRAZKY_OCR and z.getinfo(cil).file_size <= MAX_CAST:
                        if z.getinfo(cil).file_size >= OCR_MIN_VELIKOST:
                            kandidati.append((len(bloky), i, cil))
                        else:  # malý obrázek na obrazovém slajdu: nečte se, ale nesmí zmizet potichu
                            info["neprecteno"].setdefault("male", []).append(i)
            hlava = f"=== slajd {i}: {nadpis} ===" if nadpis else f"=== slajd {i} ==="
            bloky.append(hlava + "\n" + "\n".join(radky))
        # obrázky slajdů „hlavně obrázek“ vybalit do cache (AI se na ně může podívat) a přečíst z nich text
        vybrane, videne = [], set()
        for b, i, cil in kandidati:
            if cil not in videne and len(vybrane) >= OCR_MAX_OBRAZKU:
                info["neprecteno"].setdefault("limit_obrazku", []).append(i)
            if cil not in videne and len(vybrane) < OCR_MAX_OBRAZKU:
                videne.add(cil)
                slozka.mkdir(parents=True, exist_ok=True)
                soubor = slozka / f"slajd{i}-{len(vybrane) + 1}{posixpath.splitext(cil)[1].lower()}"
                soubor.write_bytes(z.read(cil))
                vybrane.append((b, soubor))
    for (b, soubor), text in zip(vybrane, ocr_obrazku([s for _, s in vybrane])):
        info["obrazky"].append(soubor)
        if text is None:
            info["odlozeno"] = True
        elif len(re.sub(r"\s", "", text)) >= 10:
            bloky[b] += "\n[text z obrázku]\n" + text
            info["ocr"] += 1
    return bloky


def z_docx(cesta, info, slozka):
    with zipfile.ZipFile(cesta) as z:
        xml = precti_cast(z, "word/document.xml")
        rel = vztahy(z, "word/document.xml")
        grafy = [r for rid in re.findall(r'<c:chart\b[^>]*\br:id="([^"]+)"', xml) if rid in rel for r in graf(z, rel[rid][1])]
        # obrázky (grafy, schémata ve Wordu): vybalit do cache pro AI a přečíst OCR; loga a ikony (malé) ne
        media = sorted((n for n in z.infolist() if n.filename.startswith("word/media/") and OCR_MIN_VELIKOST <= n.file_size <= MAX_CAST
                        and posixpath.splitext(n.filename)[1].lower() in OBRAZKY_OCR),
                       key=lambda n: [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", n.filename)])
        if len(media) > OCR_MAX_OBRAZKU:
            info["neprecteno"]["obrazky_dokumentu"] = [len(media) - OCR_MAX_OBRAZKU]
        vybrane = []
        for n in media[:OCR_MAX_OBRAZKU]:
            slozka.mkdir(parents=True, exist_ok=True)
            soubor = slozka / f"obrazek{len(vybrane) + 1}{posixpath.splitext(n.filename)[1].lower()}"
            soubor.write_bytes(z.read(n.filename))
            vybrane.append(soubor)
    texty_obrazku = []
    for soubor, text in zip(vybrane, ocr_obrazku(vybrane)):
        info["obrazky"].append(soubor)
        if text is None:
            info["odlozeno"] = True
        elif len(re.sub(r"\s", "", text)) >= 10:
            texty_obrazku += ["[text z obrázku]", text]
            info["ocr"] += 1
    radky = []
    for kus, je_tabulka in docx_kusy(xml):
        if je_tabulka:
            radky.append(docx_tabulka(kus))
            continue
        for p in kus.split("</w:p>"):
            text = html.unescape("".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", p))).strip()
            if not text:
                continue
            styl = re.search(r'<w:pStyle w:val="(?:Heading|Nadpis)(\d)"', p)
            radky.append(("#" * int(styl.group(1)) + " " if styl else "") + text)
    return ["\n".join([r for r in radky if r] + grafy + texty_obrazku + odkazy(rel))]


def zbyva_ocr():
    return OCR_ROZPOCET - (time.monotonic() - ZACATEK)


def ocr_zapnuto():
    return sys.platform == "darwin" and nastaveni().get("ocr", True) is not False


def ocr_jazyky():
    return ",".join(OCR_JAZYKY.get(nastaveni().get("jazyk"), OCR_JAZYKY["cs"]))


class OcrNedostupne(Exception):
    """Text z PDF ani OCR teď přečíst nejde (osascript nefunguje) – cache se nepřepíše, zkusí se příště."""


def osascript(argumenty, cas):
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", OCR_JXA, *argumenty],
                       capture_output=True, text=True, encoding="utf8", timeout=cas)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def ocr_obrazku(cesty):
    """Text z obrázků přes macOS Vision – pro každý text, "" (nic/OCR nejde) nebo None (došel čas, zkusí se příště)."""
    if not cesty or not ocr_zapnuto():
        return [""] * len(cesty)
    zbyva = zbyva_ocr()
    if zbyva < 5:
        return [None] * len(cesty)
    try:
        v = osascript(["obrazky", str(int((time.time() + zbyva) * 1000)), ocr_jazyky(), *map(str, cesty)], zbyva + 60)
    except subprocess.TimeoutExpired:
        return [None] * len(cesty)
    except (ValueError, OSError):
        v = None
    if v is None:  # osascript nejde – zkusí se příště, ne „obrázek bez textu“
        return [None] * len(cesty)
    return v if isinstance(v, list) and len(v) == len(cesty) else [""] * len(cesty)


def z_pdf(cesta, info, slozka):
    zbyva = max(zbyva_ocr(), 0) if ocr_zapnuto() else 0
    strany = osascript(["pdf", str(int((time.time() + zbyva) * 1000) if zbyva >= 5 else 0), ocr_jazyky(),
                        str(cesta), str(OCR_MAX_STRAN)], 300 + zbyva)
    if not strany:  # osascript nejde nebo PDF neotevřel (sandbox, chyba macOS) – nezapisovat prázdnou cache
        raise OcrNedostupne(cesta.name)
    bloky = []
    for i, s in enumerate(strany, 1):
        text = (s.get("t") or "").strip()
        info["ocr"] += s.get("o") == 1
        info["odlozeno"] |= s.get("o") == 2 and ocr_zapnuto()
        if s.get("o") == 3:
            info["neprecteno"].setdefault("limit_stran", []).append(i)
        if len(re.sub(r"\s", "", text)) < MALO_TEXTU and s.get("o") != 2:
            info["obrazove"].append(i)
        bloky.append(f"=== strana {i} ===\n{text}")
    return bloky


def z_obrazek(cesta, info, slozka):
    text = ocr_obrazku([cesta])[0]
    if text is None:
        info["odlozeno"] = True
    elif len(re.sub(r"\s", "", text)) >= 10:
        info["ocr"] = 1
        return [text]
    return []


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
    # řádky tabulek a značky jako [poznámky řečníka] se opakují záměrně
    opakovane = {r for r, n in pocty.items() if n >= hranice and len(bloky) >= 4
                 and not r.startswith("|") and not re.fullmatch(r"\[[^\]]+\]", r)}
    ciste = []
    for b in bloky:
        radky = b.splitlines()
        hlava, telo = (radky[0], radky[1:]) if radky and radky[0].startswith("===") else ("", radky)
        telo = [re.sub(r"[ \t]+", " ", r).strip() for r in telo]
        telo = [r for r in telo if r and r not in opakovane and not re.fullmatch(r"\d{1,3}", r)]
        if telo:
            ciste.append((hlava + "\n" if hlava else "") + "\n".join(telo))
    return "\n\n".join(ciste), len(opakovane)


def extrahuj(cesta, info, slozka):
    """Vrátí (bloky, typ); do info doplní počet stran/obrázků s OCR, slajdy/strany „hlavně obrázek“ a vybalené obrázky."""
    pripona = cesta.suffix.lower()
    if pripona == ".pptx":
        return z_pptx(cesta, info, slozka), "prezentace"
    if pripona == ".docx":
        return z_docx(cesta, info, slozka), "dokument"
    if pripona == ".pdf":
        return z_pdf(cesta, info, slozka), "pdf"
    if pripona in OBRAZKY:
        return z_obrazek(cesta, info, slozka), "obrázek"
    if pripona == ".webloc":
        return z_webloc(cesta), "odkaz"
    return z_textutil(cesta), "text"


def nastaveni():
    try:
        data = json.loads(NASTAVENI.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}  # pole nebo číslo místo objektu = jako bez nastavení


def texty():
    """Texty pro Fronta.md a výpis v jazyce z nastaveni.json (cs, sk, en, uk); chybějící doplní čeština."""
    jazyk = "cs"
    try:
        jazyk = json.loads(NASTAVENI.read_text()).get("jazyk") or "cs"
    except Exception:
        pass
    data = json.loads((SYS / "texty.json").read_text(encoding="utf8"))
    return {**data["cs"], **data.get(jazyk if isinstance(jazyk, str) else "cs", {})}


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
        if not p.is_file() or {nfc(x) for x in rel.parts[:-1]} & VYNECHAT or p.name.startswith("."):
            continue
        if len(rel.parts) == 1:  # soubory v kořeni trezoru (Domov apod.)
            continue
        if p.name.startswith(("~$", ".~lock")):  # dočasné soubory otevřených dokumentů
            continue
        if VLASTNI_PREFIX and p.name.startswith(VLASTNI_PREFIX):  # vlastní práce vytvořené ze šablony
            continue
        if p.suffix.lower() in TEXTOVE | OBRAZKY:
            yield p, nfc(str(rel))


def soubor_v_trezoru(cesta):
    koren, p = TREZOR.resolve(), (TREZOR / cesta).resolve()  # absolutní cesta TREZOR nahradí
    if not cesta.strip() or not p.is_relative_to(koren) or not p.is_file():  # složka, prázdná nebo cesta ven
        sys.exit(f"Soubor v trezoru neexistuje: {cesta!r}")
    return p, nfc(str(p.relative_to(koren)))


def je_bez_ai():
    try:
        return json.loads(NASTAVENI.read_text()).get("ai") == "zadna"
    except Exception:
        return False


def oznac(cesta, stav, poznamka=None):
    p, rel = soubor_v_trezoru(cesta)
    if stav == "hotovo":
        T = texty()
        bez_ai = je_bez_ai()
        if not bez_ai:
            over_slouceni(rel, poznamka, T)
        data, pozn = kontroluj(p, rel, poznamka)
        if data["chybi"] and not bez_ai:
            sys.exit(T["kontrola_neoznaceno"].format(c=len(data["chybi"])))
        if pozn and frontmatter(pozn).get("typ") != "predmet":  # přehled předmětu (osnova) vlastnost nedostane
            # sloučená poznámka (verze téhož textu) je úplná, jen když jsou úplné všechny její zdroje
            nastav_vlastnost(pozn, "uplnost", "k-overeni" if mezera(data) or mezera_dalsich_zdroju(pozn, rel) else "uplna")
    reg = nacti_registr()
    reg[rel] = {"otisk": otisk(p), "stav": stav, "datum": date.today().isoformat(), **podpis(p)}
    uloz_registr(reg)
    print(f"{stav}: {rel}")


# ---------- Kontrola úplnosti ----------
# Skript z cache sestaví povinné položky (nadpisy, definice, tabulky, grafy, data, čísla, jména, odkazy, výčty)
# a ověří, že se v poznámce opravdu vyskytují. Co chybí, musí AI doplnit, nebo vynechání zdůvodnit (--vynech).
# Důležitost posoudit neumí – proto druhé čtení AI a místa „k ověření“.

def bez_diakritiky(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)).lower()


def klic_slova(w):
    """Kmen pro porovnání: skloňování mění konec slova (katalog/katalogu, cíl/cíle)."""
    return w[:4] if len(w) >= 5 else w[:3]


def klice(text):
    return [klic_slova(w) for w in re.findall(r"[^\W\d_]+", bez_diakritiky(text)) if len(w) >= 3 and w not in NEVYZNAMNA]


def data_v(text):
    """Data v textu jako „RRRR-MM-DD“ (bez roku „-MM-DD“): 30. 11. 2026, 30. listopadu 2026 i 2026-11-30."""
    vysledek = set()
    for d, m, r in K_DATUM.findall(text):
        vysledek.add(f"{r}-{int(m):02}-{int(d):02}")
    for d, m, r in K_DATUM_SLOVEM.findall(text):
        vysledek.add(f"{r}-{MESICE[m.lower()]:02}-{int(d):02}")
    for r, m, d in ISO_DATUM.findall(text):
        vysledek.add(f"{r}-{int(m):02}-{int(d):02}")
    return vysledek


def bez_dat(text):
    for vzor in (K_DATUM, K_DATUM_SLOVEM, ISO_DATUM):
        text = vzor.sub(" ", text)
    return text


def cisla_v(text):
    return {re.sub(r"[  ]", "", c).replace(",", ".") for c in CISLO.findall(bez_dat(text))}


def ciste_url(u):
    return re.sub(r"^https?://(www\.)?", "", u.strip().lower()).rstrip("/.,;")


def jmena_v(radek):
    """Víceslovná jména uprostřed věty (Jan Novák, Dublin Core); první slovo věty se nepočítá."""
    slova = list(re.finditer(r"[^\W\d_]+|[.!?:;]", radek))
    vysledek, rada = [], []
    for i, m in enumerate(slova):
        w = m.group(0)
        zacatek_vety = i == 0 or slova[i - 1].group(0) in ".!?:;"
        if len(w) > 1 and w[0].isupper() and w[1:].islower() and (rada or not zacatek_vety):
            rada.append(w)
            continue
        if len(rada) >= 2:
            vysledek.append(" ".join(rada))
        rada = []
    if len(rada) >= 2:
        vysledek.append(" ".join(rada))
    return vysledek


def polozky_kontroly(text, typ):
    """Povinné položky z textu cache. Každá má id, druh, text, kde a podklady pro porovnání (k, c, d, u, podil)."""
    polozky, videne, pocty = [], set(), Counter()
    kde, cislo_radku = "", 0  # řádek položky v cache – podle něj kontrola po kapitolách

    def pridej(druh, popis, podil=1.0, **podklad):
        popis = re.sub(r"\s+", " ", popis).strip()
        if not any(podklad.values()):
            return
        podklad = {k: sorted(v) for k, v in podklad.items() if v}
        znacka = (druh, json.dumps(podklad, sort_keys=True, ensure_ascii=False))
        if znacka in videne:
            return
        videne.add(znacka)
        pocty[druh] += 1
        predpona = {"nadpis": "n", "definice": "d", "tabulka": "t", "graf": "g", "datum": "dt", "cislo": "c",
                    "jmeno": "j", "odkaz": "o", "vycet": "v"}[druh]
        polozky.append({"id": f"{predpona}{pocty[druh]}", "druh": druh, "text": popis[:90], "kde": kde, "podil": podil,
                        "r": cislo_radku, **podklad})

    def tabulka(radky, nazev=""):
        bunky = [b.strip().replace("\\|", "|") for r in radky if not re.fullmatch(r"\|[-|: ]*\|", r)
                 for b in re.split(r"(?<!\\)\|", r.strip().strip("|"))]
        slova = {k[0] for b in bunky if (k := klice(b))}
        cisla = set().union(*(cisla_v(b) for b in bunky)) if bunky else set()
        return slova | set(klice(nazev)), cisla

    radky = text.splitlines()
    i = 0
    vycet = []

    def uzavri_vycet():
        if len(vycet) >= 3:
            kmeny = [max(k, key=len) for r in vycet if (k := klice(r))]
            pridej("vycet", "; ".join(vycet[:3]) + (" …" if len(vycet) > 3 else ""), 0.6, k=kmeny)
        vycet.clear()

    while i < len(radky):
        r = radky[i].strip()
        dalsi = next((x.strip() for x in radky[i + 1:] if x.strip()), "")
        cislo_radku = i
        i += 1
        if not r:
            continue
        hlava = re.fullmatch(r"=== (slajd|strana) (\d+)(?:: (.*))? ===", r)
        if hlava:
            uzavri_vycet()
            kde = f"{hlava.group(1)} {hlava.group(2)}"
            if hlava.group(3):
                pridej("nadpis", hlava.group(3), 0.5, k=set(klice(hlava.group(3))))
            continue
        if r.startswith("[graf"):
            uzavri_vycet()
            nazev = r[len("[graf"):].strip(" :]")
            tab = []
            while i < len(radky) and radky[i].strip().startswith("|"):
                tab.append(radky[i].strip())
                i += 1
            slova, cisla = tabulka(tab, nazev)
            pridej("graf", nazev or (tab[0] if tab else "graf"), 0.5, k=slova, c=cisla)
            continue
        if r.startswith("|"):
            uzavri_vycet()
            tab = [r]
            while i < len(radky) and radky[i].strip().startswith("|"):
                tab.append(radky[i].strip())
                i += 1
            slova, cisla = tabulka(tab)
            pridej("tabulka", tab[0].strip("| "), 0.5, k=slova, c=cisla)
            continue
        for u in URL.findall(r):
            pridej("odkaz", u, u={ciste_url(u)})
        if r.startswith("[odkazy]"):
            continue
        if re.fullmatch(r"\[[^\]]+\]", r) or "©" in r:  # značky jako [poznámky řečníka], patička s copyrightem
            continue
        nadpis_md = re.match(r"#{1,6}\s+(.*)", r)
        if nadpis_md:
            uzavri_vycet()
            pridej("nadpis", nadpis_md.group(1), 0.5, k=set(klice(nadpis_md.group(1))))
            continue
        odrazka = ODRAZKA.match(r) or (r[:2] == "o " and r[2:3].isupper())
        obsah = r[odrazka.end():] if hasattr(odrazka, "end") else r[2:] if odrazka else r
        if odrazka:
            vycet.append(obsah)
        else:
            uzavri_vycet()
            # nadpis bez značky (PDF, prostý text): krátký řádek bez interpunkce na konci, za ním další text
            # zalomený řádek sloupce pokračuje malým písmenem; „X – …“ je začátek definice, ne nadpis
            if (typ in ("pdf", "text", "obrázek") and dalsi and 2 <= len(r) <= 60 and len(r.split()) <= 7 and r[0].isupper()
                    and not re.search(r"[.,:;!?]$|,|\s[–—-]\s|:\s", r) and not dalsi[0].islower() and klice(r)):
                pridej("nadpis", r, 0.5, k=set(klice(r)))
                continue
        definice = re.match(r"([^\W\d_][^:–—=]{1,48}?)\s*(?:\s[–—=-]\s|:\s)\s*\S", obsah)
        zalomeno = typ in ("pdf", "text", "obrázek") and not obsah[0].isupper()  # pokračování zalomené věty, ne definice
        if definice and not zalomeno and len(definice.group(1).split()) <= 5 and "//" not in definice.group(1):
            pridej("definice", obsah, k=set(klice(definice.group(1))))
        for d in data_v(obsah):
            pridej("datum", d, d={d})
        for c in cisla_v(obsah):
            cele = c.split(".")[0]
            if len(cele) >= 2 or "." in c or re.search(re.escape(c.replace(".", ",")) + r"\s?%", obsah):
                pridej("cislo", c + "  ← " + obsah[:70], c={c})
        for j in jmena_v(obsah):
            prijmeni = re.findall(r"[^\W\d_]+", bez_diakritiky(j))[-1]  # jména se skloňují víc (Čapek/Čapka)
            pridej("jmeno", j, k={prijmeni[:min(4, max(3, len(prijmeni) - 2))]})
    uzavri_vycet()
    return polozky


def je_pokryta(polozka, slova, cisla, data, text):
    if "u" in polozka:
        return all(u in text for u in polozka["u"])
    if "d" in polozka:  # „-MM-DD“ = datum bez roku, stačí shoda dne a měsíce
        return all(any(x.endswith(d) for x in data) if d.startswith("-") else d in data for d in polozka["d"])
    vsechny = [("k", k) for k in polozka.get("k", [])] + [("c", c) for c in polozka.get("c", [])]
    if not vsechny:
        return True
    nalezeno = sum(1 for druh, v in vsechny if (v in slova if druh == "k" else v in cisla))
    return nalezeno >= max(1, polozka["podil"] * len(vsechny) - 1e-9)


def odkazy_zdroju(p):
    """Názvy souborů z vlastností `zdroj` a `zdroje` poznámky (jeden odkaz i seznam)."""
    text = p.read_text(errors="ignore")
    if not text.startswith("---") or text.count("---") < 2:
        return set()
    nazvy, klic = set(), None
    for radek in text.split("---", 2)[1].splitlines():
        m = re.match(r"([\w]+):", radek)
        if m:
            klic = m.group(1)
        if klic in ("zdroj", "zdroje"):
            for odkaz in re.findall(r"\[\[([^\]|#]+)", radek):
                nazvy.add(nfc(odkaz.strip().rsplit("/", 1)[-1]))
    return nazvy


def najdi_poznamku(rel, zadana):
    T = texty()
    if zadana is not None:
        koren, p = TREZOR.resolve(), (TREZOR / zadana).resolve()
        if (not zadana.strip() or not p.is_relative_to(koren) or p.suffix.lower() != ".md" or not p.is_file()
                or nfc(p.relative_to(koren).parts[0]) in VYNECHAT - {"_Pojmy", "_Přehledy", "_Zdroje", "Poznámky"} | {".druhy-mozek-zaloha"}):
            sys.exit(T["kontrola_spatna_poznamka"].format(p=zadana))
        return p
    jmeno = nfc(Path(rel).name)
    hledam = {jmeno, nfc(Path(rel).stem)}
    koren = TREZOR.resolve()
    nalezene = [(p, r) for p, r in poznamky() if p.resolve().is_relative_to(koren) and odkazy_zdroju(p) & hledam]  # odkaz ven ne
    if len(nalezene) > 1:  # stejný název souboru ve víc předmětech → přednost má stejný předmět
        stejny = [x for x in nalezene if x[1].split("/")[0] == rel.split("/")[0]]
        nalezene = stejny if stejny else nalezene
    if not nalezene:
        return None
    if len(nalezene) > 1:
        sys.exit(T["kontrola_vic_poznamek"].format(n=jmeno, s=", ".join(r for _, r in nalezene), m=rel))
    return nalezene[0][0]


def rozsahy(cisla):
    """[1, 2, 3, 7] → „1-3,7“ (do hlavičky cache, bez mezer a svislítek)."""
    cisla, vysledek = sorted(set(cisla)), []
    for c in cisla:
        if vysledek and c == vysledek[-1][1] + 1:
            vysledek[-1][1] = c
        else:
            vysledek.append([c, c])
    return ",".join(f"{a}-{b}" if a != b else str(a) for a, b in vysledek)


def neprectene(hlava, T):
    """Co skript z materiálu nepřečetl (z hlavičky cache) jako texty pro frontu, kontrolu a Domov."""
    vysledek = []
    m = re.search(r"\| neprecteno: ([^|]*?)\s*(?:\||-->)", hlava)
    for cast in (m.group(1).split(";") if m else []):
        kod, _, hodnota = cast.partition("=")
        hodnota = re.sub(r"[^\d,-]", "", hodnota).replace(",", ", ").replace("-", "–")
        if f"np_{kod}" in T and hodnota:
            vysledek.append(T[f"np_{kod}"].format(s=hodnota))
    if "ocr_odlozeno" in hlava:
        vysledek.append(T["np_odlozeno"])
    return vysledek


def telo_cache(text):
    return text.split("\n", 1)[-1]


def rozdel_kapitoly(telo):
    """Rozdělí text cache na kapitoly do KAPITOLA tokenů – jen na hranici slajdu, strany nebo nadpisu
    (bez nich po odstavcích, nikdy uprostřed tabulky). Vrátí [{od_radku, do_radku, od, do, tokeny}]."""
    radky = telo.split("\n")
    znacka = re.compile(r"=== (slajd|strana) (\d+)|#{1,6} (.*)")
    hranice = [i for i, r in enumerate(radky) if znacka.match(r)]
    if not hranice:  # prostý text: každý odstavec mimo pokračování tabulky
        hranice = [i for i, r in enumerate(radky) if r.strip() and not (r.startswith("|") and i and radky[i - 1].startswith("|"))]
    hranice = sorted(set([0] + hranice))
    useky = [(a, b) for a, b in zip(hranice, hranice[1:] + [len(radky)])]

    def stitek(i):
        m = znacka.match(radky[i])
        if m and m.group(1):
            return f"{m.group(1)} {m.group(2)}"
        return (m.group(3) if m else radky[i].strip())[:40] or f"řádek {i + 1}"

    kapitoly, od, velikost = [], 0, 0
    for a, b in useky:
        delka = tokeny("\n".join(radky[a:b]))
        if velikost and velikost + delka > KAPITOLA:
            kapitoly.append((od, a))
            od, velikost = a, 0
        velikost += delka
    kapitoly.append((od, len(radky)))
    vysledek = []
    for a, b in kapitoly:
        prvni = next((i for i in range(a, b) if radky[i].strip()), a)
        posledni = max((i for i in hranice if a <= i < b and radky[i].strip()), default=prvni)
        vysledek.append({"od_radku": a, "do_radku": b, "od": stitek(prvni), "do": stitek(posledni),
                         "tokeny": tokeny("\n".join(radky[a:b]))})
    return vysledek


def zapis_kapitoly(cil, text):
    """Kapitoly velkého materiálu jako samostatné soubory cache vedle celé cache (AI čte jen jednu najednou)."""
    hlava, telo = text.split("\n", 1)[0], telo_cache(text)
    zdroj = (re.search(r"zdroj: ([^|]*)\|", hlava) or [None, ""])[1].strip()
    radky, kapitoly = telo.split("\n"), rozdel_kapitoly(telo)
    vysledek = []
    for n, k in enumerate(kapitoly, 1):
        soubor = cil.with_name(f"{cil.stem}-k{n:02}.md")
        soubor.write_text(f"<!-- zdroj: {zdroj} | kapitola: {n}/{len(kapitoly)} | od: {k['od']} | do: {k['do']} -->\n\n"
                          + "\n".join(radky[k["od_radku"]:k["do_radku"]]).strip() + "\n")
        vysledek.append({"cast": n, "cache": str(soubor.relative_to(TREZOR)), "od": k["od"], "do": k["do"], "tokeny": k["tokeny"]})
    return vysledek


def k_overeni_hotovych(reg, T):
    """Hotové materiály s místy k ověření: [(poznámka, zdroj, místa)]. Kontroly smazaných a změněných materiálů zahodí."""
    if not KONTROLA.is_dir():
        return []
    platne = {v["otisk"][:16]: k for k, v in reg.items()}
    vysledek = []
    for f in sorted(KONTROLA.glob("*.json")):
        if f.stem not in platne:
            f.unlink()
            continue
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        rel = platne[f.stem]
        if not isinstance(data, dict) or reg[rel]["stav"] != "hotovo":
            continue
        podle_id = {x["id"]: x for x in data.get("polozky") or [] if isinstance(x, dict) and "id" in x}
        mista = [T["k_overeni_neprecteno"].format(s=m["text"]) for m in zbyva_neprecteno(data)] + \
                [str(m) for m in data.get("k_overeni") or []] + \
                [f"{T.get('druh_' + str(podle_id[i].get('druh')), '')}: {podle_id[i].get('text', '')}"
                 for i in data.get("chybi") or [] if i in podle_id]
        if mista:
            pozn = Path(str(data.get("poznamka") or rel)).stem
            vysledek.append((re.sub(r"[\[\]|\x00-\x1f]", " ", pozn), Path(rel).name,
                             [html.escape(re.sub(r"[\x00-\x1f]", " ", m), quote=False) for m in mista]))
    return vysledek


def soubor_kontroly(p):
    return KONTROLA / f"{otisk(p)[:16]}.json"


def nacti_kontrolu(p):
    try:
        data = json.loads(soubor_kontroly(p).read_text())
        return data if isinstance(data, dict) and data.get("verze") == KONTROLA_VERZE else None
    except Exception:
        return None


def kontroluj(p, rel, zadana=None, tisk=True, kapitola=None):
    """Porovná položky cache s poznámkou, výsledek uloží a vypíše. Vrátí (data, poznámka nebo None)."""
    T = texty()
    h = otisk(p)
    cache = CACHE / f"{h[:16]}.md"
    pozn = najdi_poznamku(rel, zadana)
    bez_ai = je_bez_ai()
    if pozn is None and not bez_ai:
        sys.exit(T["kontrola_chybi_poznamka"].format(n=Path(rel).name, m=rel))
    if pozn is None:  # bez AI a bez poznámky (zpracováno jinde, třeba na papíře) – není co porovnat
        return {"chybi": [], "k_overeni": []}, None
    rozsah, kap_info = None, ""
    if cache.exists():
        obsah = cache.read_text(errors="ignore")
        typ = (re.search(r"\| typ: ([^|]+)", obsah.split("\n", 1)[0]) or [None, ""])[1].strip()
        polozky = polozky_kontroly(telo_cache(obsah), typ)
        neprecteno = [{"id": f"np{n}", "text": x} for n, x in enumerate(neprectene(obsah.split("\n", 1)[0], T), 1)]
        if kapitola is not None:
            kapitoly = rozdel_kapitoly(telo_cache(obsah))
            if not (kapitola.isascii() and kapitola.isdigit() and 1 <= int(kapitola) <= len(kapitoly)):
                sys.exit(T["kontrola_kapitola"].format(n=len(kapitoly)))
            k = kapitoly[int(kapitola) - 1]
            rozsah = range(k["od_radku"], k["do_radku"])
            kap_info = T["kontrola_kapitola_info"].format(n=kapitola, c=len(kapitoly), od=k["od"], do=k["do"])
    elif kapitola is not None:
        sys.exit(T["kontrola_bez_cache"])
    else:
        polozky, neprecteno = [], []
    stara = nacti_kontrolu(p) or {}
    ids = {x["id"] for x in polozky} | {x["id"] for x in neprecteno}
    data = {"verze": KONTROLA_VERZE, "zdroj": rel, "otisk": h, "datum": date.today().isoformat(),
            "poznamka": nfc(str(pozn.resolve().relative_to(TREZOR.resolve()))) if pozn else None,
            "polozky": polozky, "pokryto": [], "chybi": [],
            "vynechano": {k: v for k, v in (stara.get("vynechano") or {}).items() if k in ids},
            "k_overeni": list(stara.get("k_overeni") or []), "neprecteno": neprecteno}
    if pozn:
        text = pozn.read_text(errors="ignore")
        if text.startswith("---") and text.count("---") >= 2:
            text = text.split("---", 2)[2]
        slova = set(klice(text))
        slova |= {k[:3] for k in slova}  # krátké kmeny (jména, slova do 4 písmen) stačí na začátek slova
        cisla, dat = cisla_v(text), data_v(text)
        nizko = text.lower()
        for x in polozky:
            pokryta = je_pokryta(x, slova, cisla, dat, nizko)
            data["pokryto" if pokryta else "chybi"].append(x["id"])
        data["chybi"] = [i for i in data["chybi"] if i not in data["vynechano"]]
    KONTROLA.mkdir(parents=True, exist_ok=True)
    soubor_kontroly(p).write_text(json.dumps(data, ensure_ascii=False, indent=1))
    if tisk:
        podle_id = {x["id"]: x for x in polozky}
        v_kapitole = (lambda i: podle_id[i]["r"] in rozsah) if rozsah else (lambda i: True)
        vypis = {k: [i for i in data[k] if v_kapitole(i)] for k in ("pokryto", "chybi")}
        if kap_info:
            print(kap_info)
        print(T["kontrola_vysledek"].format(m=rel, p=data["poznamka"] or "—", a=len(vypis["pokryto"]),
                                            b=sum(1 for x in polozky if v_kapitole(x["id"])), v=len(data["vynechano"]),
                                            c=len(vypis["chybi"]), k=len(data["k_overeni"])))
        if not cache.exists():
            print(T["kontrola_bez_cache"])
        for x in zbyva_neprecteno(data):
            print(T["kontrola_neprecteno"].format(id=x["id"], s=x["text"]))
        for i in vypis["chybi"]:
            x = podle_id[i]
            print(T["kontrola_polozka"].format(id=i, druh=T.get("druh_" + x["druh"], x["druh"]), text=x["text"],
                                               kde=f" ({x['kde']})" if x["kde"] else ""))
        if vypis["chybi"] and not bez_ai:  # bez AI uživatel příkazy nepíše, výsledek mu ukáže rozšíření
            print(T["kontrola_rada"].format(m=rel))
        if bez_ai:
            print(T["kontrola_bez_ai"])
    return data, pozn


def vynech(cesta, ids, duvod):
    T = texty()
    p, rel = soubor_v_trezoru(cesta)
    data = nacti_kontrolu(p)
    if not data:
        sys.exit(T["kontrola_nejdriv"].format(m=rel))
    duvod = re.sub(r"[\x00-\x1f\x7f]+", " ", duvod).strip()[:VYNECH_MAX]
    if not duvod:
        sys.exit(T["kontrola_duvod"])
    vybrane = [i.strip() for i in ids.split(",") if i.strip()]
    nezname = [i for i in vybrane if i not in {x["id"] for x in data["polozky"]} | {x.get("id") for x in data.get("neprecteno") or []
                                                                                  if isinstance(x, dict)}]
    if nezname or not vybrane:
        sys.exit(T["kontrola_nezname_id"].format(s=", ".join(nezname) or "—"))
    data["vynechano"].update({i: duvod for i in vybrane})
    data["chybi"] = [i for i in data["chybi"] if i not in data["vynechano"]]
    soubor_kontroly(p).write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(T["kontrola_vynechano"].format(s=", ".join(vybrane)))


def pridej_k_overeni(cesta, text):
    T = texty()
    p, rel = soubor_v_trezoru(cesta)
    data = nacti_kontrolu(p) or {"verze": KONTROLA_VERZE, "zdroj": rel, "otisk": otisk(p), "polozky": [], "pokryto": [],
                                 "chybi": [], "vynechano": {}, "k_overeni": [], "poznamka": None}
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text).strip()[:VYNECH_MAX]
    if not text:
        sys.exit(T["kontrola_text_prazdny"])
    if text not in data["k_overeni"]:
        data["k_overeni"] = (data["k_overeni"] + [text])[-K_OVERENI_MAX:]
    KONTROLA.mkdir(parents=True, exist_ok=True)
    soubor_kontroly(p).write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(T["kontrola_k_overeni"].format(n=len(data["k_overeni"]), s=text))


def mezera(data):
    return bool(data.get("chybi") or data.get("k_overeni") or zbyva_neprecteno(data))


def zdroje_poznamky(pozn, reg):
    """Materiály z registru, na které poznámka odkazuje ve `zdroj`/`zdroje` (stejný název jinde → přednost má předmět poznámky)."""
    nazvy = odkazy_zdroju(pozn)
    try:
        predmet = nfc(str(pozn.resolve().relative_to(TREZOR.resolve()))).split("/")[0]
    except ValueError:  # odkaz ven z trezoru – předmět neznáme
        predmet = ""
    podle_nazvu = {}
    for k in reg:
        for n in {nfc(Path(k).name), nfc(Path(k).stem)} & nazvy:
            podle_nazvu.setdefault(n, []).append(k)
    vysledek = set()
    for kandidati in podle_nazvu.values():
        stejny = [k for k in kandidati if k.split("/")[0] == predmet]
        vysledek.update(stejny or kandidati)
    return sorted(vysledek)


def mezera_dalsich_zdroju(pozn, rel):
    reg = nacti_registr()
    for k in zdroje_poznamky(pozn, reg):
        if k != rel and reg[k].get("stav") == "hotovo" and (TREZOR / k).is_file():
            data = nacti_kontrolu(TREZOR / k)
            if data and mezera(data):
                return True
    return False


def ctverice_otisku(o):
    """Čtveřice slov z cache (měřítko podobnosti textů), None u krátkého nebo chybějícího textu."""
    c = CACHE / f"{o[:16]}.md"
    if not c.exists():
        return None
    slova = re.findall(r"\w{2,}", c.read_text(errors="ignore").split("\n", 1)[-1].lower())[:PODOBNOST_SLOV]
    ctverice = {" ".join(slova[i:i + 4]) for i in range(max(0, len(slova) - 3))}
    return ctverice if len(ctverice) >= PODOBNOST_MIN else None


def shoda(ta, tb):
    """(verze téhož textu?, shoda v %) – stejné měřítko jako u podobných duplicit."""
    spolecne = len(ta & tb)
    jaccard, obsazeni = spolecne / len(ta | tb), spolecne / min(len(ta), len(tb))
    return jaccard >= 0.5 or obsazeni >= 0.8, round(max(jaccard, obsazeni) * 100)


VICE_ZDROJU = ("predmet", "ukol", "zkouska")  # přehled předmětu a úkol smí odkazovat na víc souborů


def ruzne_zdroje(pozn, reg, jen=None):
    """Dvojice zdrojů poznámky, které nejsou verzemi téhož textu: [(a, b, shoda %)]."""
    if frontmatter(pozn).get("typ") in VICE_ZDROJU:
        return []
    zdroje = [k for k in zdroje_poznamky(pozn, reg) if "otisk" in reg[k]]
    if len(zdroje) < 2:
        return []
    texty_zdroju = {k: ctverice_otisku(reg[k]["otisk"]) for k in zdroje}
    vysledek = []
    for a, b in itertools.combinations(zdroje, 2):
        if jen and jen not in (a, b) or reg[a]["otisk"] == reg[b]["otisk"] or not texty_zdroju[a] or not texty_zdroju[b]:
            continue
        podobne, procent = shoda(texty_zdroju[a], texty_zdroju[b])
        if not podobne:
            vysledek.append((a, b, procent))
    return vysledek


def over_slouceni(rel, zadana, T):
    """Jedna poznámka na materiál: materiál musí být ve zdroji poznámky a sloučit jde jen verze téhož textu."""
    pozn = najdi_poznamku(rel, zadana)
    if pozn is None:
        return
    if zadana is not None and frontmatter(pozn).get("typ") not in VICE_ZDROJU \
            and not {nfc(Path(rel).name), nfc(Path(rel).stem)} & odkazy_zdroju(pozn):
        sys.exit(T["slouceni_zdroj"].format(m=Path(rel).name, p=pozn.stem))
    for a, b, procent in ruzne_zdroje(pozn, nacti_registr(), jen=rel):
        sys.exit(T["slouceni_ruzne"].format(p=pozn.stem, a=Path(a).name, b=Path(b).name, s=procent))


def sloucene_poznamky(reg):
    """Starší poznámky, které slučují různé materiály: [(poznámka, a, b, shoda %)] – k rozdělení."""
    vysledek = []
    for p, _ in poznamky():
        if len(odkazy_zdroju(p)) > 1:
            vysledek += [(p.stem, a, b, s) for a, b, s in ruzne_zdroje(p, reg)]
    return vysledek


def zbyva_neprecteno(data):
    """Nepřečtené části, které AI nevyřešila (`--vynech np1 "přečteno z originálu…"`)."""
    vyreseno = data.get("vynechano") or {}
    return [x for x in data.get("neprecteno") or [] if isinstance(x, dict) and x.get("id") not in vyreseno and "text" in x]


def nastav_vlastnost(p, klic, hodnota):
    """Nastaví jednu vlastnost ve frontmatteru, zbytek poznámky nechá beze změny."""
    text = p.read_text(errors="ignore")
    radek = f"{klic}: {hodnota}"
    if text.startswith("---\n") and "\n---" in text[3:]:
        konec = text.index("\n---", 3)
        blok = text[4:konec]
        if re.search(rf"^{klic}:.*$", blok, re.M):
            blok = re.sub(rf"^{klic}:.*$", radek, blok, count=1, flags=re.M)
        else:
            blok = (blok + "\n" if blok else "") + radek
        text = "---\n" + blok + text[konec:]
    else:
        text = f"---\n{radek}\n---\n\n" + text
    p.write_text(text)


def ciste_jmeno(rel):
    return re.sub(r"[\x00-\x1f\x7f|`]", " ", rel)


def najdi_duplicity(reg):
    """Stejné soubory (hash) a soubory s podobným textem (4 slova za sebou) – jen k zobrazení, nic se nemaže."""
    try:
        nechat = {frozenset(x) for x in json.loads(DUPLICITY_NECHAT.read_text())}
    except (OSError, ValueError, TypeError):
        nechat = set()
    vysledek = []
    for k, v in sorted(reg.items()):
        if v["stav"] == "duplicita" and v.get("stejne_jako") in reg:
            if frozenset((v["otisk"],)) not in nechat:
                vysledek.append({"typ": "stejne", "a": v["stejne_jako"], "b": k, "shoda": 100})
    texty_souboru = {}
    for k, v in sorted(reg.items()):
        if v["stav"] == "duplicita":
            continue
        ctverice = ctverice_otisku(v["otisk"])
        if ctverice:
            texty_souboru[k] = (v["otisk"], ctverice)
    for a, b in itertools.combinations(sorted(texty_souboru), 2):
        (oa, ta), (ob, tb) = texty_souboru[a], texty_souboru[b]
        if oa == ob or frozenset((oa, ob)) in nechat:
            continue
        podobne, procent = shoda(ta, tb)
        if podobne:
            vysledek.append({"typ": "podobne", "a": a, "b": b, "shoda": procent})
    return vysledek


def nechat_obe(a, b):
    """Dvojici si uživatel prohlédl a chce nechat obě – příště se neukáže."""
    reg = nacti_registr()
    if nfc(a) not in reg or nfc(b) not in reg:
        sys.exit(f"Soubor není v registru: {a!r} nebo {b!r}")
    try:
        nechat = json.loads(DUPLICITY_NECHAT.read_text())
    except (OSError, ValueError):
        nechat = []
    nechat.append(sorted({reg[nfc(a)]["otisk"], reg[nfc(b)]["otisk"]}))
    DUPLICITY_NECHAT.write_text(json.dumps(nechat))


CACHE_SOUBOR = re.compile(r"([0-9a-f]{16})(?:\.md|-k\d+\.md|\.stara)?")


def smaz_cache(o):
    """Smaže cache jednoho otisku: text, kapitoly, obrázky i nedokončenou starou složku. Cizí soubory nechá."""
    if not CACHE.is_dir():
        return
    for f in CACHE.iterdir():
        m = CACHE_SOUBOR.fullmatch(f.name)
        if m and m.group(1) == o:
            if f.is_dir() and not f.is_symlink():
                shutil.rmtree(f, ignore_errors=True)
            else:
                f.unlink(missing_ok=True)


def uklid_cache(reg):
    """Cache smazaných a změněných materiálů (otisk už v registru není) se uklidí."""
    platne = {v["otisk"][:16] for v in reg.values() if isinstance(v, dict) and isinstance(v.get("otisk"), str)}
    if not CACHE.is_dir():
        return
    for o in {m.group(1) for f in CACHE.iterdir() if (m := CACHE_SOUBOR.fullmatch(f.name))} - platne:
        smaz_cache(o)


def znovu(cesta):
    """Vrátí materiál do fronty: cache se přečte znovu a AI ho zpracuje jako nový (poznámka zůstane)."""
    T = texty()
    p, rel = soubor_v_trezoru(cesta)
    reg = nacti_registr()
    z = reg.get(rel) or {}
    if z.get("stav") == "duplicita":
        sys.exit(T["znovu_duplicita"].format(m=rel, o=z.get("stejne_jako", "")))
    h = otisk(p)
    for o in {h[:16], str(z.get("otisk", ""))[:16]} - {""}:
        if not any(v.get("otisk", "")[:16] == o and v.get("stav") == "hotovo" for k, v in reg.items() if k != rel):
            smaz_cache(o)
    reg[rel] = {"otisk": h, "stav": "ceka", "datum": date.today().isoformat(), **podpis(p)}
    uloz_registr(reg)
    print(T["znovu_hotovo"].format(m=rel))


def zaloha_registru():
    """Před první migrací nové verze uloží kopii registru (registr.zaloha-<verze>.json); drží poslední 3."""
    try:
        verze = json.loads((TREZOR / ".obsidian/plugins/druhy-mozek/manifest.json").read_text())["version"]
    except Exception:
        return
    if not REGISTR.is_file() or not re.fullmatch(r"\d+\.\d+\.\d+", str(verze)):
        return
    cil = SYS / f"registr.zaloha-{verze}.json"
    if not cil.exists():
        shutil.copy2(REGISTR, cil)
        os.utime(cil)  # pořadí záloh podle doby vzniku, ne podle stáří registru
    zalohy = sorted(SYS.glob("registr.zaloha-*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for stara in zalohy[3:]:
        if stara != cil:
            stara.unlink()


def prehled():
    CACHE.mkdir(parents=True, exist_ok=True)
    T = texty()
    reg = nacti_registr()
    existujici = {rel for _, rel in materialy()}
    # starší registr: „duplicita“ souboru, který už neexistuje (přesunutý originál) → soubor přebírá jeho roli
    # hotovo jen s dokladem (poznámka odkazuje na soubor), jinak jde soubor k posouzení do fronty
    zive = {v["otisk"]: k for k, v in reg.items() if k in existujici and v["stav"] in ("hotovo", "preskoceno")}
    odkazovane = None
    for k, v in reg.items():
        if v["stav"] == "duplicita" and k in existujici and v.get("stejne_jako") not in existujici:
            if v["otisk"] in zive:
                v["stejne_jako"] = zive[v["otisk"]]
                continue
            if odkazovane is None:
                odkazovane = set().union(*(odkazy_zdroju(p) for p, _ in poznamky()))
            v.pop("stejne_jako", None)
            if {nfc(Path(k).name), nfc(Path(k).stem)} & odkazovane:
                v["stav"] = "hotovo"
                zive[v["otisk"]] = k
            else:
                v["stav"] = "ceka"
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
        if h in hotove_otisky and hotove_otisky[h] not in existujici:  # přesunutý nebo přejmenovaný soubor: stav jde s ním
            reg[rel] = {**reg[hotove_otisky[h]], **podpis(p)}
            hotove_otisky[h] = rel
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

        polozka = {"soubor": rel, "predmet": rel.split("/")[0], "velikost_mb": round(p.stat().st_size / 1e6, 1)}
        cil, slozka = CACHE / f"{h[:16]}.md", CACHE / h[:16]
        hlava = cil.read_text().split("\n", 1)[0] if cil.exists() else ""
        verze = re.search(r"\| cache: (\d+)", hlava)
        # cache starší verze nebo s nedočteným OCR (došel čas) se vytvoří znovu
        prepsat = False
        if not verze or int(verze.group(1)) != CACHE_VERZE or "ocr_odlozeno" in hlava:
            zaloha_slozky = slozka.with_name(slozka.name + ".stara")
            shutil.rmtree(zaloha_slozky, ignore_errors=True)
            if slozka.is_dir():
                slozka.rename(zaloha_slozky)
            info = {"ocr": 0, "odlozeno": False, "obrazove": [], "obrazky": [], "neprecteno": {}}
            nedostupne = False
            try:
                bloky, typ = extrahuj(p, info, slozka)
            except OcrNedostupne:
                bloky, typ, nedostupne = [], "pdf", True
                info["odlozeno"] = True
            except Exception as e:  # poškozený nebo zamčený soubor
                bloky, typ = [], "chyba: " + re.sub(r"[\s|]+", " ", str(e))[:200]
            if nedostupne and cil.exists():  # stará cache zůstane, dokud nová nepůjde přečíst
                shutil.rmtree(slozka, ignore_errors=True)
                if zaloha_slozky.is_dir():
                    zaloha_slozky.rename(slozka)
            shutil.rmtree(zaloha_slozky, ignore_errors=True)
            prepsat = not (nedostupne and cil.exists())
        if prepsat:
            text, odstraneno = vycisti(bloky)
            zdroj = re.sub(r"[\x00-\x1f\x7f|]", " ", rel)  # nový řádek v názvu by rozbil hlavičku
            cil.write_text(f"<!-- zdroj: {zdroj} | typ: {typ} | bloků: {len(bloky)} | "
                           f"odstraněno opakujících se řádků: {odstraneno} | cache: {CACHE_VERZE} | ocr: {info['ocr']} | "
                           f"obrazove: {','.join(map(str, info['obrazove']))}"
                           + (" | neprecteno: " + ";".join(f"{k}={rozsahy(v)}" for k, v in info["neprecteno"].items()) if info["neprecteno"] else "")
                           + (" | ocr_odlozeno: 1" if info["odlozeno"] else "") + f" -->\n\n{text}\n")
        text = cil.read_text()
        hlava = text.split("\n", 1)[0]
        typ = re.search(r"\| typ: ([^|]+)", hlava).group(1).strip()
        bloku = int(re.search(r"bloků: (\d+)", hlava).group(1))
        ocr = int(re.search(r"\| ocr: (\d+)", hlava).group(1))
        obrazove = [int(x) for x in re.search(r"\| obrazove: ([\d,]*)", hlava).group(1).split(",") if x]
        t = tokeny(text)
        if p.suffix.lower() in OBRAZKY and not ocr:
            polozka.update(typ="obrázek", tokeny=1600, slova=0, cache=None, poznamka="AI přečte obrázek přímo")
            uspora_puvodni += 1600
            uspora_cista += 1600
        else:
            poznamka = ""
            if typ == "obrázek":
                poznamka = "OCR – text z obrázku rozpoznán v macOS, originál otevřít jen u grafu nebo schématu"
            elif typ == "pdf" and bloku and len(text) / bloku < 80:
                poznamka = "SKEN – text chybí, číst obrazem jen vybrané strany"
            elif t > VELKE:
                poznamka = "VELKÉ – zeptej se uživatele: po kapitolách (pole kapitoly), jen shrnutí, nebo přeskočit"
            elif typ == "pdf" and ocr:
                poznamka = "SKEN (OCR) – text rozpoznán v macOS, originál otevřít jen u nejasných stran"
            casti = rel.split("/")
            if len(casti) >= 4 and casti[1] == "Úkoly":  # <Předmět>/Úkoly/<N Název>/soubor
                ukol = next((q for q in sorted((TREZOR / "/".join(casti[:3])).glob("*.md"))
                             if frontmatter(q).get("typ") in ("ukol", "zkouska")), None)
                polozka["ukol"] = nfc(str(ukol.relative_to(TREZOR))) if ukol else ""
                if not poznamka:
                    poznamka = ("ÚKOL – zadání → úplně do poznámky úkolu; podklad → učivo s vlastní poznámkou, "
                                "odkaz z poznámky úkolu; vlastní práce → jen do přehledu, --preskoc")
            # odhad, kolik by stálo čtení originálu (PDF/prezentace AI čte i jako obrázky)
            puvodni = 1600 if typ == "obrázek" else t + (bloku * 1500 if typ in ("pdf", "prezentace") else 0)
            uspora_puvodni += puvodni
            uspora_cista += t
            polozka.update(typ=typ, tokeny=t, slova=len(text.split("\n", 1)[-1].split()), bloky=bloku, cache=str(cil.relative_to(TREZOR)), poznamka=poznamka)
            if obrazove:
                polozka["obrazove"] = obrazove[:50]
            for stara in CACHE.glob(f"{h[:16]}-k*.md"):
                stara.unlink()
            if t > VELKE and typ != "obrázek":
                polozka["kapitoly"] = zapis_kapitoly(cil, text)
            neprecteno = neprectene(hlava, T)
            if neprecteno:
                polozka["neprecteno"] = neprecteno
            if slozka.is_dir():
                polozka["obrazky"] = sorted((nfc(str(x.relative_to(TREZOR))) for x in slozka.iterdir()),
                                            key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", x)])
        reg[rel] = {"otisk": h, "stav": "ceka", "datum": date.today().isoformat(), **podpis(p)}
        fronta.append(polozka)

    # záznamy smazaných souborů už nepotřebujeme
    for rel in [k for k in reg if k not in existujici]:
        del reg[rel]
    uloz_registr(reg)
    uklid_cache(reg)
    duplicity = najdi_duplicity(reg)
    (SYS / "duplicity.json").write_text(json.dumps(duplicity, ensure_ascii=False, indent=1))
    ignorovane = nacti_ignorovane()
    ukoly_predmetu = {}
    for p_u, rel_u in poznamky():
        fm_u = frontmatter(p_u)
        if fm_u.get("typ") in ("ukol", "zkouska"):
            ukoly_predmetu.setdefault(rel_u.split("/")[0], []).append((slova_nazvu(p_u.stem), fm_u.get("zdroj", "")))
    (SYS / "ukoly_navrhy.json").write_text(json.dumps({"nove": najdi_nove_ukoly(reg, ignorovane, ukoly_predmetu),
                                                       "hotove": najdi_hotove(ignorovane)}, ensure_ascii=False, indent=1))

    stavy = Counter(v["stav"] for v in reg.values())
    vyrizeno = stavy["hotovo"] + stavy["preskoceno"] + stavy["duplicita"]
    celkem = vyrizeno + len(fronta)
    T = texty()
    cislo = lambda n: f"{n:,}".replace(",", " ")
    # bez AI nemají tokeny smysl → místo nich rozsah materiálu
    try:
        bez_ai = json.loads(NASTAVENI.read_text()).get("ai") == "zadna"
    except Exception:
        bez_ai = False
    def rozsah(f):  # bez AI: kolik toho je, ne odhad času
        if f["typ"] == "prezentace":
            return T["rozsah_slidy"].format(n=f.get("bloky", 0))
        if f["typ"] == "pdf":
            return T["rozsah_strany"].format(n=f.get("bloky", 0))
        return T["rozsah_obrazek"] if f["typ"] == "obrázek" else T["rozsah_slova"].format(n=f.get("slova", 0))
    # /zpracuj vezme najednou DAVKA položek; k přečtení se přičte i psaní poznámek a pojmů (VYSTUP na položku)
    davek = -(-len(fronta) // DAVKA)
    # bez stropů roste poznámka s materiálem: odhad psaní ~ polovina čtení, nejméně VYSTUP (ověřit měřením /zpracuj)
    odhad_celkem = sum(f["tokeny"] + max(VYSTUP, f["tokeny"] // 2) for f in fronta)
    # poznámky ve fronta.json zůstávají česky (čte je AI), do Fronta.md jdou v jazyce uživatele
    pozn_preklad = {"ÚKOL": T["pozn_ukol"], "SKEN (OCR)": T["pozn_sken_ocr"], "SKEN": T["pozn_sken"], "VELKÉ": T["pozn_velke"],
                    "AI přečte": T["pozn_obrazek"], "OCR": T["pozn_ocr"]}
    preloz = lambda text: next((v for k, v in pozn_preklad.items() if text.startswith(k)), text)
    k_overeni = k_overeni_hotovych(reg, T)
    sloucene = sloucene_poznamky(reg)
    radky = [
        f"# {T['fronta_nadpis']}", "",
        f"## {T['souhrn']}",
        (T["ceka_rucne"].format(n=len(fronta)) if bez_ai
         else T["ceka"].format(n=len(fronta), t=cislo(sum(f["tokeny"] for f in fronta)))) if fronta else T["nic_neceka"],
        "",
        *([T["davky"].format(d=davek, t=cislo(odhad_celkem)), ""] if fronta and not bez_ai else []),
        *([T["rada_sezeni"], ""] if davek > 1 and not bez_ai else []),
        f'<progress value="{vyrizeno}" max="{max(celkem, 1)}"></progress> ' + T["zpracovano"].format(a=vyrizeno, b=celkem),
        "",
        *([T["k_overeni_souhrn"].format(n=len(k_overeni), h=T["k_overeni_nadpis"]), ""] if k_overeni else []),
        f"## {T['seznam']}",
        T["aktualizovano"].format(d=date.today().isoformat()), "",
    ]
    if fronta:
        radky += [T["tabulka_rucne"] if bez_ai else T["tabulka"], "|---|---|---|---:|---|"]
        for f in fronta:
            typ = T.get("typ_" + f["typ"], f["typ"])
            mnozstvi = rozsah(f) if bez_ai else cislo(f["tokeny"])
            pozn = "" if bez_ai and f["poznamka"].startswith(("VELKÉ", "AI přečte", "OCR", "SKEN (OCR)")) else preloz(f["poznamka"])
            if f.get("neprecteno"):
                pozn = (pozn + " " if pozn else "") + "⚠️ " + T["np_fronta"]
            radky.append(f"| {Path(f['soubor']).name.replace('|', '/')} | {f['predmet']} | {typ} | {mnozstvi} | {pozn} |")
    if duplicity:
        radky += ["", f"## {T['duplicity_nadpis']}", T["duplicity_rada"], ""]
        for d in duplicity:
            druh = T["duplicity_stejne"] if d["typ"] == "stejne" else T["duplicity_podobne"].format(s=d["shoda"])
            radky.append(f"- {ciste_jmeno(d['a'])} ↔ {ciste_jmeno(d['b'])} ({druh})")
    if k_overeni:
        radky += ["", f"## {T['k_overeni_nadpis']}", T["k_overeni_rada"], ""]
        for pozn, zdroj, mista in k_overeni:
            dalsich = T["k_overeni_dalsich"].format(n=len(mista) - 5) if len(mista) > 5 else ""
            radky.append(f"- [[{pozn}]] ({zdroj.replace('|', '/')}): " + "; ".join(m.replace("|", "/") for m in mista[:5]) + dalsich)
    if sloucene:
        radky += ["", f"## {T['sloucene_nadpis']}", T["sloucene_rada"], ""]
        for pozn, a, b, procent in sloucene:
            nazev = re.sub(r"[\[\]|\x00-\x1f]", " ", pozn)
            radky.append(f"- [[{nazev}]]: {ciste_jmeno(a)} ↔ {ciste_jmeno(b)} ({T['duplicity_podobne'].format(s=procent)})")
    FRONTA.write_text("\n".join(radky) + "\n")
    (SYS / "fronta.json").write_text(json.dumps(fronta, ensure_ascii=False, indent=1))

    print(T["ve_fronte"].format(n=len(fronta), h=stavy["hotovo"], p=stavy["preskoceno"], d=stavy["duplicita"]))
    if fronta:
        print(T["odhad"].format(a=cislo(uspora_cista), b=cislo(uspora_puvodni)))
        if not bez_ai:
            print(T["davky"].replace("**", "").replace("`", "").format(d=davek, t=cislo(odhad_celkem)))
        for f in fronta:
            print(f"  - [{f['typ']}] {f['soubor']} (~{f['tokeny']} tok.) {f['poznamka']}")

def ciste_jmeno_souboru(nazev):
    nazev = re.sub(r'[\\/:*?"<>|#^\[\]]', "-", re.sub(r"[\x00-\x1f\x7f]+", " ", nazev)).strip()
    return nazev.encode("utf8")[:200].decode("utf8", "ignore").strip().lstrip(".").strip()


def presun(soubor, predmet, nazev=None):
    """Zařadí materiál do <Předmět>/Učivo: z vkládací složky nebo z kořene předmětu, volitelně s novým názvem."""
    inbox = (TREZOR / INBOX).resolve()
    zdroj = (TREZOR / soubor).resolve()
    cilova = (TREZOR / predmet).resolve()
    if cilova.parent != TREZOR.resolve() or not (cilova / f"{cilova.name}.md").exists():
        sys.exit(f"Neznámý předmět: {predmet}")
    rozcestniky = {inbox / f"{INBOX[1:]}.md", cilova / f"{cilova.name}.md"}
    if zdroj.parent not in (inbox, cilova) or not zdroj.is_file() or zdroj in rozcestniky:
        sys.exit(f"Zařadit jde jen soubory přímo z {INBOX} nebo z kořene předmětu.")
    jmeno = zdroj.name
    if nazev is not None:
        cisty = ciste_jmeno_souboru(nazev[:-len(zdroj.suffix)] if zdroj.suffix and nazev.endswith(zdroj.suffix) else nazev)
        if not cisty:
            sys.exit("Název nesmí být prázdný.")
        jmeno = cisty + zdroj.suffix
    cil = cilova / "Učivo" / jmeno
    if cil.exists():
        sys.exit(f"V předmětu už soubor {jmeno} je – nepřepisuju ho.")
    cil.parent.mkdir(exist_ok=True)
    shutil.move(str(zdroj), str(cil))
    print(f"přesunuto: {nfc(str(cil.relative_to(TREZOR.resolve())))}")


def navrh(soubor):
    """Návrh předmětu a názvu podle textu v cache – jen návrh, rozhoduje uživatel nebo AI. Nic se nezapisuje."""
    import predmety
    p = (TREZOR / soubor).resolve()
    if not p.is_relative_to(TREZOR.resolve()) or not p.is_file():
        sys.exit(f"Soubor v trezoru neexistuje: {soubor!r}")
    zaznam = nacti_registr().get(nfc(str(p.relative_to(TREZOR.resolve()))), {})
    c = CACHE / f"{zaznam.get('otisk', '')[:16]}.md"
    text = c.read_text(errors="ignore").split("\n", 1)[-1] if zaznam and c.exists() else ""
    zacatek = nfc(text[:3000]).casefold()
    seznam = predmety.seznam()
    nalezeny = next((x for x in seznam if x["kod"] and x["kod"].casefold() in (zacatek + " " + nfc(p.stem).casefold())), None)
    nalezeny = nalezeny or next((x for x in seznam if x["nazev"].casefold() in zacatek), None)
    kod = nalezeny["kod"] if nalezeny else ""
    je_io = "interaktivní osnova" in zacatek[:500] or "učitel doporučuje studovat" in text.casefold()
    preskoc = re.compile(r"^(interaktivní osnova|anotace|menu|úvodní vymezení|\[text z|(mgr|bc|ing|phdr|doc|prof|dr)\.)", re.I)
    titul = ""
    for r in (x.strip() for x in text.splitlines()):
        if kod:  # „Zadání portfolia ISKB08“ → nadpis bez kódu; sám kód nadpis není
            r = re.sub(re.escape(kod), "", r, flags=re.I).strip(" –-:")
        r = re.split(r":\s|(?<=\w{4})\.\s", r.lstrip("#• "))[0].rstrip(" .:?!")  # jen první část víceřádkového nebo dlouhého nadpisu
        if (4 <= len(r) <= 70 and not r.startswith("===") and not preskoc.match(r) and re.search(r"[^\W\d_]{3}", r)
                and not (nalezeny and nfc(r).casefold() == nalezeny["nazev"].casefold())):
            titul = r
            break
    if not titul:  # bez textu aspoň uklizený název souboru
        titul = re.sub(r"^\d+[\s._-]*|\s*\(\d+\)$", "", re.sub(r"[_]+", " ", p.stem)).strip() or p.stem
    jmeno = ciste_jmeno_souboru(f"{'IO – ' if je_io else ''}{titul}{' – ' + kod if kod else ''}")
    print(json.dumps({"predmet": nalezeny["nazev"] if nalezeny else "", "nazev": jmeno, "io": je_io}, ensure_ascii=False))


def migruj_inbox():
    """Starší trezor: _Inbox → _Vkládání učiva. Bezpečné spouštět pořád: co už je hotové, nic nedělá."""
    stara, nova = TREZOR / "_Inbox", TREZOR / INBOX
    if nova.is_symlink() or stara.is_symlink():
        return
    if stara.is_dir():
        if not nova.exists():
            stara.rename(nova)
        else:  # rozšíření mezitím založilo novou složku: přesunout, nic nepřepsat
            for f in sorted(stara.iterdir()):
                cil = nova / ("Vkládání učiva.md" if f.name == "Inbox.md" else f.name)
                if f.name == ".DS_Store":
                    f.unlink()
                elif f.name == "Inbox.md" or not cil.exists():  # vlastní rozcestník má přednost před čerstvou šablonou
                    f.replace(cil)
            if not any(stara.iterdir()):
                stara.rmdir()
        if (nova / "Inbox.md").is_file():
            (nova / "Inbox.md").replace(nova / "Vkládání učiva.md")
    if REGISTR.exists():
        text = REGISTR.read_text(encoding="utf8")
        if '"_Inbox/' in text:
            try:
                reg = json.loads(text)
            except ValueError:
                reg = None
            if isinstance(reg, dict):
                prevod = lambda x: INBOX + x[len("_Inbox"):] if isinstance(x, str) and x.startswith("_Inbox/") else x
                for v in reg.values():
                    if isinstance(v, dict) and "stejne_jako" in v:
                        v["stejne_jako"] = prevod(v["stejne_jako"])
                uloz_registr({prevod(k): v for k, v in reg.items()})
    domov = TREZOR / "00 Domov.md"
    if domov.is_file() and not domov.is_symlink():
        text = domov.read_text(encoding="utf8", errors="surrogateescape")
        novy = text.replace("[[Inbox|", "[[Vkládání učiva|").replace("[[Inbox]]", "[[Vkládání učiva]]").replace("`_Inbox`", f"`{INBOX}`")
        if novy != text:
            domov.write_text(novy, encoding="utf8", errors="surrogateescape")
    if domov.is_file() and not domov.is_symlink():
        text = domov.read_text(encoding="utf8", errors="surrogateescape")
        novy = text.replace("> > ![[Studium.base#Nejbližší termíny]]", "> > ```druhy-mozek-ukoly\n> > ```")
        if novy != text:
            domov.write_text(novy, encoding="utf8", errors="surrogateescape")
    for d in TREZOR.iterdir():  # tabulka úkolů v přehledu předmětu → interaktivní
        prehled = d / f"{d.name}.md"
        if d.is_dir() and not d.name.startswith((".", "_")) and prehled.is_file() and not prehled.is_symlink():
            text = prehled.read_text(encoding="utf8", errors="surrogateescape")
            novy = text.replace("![[Studium.base#Úkoly předmětu]]", "```druhy-mozek-ukoly\npredmet\n```")
            if novy != text:
                prehled.write_text(novy, encoding="utf8", errors="surrogateescape")
    app = TREZOR / ".obsidian/app.json"
    if app.is_file() and not app.is_symlink():
        try:
            data = json.loads(app.read_text(encoding="utf8"))
        except ValueError:
            data = None
        if isinstance(data, dict) and data.get("newFileFolderPath") == "_Inbox":
            data["newFileFolderPath"] = INBOX
            app.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def nacti_ignorovane():
    try:
        return set(json.loads(UKOLY_IGNOROVAT.read_text()))
    except (OSError, ValueError, TypeError):
        return set()


def ignoruj(klic):
    """Návrh úkolu nebo „hotovo“, který uživatel odmítl, se už nenabízí."""
    if not re.fullmatch(r"[\w:./ –()-]{1,500}", klic):
        sys.exit("Neplatný klíč.")
    UKOLY_IGNOROVAT.write_text(json.dumps(sorted(nacti_ignorovane() | {klic}), ensure_ascii=False))


def slova_nazvu(text):
    return {w for w in re.findall(r"\w{3,}", nfc(text).casefold()) if w not in ("úkol", "ukol", "zadání", "zadani")}


def najdi_datum(radek):
    """První datum v řádku jako RRRR-MM-DD: 16. 12. 2026, 25. října 2026 i 11. října (bez roku = nejbližší další)."""
    try:
        d = DATUM.search(radek)
        if d:
            return date(int(d.group(3)), int(d.group(2)), int(d.group(1))).isoformat()
        d = DATUM_SLOVEM.search(radek)
        if d:
            mesic, den = MESICE[d.group(2).lower()], int(d.group(1))
            dnes = date.today()
            rok = int(d.group(3)) if d.group(3) else dnes.year + (1 if date(dnes.year, mesic, den) < dnes else 0)
            return date(rok, mesic, den).isoformat()
    except ValueError:
        pass
    return ""


def najdi_nove_ukoly(reg, ignorovane, ukoly_predmetu):
    """Zadání v textu materiálů (bez AI): jen návrhy, přidává je uživatel. Text z dokumentu jsou data, nic se z něj nespouští."""
    nove = []
    for rel, v in sorted(reg.items()):
        klic = "material:" + v["otisk"][:16]
        cast = rel.split("/")
        predmet = "" if cast[0] == INBOX else cast[0]
        if v["stav"] == "duplicita" or klic in ignorovane or (VLASTNI_PREFIX and cast[-1].startswith(VLASTNI_PREFIX)):
            continue
        if "Úkoly" in cast[1:-1] or "Organizace" in cast[1:-1]:  # už přiřazené k úkolu, nebo podmínky předmětu
            continue
        c = CACHE / f"{v['otisk'][:16]}.md"
        if not c.exists():
            continue
        radky = c.read_text(errors="ignore").split("\n")[1:]
        for i, radek in enumerate(radky):
            m = ZADANI.search(radek)
            if not m:
                continue
            nazev = re.sub(r"\s*\(.*$|^[\s:–-]+|[\s.:;,]+$", "", radek[m.end():]).strip()
            if m.group(0).casefold().startswith("zadání portfolia"):
                nazev = "Portfolio"
            if not 4 <= len(nazev) <= 80:
                nazev = re.sub(r"[_]+", " ", Path(cast[-1]).stem).strip()
            nazev = ciste_jmeno_souboru(nazev)
            termin = ""
            for r in radky[i:i + 3]:  # hned u zadání, nebo kdekoli na řádku o odevzdání
                termin = najdi_datum(r) if "doporučuje studovat" not in r and (ODEVZDANI.search(r) or r is radky[i]) else ""
                if termin:
                    break
            if not termin:
                termin = next((d for r in radky if ODEVZDANI.search(r) and "doporučuje studovat" not in r and (d := najdi_datum(r))), "")
            znama = ukoly_predmetu.get(predmet, [])
            sl = slova_nazvu(nazev)
            if any(cast[-1] in z or (sl and len(sl & u) / min(len(sl), len(u) or 1) >= 0.6) for u, z in znama):
                break  # takový úkol už existuje
            nove.append({"klic": klic, "soubor": rel, "predmet": predmet, "nazev": nazev, "termin": termin})
            break
    return nove


def pocet_slov_docx(p):
    try:
        with zipfile.ZipFile(p) as z:
            if z.getinfo("word/document.xml").file_size > MAX_CAST:
                return 0
            return len(re.sub(r"<[^>]+>", " ", z.read("word/document.xml").decode("utf8", "ignore")).split())
    except (OSError, KeyError, zipfile.BadZipFile):
        return 0


def najdi_hotove(ignorovane):
    """Otevřený úkol, ve složce kterého už leží hotová práce → nabídka „hotovo“. Rozhoduje vždy uživatel."""
    hotove = []
    for p, rel in poznamky():
        fm = frontmatter(p)
        klic = "hotovo:" + rel
        if fm.get("typ") != "ukol" or fm.get("stav") == "hotovo" or p.parent.parent.name != "Úkoly" or klic in ignorovane:
            continue
        for f in sorted(p.parent.rglob("*")):
            if not f.is_file() or f.is_symlink() or f.suffix == ".md" or f.name.startswith("."):
                continue
            jmeno = nfc(f.name).casefold()
            vlastni = VLASTNI_PREFIX and f.name.startswith(VLASTNI_PREFIX) and f.suffix == ".docx" and pocet_slov_docx(f) >= PRACE_SLOV
            if vlastni or f.suffix.lower() in (".mp4", ".mov", ".wav", ".mp3") or re.search(r"hotovo|vypracov|odevzdan", jmeno):
                hotove.append({"klic": klic, "ukol": rel, "soubor": nfc(str(f.relative_to(TREZOR)))})
                break
    return hotove


def pridej_ukol(soubor, predmet, nazev, termin=""):
    """Úkol z nalezeného zadání: vlastní složka v <Předmět>/Úkoly a poznámka s odkazem na materiál."""
    T = texty()
    zdroj = (TREZOR / soubor).resolve()
    cilova = (TREZOR / predmet).resolve()
    prehled = cilova / f"{cilova.name}.md"
    if cilova.parent != TREZOR.resolve() or not prehled.is_file():
        sys.exit(f"Neznámý předmět: {predmet}")
    if not zdroj.is_relative_to(TREZOR.resolve()) or not zdroj.is_file():
        sys.exit(f"Soubor v trezoru neexistuje: {soubor!r}")
    if termin:
        try:
            termin = date.fromisoformat(termin).isoformat()
        except ValueError:
            sys.exit(T["chyba_termin"])
    cisty = ciste_jmeno_souboru(nazev)[:150].strip()
    if not cisty:
        sys.exit(T["chyba_nazev"])
    ukoly = cilova / "Úkoly"
    cisla = [int(m.group(1)) for d in (ukoly.iterdir() if ukoly.is_dir() else []) if d.is_dir() and (m := re.match(r"(\d+) ", d.name))]
    cil = ukoly / f"{max(cisla, default=0) + 1} {cisty}" / f"{T['ukol_prefix']}{cisty}.md"
    cil.parent.mkdir(parents=True)
    rel_zdroj = nfc(str(zdroj.relative_to(TREZOR.resolve())))
    kod = frontmatter(prehled).get("kod", "")
    odkaz = json.dumps(f"[[{rel_zdroj}|{zdroj.name}]]", ensure_ascii=False)
    cil.write_text(f"---\ntyp: ukol\npredmet: \"[[{cilova.name}]]\"\nkod: {kod}\ntermin: {termin}\nstav: otevreno\nzdroj: {odkaz}\n"
                   f"tags:\n  - ukol\n---\n# {T['ukol_prefix']}{cisty}\n\n{T['zadani']}\n\n{T['postup']}\n- [ ] \n"
                   + (f"- [ ] {T['odevzdat']} [due:: {termin}]\n" if termin else f"- [ ] {T['odevzdat']}\n")
                   + f"\n{T['poznamky']}\n", encoding="utf8")
    print(nfc(str(cil.relative_to(TREZOR.resolve()))))


def frontmatter(p):
    text = p.read_text(errors="ignore")
    if not text.startswith("---"):
        return {}
    blok = text.split("---", 2)[1] if text.count("---") >= 2 else ""
    return {k.strip(): v.strip().strip('"') for k, v in re.findall(r"^([\w]+):[ \t]*(.*)$", blok, re.M)}


def poznamky():
    for p in sorted(TREZOR.rglob("*.md")):
        rel = p.relative_to(TREZOR)
        if nfc(rel.parts[0]) not in ("_Systém", "_Archiv", ".obsidian", ".claude", ".trash"):
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
    zaloha_registru()
    migruj_inbox()
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--hotovo":
        oznac(sys.argv[2], "hotovo", sys.argv[3] if len(sys.argv) == 4 else None)
    elif len(sys.argv) == 3 and sys.argv[1] == "--preskoc":
        oznac(sys.argv[2], "preskoceno")
    elif len(sys.argv) == 3 and sys.argv[1] == "--znovu":
        znovu(sys.argv[2])
    elif len(sys.argv) in (3, 4, 5, 6) and sys.argv[1] == "--kontrola":
        argumenty, kapitola = sys.argv[2:], None
        if "--kapitola" in argumenty[1:]:
            i = argumenty.index("--kapitola", 1)
            kapitola = argumenty[i + 1] if i + 1 < len(argumenty) else ""
            argumenty = argumenty[:i] + argumenty[i + 2:]
        if len(argumenty) > 2:
            sys.exit("Použití: priprav.py --kontrola CESTA [POZNÁMKA] [--kapitola N]")
        kontroluj(*soubor_v_trezoru(argumenty[0]), argumenty[1] if len(argumenty) == 2 else None, kapitola=kapitola)
    elif len(sys.argv) == 5 and sys.argv[1] == "--vynech":
        vynech(*sys.argv[2:])
    elif len(sys.argv) == 4 and sys.argv[1] == "--k-overeni":
        pridej_k_overeni(*sys.argv[2:])
    elif len(sys.argv) in (4, 5) and sys.argv[1] == "--presun":
        presun(*sys.argv[2:])
    elif len(sys.argv) in (5, 6) and sys.argv[1] == "--pridej-ukol":
        pridej_ukol(*sys.argv[2:])
    elif len(sys.argv) == 3 and sys.argv[1] == "--ignoruj":
        ignoruj(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "--navrh":
        navrh(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "--nechat":
        nechat_obe(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3 and sys.argv[1] == "--zmenene":
        if not (sys.argv[2].isascii() and sys.argv[2].isdigit()):
            sys.exit(f"Počet dní musí být celé číslo: {sys.argv[2]!r}")
        zmenene(int(sys.argv[2]))
    elif len(sys.argv) == 2 and sys.argv[1] == "--ukoly":
        ukoly()
    else:
        prehled()
