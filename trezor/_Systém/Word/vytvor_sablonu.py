#!/usr/bin/env python3
"""Vygeneruje Word šablonu KISK (Šablona KISK.dotx) podle vzoru MUNI ARTS – jen ze standardní knihovny.

  python3 _Systém/Word/vytvor_sablonu.py            # přegeneruje _Systém/Word/Šablona KISK.dotx
  python3 _Systém/Word/vytvor_sablonu.py vystup.docx --jazyk en   # šablona v jiném jazyce (cs, sk, en, uk)

Jméno a UČO bere z _Systém/nastaveni.json. Logo (volitelné) z _Systém/Word/logo-muni-arts.png –
v repozitáři není (ochranná známka MU); bez něj má záhlaví jen text.
"""
import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

SLOZKA = Path(__file__).resolve().parent
NASTAVENI = json.loads((SLOZKA.parent / "nastaveni.json").read_text())
ARGY = sys.argv[1:]
JAZYK_DOKUMENTU = None
if "--jazyk" in ARGY:
    i = ARGY.index("--jazyk")
    JAZYK_DOKUMENTU = ARGY[i + 1]
    del ARGY[i:i + 2]
OUT = ARGY[0] if ARGY else str(SLOZKA / "Šablona KISK.dotx")
LOGO = SLOZKA / "logo-muni-arts.png"
JMENO, UCO = NASTAVENI["jmeno"], NASTAVENI["uco"]
_TEXTY = json.loads((SLOZKA.parent / "texty.json").read_text(encoding="utf8"))
# jazyk dokumentů ve Wordu: --jazyk, jinak nastavení „jazyk_word“, jinak jazyk rozhraní
T = {**_TEXTY["cs"], **_TEXTY.get(JAZYK_DOKUMENTU or NASTAVENI.get("jazyk_word") or NASTAVENI.get("jazyk") or "cs", {})}
JAZYK = T["lang"]
STYL_STRED, STYL_UDAJ, STYL_ZDROJ = (escape(T[k], {'"': "&quot;"}) for k in ("styl_stred", "styl_udaj", "styl_zdroj"))
MODRA, SEDA, AZUR, NADPIS = "0000DC", "6B6B6B", "00AEEF", "3DA5E8"
WP = ' xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def run(text, b=False, sz=None, color=None, caps=False):
    rpr = ""
    if b: rpr += "<w:b/>"
    if caps: rpr += "<w:caps/>"
    if color: rpr += f'<w:color w:val="{color}"/>'
    if sz: rpr += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    rpr = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def p(content, style=None, align=None, after=None, before=None, border=False, keep=False, extra=""):
    ppr = ""
    if style: ppr += f'<w:pStyle w:val="{style}"/>'
    if keep: ppr += "<w:keepNext/>"
    if border: ppr += f'<w:pBdr><w:bottom w:val="single" w:sz="8" w:space="6" w:color="{MODRA}"/></w:pBdr>'
    if after is not None or before is not None:
        ppr += f'<w:spacing w:before="{before or 0}" w:after="{after or 0}"/>'
    if align: ppr += f'<w:jc w:val="{align}"/>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{extra}{content}</w:p>"



hlavicka = (
    p("", before=3600, after=0)
    + p(run(T["ph_nazev"]), style="Title")
    + p(run(T["ph_typ"]), style="Title")
    + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
)

telo = (
    p(run(T["h_uvod"]), style="Heading1",
      extra='<w:bookmarkStart w:id="0" w:name="TeloPrace"/><w:bookmarkEnd w:id="0"/>')
    + p(run(T["t_uvod"]))
    + p(run(T["h_hlavni"]), style="Heading1")
    + p(run(T["t_hlavni"]))
    + p(run(T["autor"], b=True) + "<w:r><w:tab/></w:r>" + run(T["ph_autor"]), style="Udaj")
    + p(run(T["rok"], b=True) + "<w:r><w:tab/></w:r>" + run(T["ph_rok"]), style="Udaj")
    + p(run(T["h_zaver"]), style="Heading1")
    + p(run(T["t_zaver"]))
    + p(run(T["h_zdroje"]), style="Heading1")
    + p(run(T["t_zdroj"]), style="Zdroj")
    + p(run(T["h_ai"]), style="Heading1")
    + p(run(T["t_ai"]))
)

sekce = ('<w:sectPr><w:headerReference w:type="default" r:id="rIdH"/><w:footerReference w:type="default" r:id="rIdF"/>'
         '<w:pgSz w:w="11906" w:h="16838"/>'
         '<w:pgMar w:top="2665" w:right="1418" w:bottom="1418" w:left="1418" w:header="709" w:footer="709" w:gutter="0"/>'
         '</w:sectPr>')
document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>{hlavicka}{telo}{sekce}</w:body></w:document>'

