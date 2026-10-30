#!/usr/bin/env python3
"""Spořič dat pro druhý mozek.

Lokálně (zdarma, bez AI) projde materiály v trezoru, z nových nebo změněných
souborů vytáhne čistý text do _Systém/cache a sestaví frontu k zpracování.
AI pak čte jen tenhle text, ne celé PDF nebo prezentace.

Použití:
  python3 _Systém/priprav.py                 # aktualizuje cache a frontu, vypíše souhrn
  python3 _Systém/priprav.py --hotovo CESTA  # označí soubor jako zpracovaný
  python3 _Systém/priprav.py --preskoc CESTA # označí soubor jako přeskočený (vlastní práce, osnova…)
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
VELKE = 30_000  # odhad tokenů, od kterého se soubor zpracuje jen jako shrnutí
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
CACHE_VERZE = 2  # při změně extrakce zvýšit – čekající položky se přegenerují, hotové ne
MALO_TEXTU = 80  # znaků: slajd/strana s menším množstvím textu je „hlavně obrázek“
OCR_ROZPOCET = 150  # s na jeden běh (Obsidian čeká na skript max. 5 min); zbytek se dočte příště
OCR_MAX_STRAN = 60  # stran jednoho PDF
OCR_MAX_OBRAZKU = 10  # obrázků z jedné prezentace
OCR_MIN_VELIKOST = 20_000  # menší obrázky (loga, ikony) se nečtou
OBRAZKY_OCR = {".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".bmp", ".heic", ".webp"}
ZACATEK = time.monotonic()

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
                    if cil in jmena and posixpath.splitext(cil)[1].lower() in OBRAZKY_OCR \
                            and OCR_MIN_VELIKOST <= z.getinfo(cil).file_size <= MAX_CAST:
                        kandidati.append((len(bloky), i, cil))
            hlava = f"=== slajd {i}: {nadpis} ===" if nadpis else f"=== slajd {i} ==="
            bloky.append(hlava + "\n" + "\n".join(radky))
        # obrázky slajdů „hlavně obrázek“ vybalit do cache (AI se na ně může podívat) a přečíst z nich text
        vybrane, videne = [], set()
        for b, i, cil in kandidati:
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
    return ["\n".join([r for r in radky if r] + grafy + odkazy(rel))]


def zbyva_ocr():
    return OCR_ROZPOCET - (time.monotonic() - ZACATEK)


def ocr_zapnuto():
    return sys.platform == "darwin" and nastaveni().get("ocr", True) is not False


def ocr_jazyky():
    return ",".join(OCR_JAZYKY.get(nastaveni().get("jazyk"), OCR_JAZYKY["cs"]))


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
    return v if isinstance(v, list) and len(v) == len(cesty) else [""] * len(cesty)


def z_pdf(cesta, info, slozka):
    zbyva = max(zbyva_ocr(), 0) if ocr_zapnuto() else 0
    strany = osascript(["pdf", str(int((time.time() + zbyva) * 1000) if zbyva >= 5 else 0), ocr_jazyky(),
                        str(cesta), str(OCR_MAX_STRAN)], 300 + zbyva) or []
    bloky = []
    for i, s in enumerate(strany, 1):
        text = (s.get("t") or "").strip()
        info["ocr"] += s.get("o") == 1
        info["odlozeno"] |= s.get("o") == 2 and ocr_zapnuto()
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
    koren, p = TREZOR.resolve(), (TREZOR / cesta).resolve()  # absolutní cesta TREZOR nahradí
    if not cesta.strip() or not p.is_relative_to(koren) or not p.is_file():  # složka, prázdná nebo cesta ven
        sys.exit(f"Soubor v trezoru neexistuje: {cesta!r}")
    rel = nfc(str(p.relative_to(koren)))
    reg[rel] = {"otisk": otisk(p), "stav": stav, "datum": date.today().isoformat(), **podpis(p)}
    uloz_registr(reg)
    print(f"{stav}: {rel}")


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
        c = CACHE / f"{v['otisk'][:16]}.md"
        if v["stav"] == "duplicita" or not c.exists():
            continue
        slova = re.findall(r"\w{2,}", c.read_text(errors="ignore").split("\n", 1)[-1].lower())[:PODOBNOST_SLOV]
        ctverice = {" ".join(slova[i:i + 4]) for i in range(max(0, len(slova) - 3))}
        if len(ctverice) >= PODOBNOST_MIN:
            texty_souboru[k] = (v["otisk"], ctverice)
    for a, b in itertools.combinations(sorted(texty_souboru), 2):
        (oa, ta), (ob, tb) = texty_souboru[a], texty_souboru[b]
        if oa == ob or frozenset((oa, ob)) in nechat:
            continue
        spolecne = len(ta & tb)
        jaccard, obsazeni = spolecne / len(ta | tb), spolecne / min(len(ta), len(tb))
        if jaccard >= 0.5 or obsazeni >= 0.8:
            vysledek.append({"typ": "podobne", "a": a, "b": b, "shoda": round(max(jaccard, obsazeni) * 100)})
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


def prehled():
    CACHE.mkdir(parents=True, exist_ok=True)
    reg = nacti_registr()
    existujici = {rel for _, rel in materialy()}
    # starší registr: „duplicita“ souboru, který už neexistuje (přesunutý originál) → soubor přebírá jeho roli
    zive = {v["otisk"]: k for k, v in reg.items() if k in existujici and v["stav"] in ("hotovo", "preskoceno")}
    for k, v in reg.items():
        if v["stav"] == "duplicita" and k in existujici and v.get("stejne_jako") not in existujici:
            if v["otisk"] in zive:
                v["stejne_jako"] = zive[v["otisk"]]
            else:
                v["stav"] = "hotovo"
                v.pop("stejne_jako", None)
                zive[v["otisk"]] = k
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
        if not verze or int(verze.group(1)) != CACHE_VERZE or "ocr_odlozeno" in hlava:
            shutil.rmtree(slozka, ignore_errors=True)
            info = {"ocr": 0, "odlozeno": False, "obrazove": [], "obrazky": []}
            try:
                bloky, typ = extrahuj(p, info, slozka)
            except Exception as e:  # poškozený nebo zamčený soubor
                bloky, typ = [], "chyba: " + re.sub(r"[\s|]+", " ", str(e))[:200]
            text, odstraneno = vycisti(bloky)
            zdroj = re.sub(r"[\x00-\x1f\x7f|]", " ", rel)  # nový řádek v názvu by rozbil hlavičku
            cil.write_text(f"<!-- zdroj: {zdroj} | typ: {typ} | bloků: {len(bloky)} | "
                           f"odstraněno opakujících se řádků: {odstraneno} | cache: {CACHE_VERZE} | ocr: {info['ocr']} | "
                           f"obrazove: {','.join(map(str, info['obrazove']))}"
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
                poznamka = "VELKÉ – zpracovat jen jako shrnutí"
            elif typ == "pdf" and ocr:
                poznamka = "SKEN (OCR) – text rozpoznán v macOS, originál otevřít jen u nejasných stran"
            # odhad, kolik by stálo čtení originálu (PDF/prezentace AI čte i jako obrázky)
            puvodni = 1600 if typ == "obrázek" else t + (bloku * 1500 if typ in ("pdf", "prezentace") else 0)
            uspora_puvodni += puvodni
            uspora_cista += t
            polozka.update(typ=typ, tokeny=t, slova=len(text.split("\n", 1)[-1].split()), bloky=bloku, cache=str(cil.relative_to(TREZOR)), poznamka=poznamka)
            if obrazove:
                polozka["obrazove"] = obrazove[:50]
            if slozka.is_dir():
                polozka["obrazky"] = sorted((nfc(str(x.relative_to(TREZOR))) for x in slozka.iterdir()),
                                            key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", x)])
        reg[rel] = {"otisk": h, "stav": "ceka", "datum": date.today().isoformat(), **podpis(p)}
        fronta.append(polozka)

    # záznamy smazaných souborů už nepotřebujeme
    for rel in [k for k in reg if k not in existujici]:
        del reg[rel]
    uloz_registr(reg)
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
    odhad_celkem = sum(f["tokeny"] for f in fronta) + len(fronta) * VYSTUP
    # poznámky ve fronta.json zůstávají česky (čte je AI), do Fronta.md jdou v jazyce uživatele
    pozn_preklad = {"SKEN (OCR)": T["pozn_sken_ocr"], "SKEN": T["pozn_sken"], "VELKÉ": T["pozn_velke"],
                    "AI přečte": T["pozn_obrazek"], "OCR": T["pozn_ocr"]}
    preloz = lambda text: next((v for k, v in pozn_preklad.items() if text.startswith(k)), text)
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
        f"## {T['seznam']}",
        T["aktualizovano"].format(d=date.today().isoformat()), "",
    ]
    if fronta:
        radky += [T["tabulka_rucne"] if bez_ai else T["tabulka"], "|---|---|---|---:|---|"]
        for f in fronta:
            typ = T.get("typ_" + f["typ"], f["typ"])
            mnozstvi = rozsah(f) if bez_ai else cislo(f["tokeny"])
            pozn = "" if bez_ai and f["poznamka"].startswith(("VELKÉ", "AI přečte", "OCR", "SKEN (OCR)")) else preloz(f["poznamka"])
            radky.append(f"| {Path(f['soubor']).name.replace('|', '/')} | {f['predmet']} | {typ} | {mnozstvi} | {pozn} |")
    if duplicity:
        radky += ["", f"## {T['duplicity_nadpis']}", T["duplicity_rada"], ""]
        for d in duplicity:
            druh = T["duplicity_stejne"] if d["typ"] == "stejne" else T["duplicity_podobne"].format(s=d["shoda"])
            radky.append(f"- {ciste_jmeno(d['a'])} ↔ {ciste_jmeno(d['b'])} ({druh})")
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
    migruj_inbox()
    if len(sys.argv) == 3 and sys.argv[1] in ("--hotovo", "--preskoc"):
        oznac(sys.argv[2], "hotovo" if sys.argv[1] == "--hotovo" else "preskoceno")
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
