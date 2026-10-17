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
NASTAVENI = SYS / "nastaveni.json"
VLASTNI_PREFIX = (json.loads(NASTAVENI.read_text())["uco"] + "-") if NASTAVENI.exists() else None
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
        return json.loads(NASTAVENI.read_text())
    except Exception:
        return {}


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
            cil.write_text(f"<!-- zdroj: {rel} | typ: {typ} | bloků: {len(bloky)} | "
                           f"odstraněno opakujících se řádků: {odstraneno} | cache: {CACHE_VERZE} | ocr: {info['ocr']} | "
                           f"obrazove: {','.join(map(str, info['obrazove']))}"
                           + (" | ocr_odlozeno: 1" if info["odlozeno"] else "") + f" -->\n\n{text}\n")
        text = cil.read_text()
        hlava = text.split("\n", 1)[0]
        typ = re.search(r"typ: ([^|]+)", hlava).group(1).strip()
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
            polozka.update(typ=typ, tokeny=t, slova=len(text.split()), cache=str(cil.relative_to(TREZOR)), poznamka=poznamka)
            if obrazove:
                polozka["obrazove"] = obrazove[:50]
            if slozka.is_dir():
                polozka["obrazky"] = sorted((nfc(str(x.relative_to(TREZOR))) for x in slozka.iterdir()),
                                            key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", x)])
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
        (T["ceka_rucne"].format(n=len(fronta), m=sum(minuty(f) for f in fronta)) if bez_ai
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
            mnozstvi = T["minuty"].format(n=minuty(f)) if bez_ai else cislo(f["tokeny"])
            pozn = "" if bez_ai and f["poznamka"].startswith(("VELKÉ", "AI přečte", "OCR", "SKEN (OCR)")) else preloz(f["poznamka"])
            radky.append(f"| {Path(f['soubor']).name.replace('|', '/')} | {f['predmet']} | {typ} | {mnozstvi} | {pozn} |")
    FRONTA.write_text("\n".join(radky) + "\n")
    (SYS / "fronta.json").write_text(json.dumps(fronta, ensure_ascii=False, indent=1))

    print(T["ve_fronte"].format(n=len(fronta), h=stavy["hotovo"], p=stavy["preskoceno"], d=stavy["duplicita"]))
    if fronta:
        print(T["odhad"].format(a=cislo(uspora_cista), b=cislo(uspora_puvodni)))
        if not bez_ai:
            print(T["davky"].replace("**", "").replace("`", "").format(d=davek, t=cislo(odhad_celkem)))
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