LOGO_CX, LOGO_CY = 1080000, 737263
logo = ('<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{LOGO_CX}" cy="{LOGO_CY}"/><wp:docPr id="32000" name="Logo MUNI ARTS"/>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
        '<pic:nvPicPr><pic:cNvPr id="32000" name="logo-muni-arts.png"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="rIdLogo"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{LOGO_CX}" cy="{LOGO_CY}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
        '</wp:inline></w:drawing></w:r>') if LOGO.exists() else ''
radek = lambda obsah: p(obsah, style="Header")
bunka = lambda w, obsah, valign, odsazeni=0: (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:tcMar><w:left w:w="{odsazeni}" w:type="dxa"/></w:tcMar><w:vAlign w:val="{valign}"/></w:tcPr>{obsah}</w:tc>')
zahlavi = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {W}{WP}>'
           '<w:tbl><w:tblPr><w:tblW w:w="9070" w:type="dxa"/>'
           '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
           '<w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders><w:tblLayout w:type="fixed"/>'
           '<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPr>'
           '<w:tblGrid><w:gridCol w:w="2100"/><w:gridCol w:w="6970"/></w:tblGrid><w:tr>'
           + bunka(2100, radek(logo), "top")
           + bunka(6970, radek(run(T["ph_predmet"]))
                         + radek(run(f"{JMENO} | {T['uco']}: {UCO}"))
                         + radek(run(T["ph_nazev"], b=True)), "center", 300)
           + '</w:tr></w:tbl><w:p><w:pPr><w:pStyle w:val="Header"/></w:pPr></w:p></w:hdr>')
zapati = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {W}>'
          '<w:p><w:pPr><w:pStyle w:val="Footer"/><w:jc w:val="right"/></w:pPr>'
          '<w:r><w:t>-</w:t></w:r><w:fldSimple w:instr=" PAGE "><w:r><w:t>1</w:t></w:r></w:fldSimple><w:r><w:t>-</w:t></w:r></w:p>'
          "</w:ftr>")

styly = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {W}>
<w:docDefaults>
 <w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" w:cs="Calibri"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="{JAZYK}"/></w:rPr></w:rPrDefault>
 <w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
 <w:pPr><w:spacing w:before="0" w:after="480" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr><w:rPr><w:b/><w:color w:val="{AZUR}"/><w:spacing w:val="30"/><w:sz w:val="40"/><w:szCs w:val="40"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
 <w:pPr><w:keepNext/><w:spacing w:before="360" w:after="240" w:line="240" w:lineRule="auto"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="{NADPIS}"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
 <w:pPr><w:keepNext/><w:spacing w:before="240" w:after="80" w:line="240" w:lineRule="auto"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="NadpisStred"><w:name w:val="{STYL_STRED}"/><w:basedOn w:val="Heading1"/><w:next w:val="Normal"/><w:qFormat/>
 <w:pPr><w:jc w:val="center"/></w:pPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="Udaj"><w:name w:val="{STYL_UDAJ}"/><w:basedOn w:val="Normal"/><w:qFormat/>
 <w:pPr><w:tabs><w:tab w:val="left" w:pos="2835"/></w:tabs><w:spacing w:after="60"/></w:pPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="Zdroj"><w:name w:val="{STYL_ZDROJ}"/><w:basedOn w:val="Normal"/><w:qFormat/>
 <w:pPr><w:spacing w:after="360"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="caption"/><w:basedOn w:val="Normal"/><w:qFormat/>
 <w:pPr><w:spacing w:after="240"/></w:pPr><w:rPr><w:sz w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Header"><w:name w:val="header"/><w:basedOn w:val="Normal"/>
 <w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Footer"><w:name w:val="footer"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:style>
<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:tblPr><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
</w:styles>'''

typ = "template" if OUT.endswith(".dotx") else "document"
content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.{typ}.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>'''
rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>'''
doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rIdSet" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
<Relationship Id="rIdH" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
<Relationship Id="rIdF" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>'''
settings = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {W}><w:defaultTabStop w:val="708"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat><w:themeFontLang w:val="{JAZYK}"/></w:settings>'
core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>{escape(T["sablona_titul"])}</dc:title><dc:creator>{JMENO}</dc:creator><cp:lastModifiedBy>{JMENO}</cp:lastModifiedBy>
</cp:coreProperties>'''

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", content_types)
    z.writestr("_rels/.rels", rels)
    z.writestr("word/document.xml", document)
    z.writestr("word/_rels/document.xml.rels", doc_rels)
    z.writestr("word/styles.xml", styly)
    z.writestr("word/settings.xml", settings)
    z.writestr("word/header1.xml", zahlavi)
    if LOGO.exists():
        z.writestr("word/_rels/header1.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rIdLogo" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo-muni-arts.png"/>'
                   '</Relationships>')
        z.write(LOGO, "word/media/logo-muni-arts.png")
    z.writestr("word/footer1.xml", zapati)
    z.writestr("docProps/core.xml", core)
print("OK", OUT)
