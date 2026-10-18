# 🧠 Druhý mozek pro KISK

<details>
<summary>🌐 <b>Jazyk</b> · Čeština</summary>

[English](../README.md) · [Slovenčina](README.sk.md) · [Українська](README.uk.md)

</details>

Studijní systém pro [Obsidian](https://obsidian.md) postavený pro studium na **KISK FF MU** (dá se upravit pro jakýkoli obor).
Materiály ze školy na jednom místě, poznámky a myšlenkové mapy vytvořené AI, úkoly ve Wordu podle vzoru MUNI ARTS
a plánování termínů – vše ovládané tlačítky přímo v Obsidianu.

> Neoficiální studentský projekt, není produktem Masarykovy univerzity.

## Co umí

- **🏠 Domov** – přehled s tlačítky, nejbližšími termíny (s odpočtem dní), frontou nezpracovaných materiálů a předměty.
- **📥 Zpracování materiálů AI** – z PDF, prezentací, dokumentů a obrázků vytvoří poznámky (shrnutí, výpisky,
  myšlenková mapa v Mermaidu, kartičky `Otázka::Odpověď`) a propojené pojmy – přes [Claude Code](https://claude.com/claude-code), jinou AI, nebo vše ručně.
- **💸 Spořič tokenů** – text se z materiálů vytáhne lokálně (bez AI), duplicity a opakující se zápatí se zahodí,
  každý soubor se zpracuje jen jednou. Na reálných materiálech ~10× méně tokenů než čtení originálů.
- **📝 Úkoly ve Wordu** – nový úkol z formuláře v šabloně ve stylu MUNI ARTS (záhlaví s předmětem, jménem a UČO,
  titulní strana), nebo převod hotové práce do šablony (text, obrázky, odkazy, číslování, poznámky pod čarou).
- **💾 Automatická záloha** – po každé změně do OneDrive, Google Drive, Dropboxu, iCloudu, na externí disk
  nebo kamkoli; uchovává zvolený počet verzí, stará se maže až po úspěšné nové.
- **✅ Odevzdání jedním klikem** – úkol zmizí z termínů a zaškrtne se v plánu.
- **🎓 Příprava na zkoušku a 🗓 týdenní přehled** generované AI z tvých poznámek.
- **🧭 Spolupráce s [Neuro Roadmap](https://github.com/phenex80/obsidian-neuro-roadmap)** (plánovač od Mattea Rossiho –
  Gantt, Horizon, kalendář): rozšíření ho naučí české vlastnosti a po každé jeho aktualizaci zkontroluje, že spolupráce funguje.
- **📚 Tvoje předměty** – při instalaci zadáš, kolik jich máš, další přidáš nebo odebereš kdykoli v Obsidianu (odebrání po potvrzení přesune složku do koše v macOS). Řídí se jimi Domov, termíny, formulář úkolu ve Wordu, plán i levý panel.
- **✍️ Užitečný i bez AI** – nová poznámka k materiálu (předvyplněná ze šablony), týdenní přehled, příprava na zkoušku (shrnutí, pojmy a kartičky předmětu v jedné poznámce), opakování kartiček, připomínky termínů, termíny do kalendáře (.ics), citace podle ČSN ISO 690, archiv předmětů na konci semestru a odhad času čtení ve frontě – vše lokálně, nic se nikam neposílá.
- **🔄 Aktualizace jedním klikem** – Obsidian 1× denně zkontroluje, jestli nevyšla nová verze, a nabídne *Co je nového*, *Stáhnout a nainstalovat* a *Teď ne*. Rozšíření balík stáhne a ověří, ty jen klikneš na **Instalovat** (nebo **Zrušit instalaci**). Poznámky, materiály, předměty a nastavení zůstanou; předem se udělá záloha a aktualizaci jde vrátit.
- **🌐 Čtyři jazyky** – rozhraní, Domov, návod, šablony poznámek i instalátor česky, slovensky, anglicky a ukrajinsky;
  jazyk přepneš kdykoli v nastavení. Jazyk dokumentů ve Wordu se volí zvlášť (jednou dopředu) a AI píše poznámky v jazyce rozhraní.
- **🛡 Bezpečnost** – hlídání neoprávněných změn kódu, ochrana proti skrytým pokynům v materiálech (prompt injection),
  zip bombám a podvrženým dokumentům, přísná oprávnění AI.

Podrobný návod k používání: **[trezor/01 Návod.md](../trezor/01%20N%C3%A1vod.md)**.

## 🤖 S AI, s jinou AI, nebo úplně bez AI

Vybereš si při instalaci a kdykoli změníš v Obsidianu (*Nastavení → Second Brain for KISK*):

| Režim | Co potřebuješ | Poznámka |
|---|---|---|
| **Claude Code** (doporučeno) | [Claude Code](https://claude.com/claude-code) + předplatné Claude | nejlepší výsledky, platí bezpečnostní pravidla systému |
| **Jiná AI v Terminálu** | např. [Gemini CLI](https://github.com/google-gemini/gemini-cli) nebo [Codex CLI](https://github.com/openai/codex) | dostane stejné instrukce; bezpečnostní pravidla systému na ni neplatí – nech v ní zapnuté potvrzování |
| **Bez AI – ručně** | nic | zdarma, nic se neposílá ven; poznámky ze šablon, materiály odškrtáváš ručně |

Domov, fronta, termíny, úkoly ve Wordu, Neuro Roadmap i kontroly fungují ve všech režimech.
Tipy ke každému režimu (ruční práce, lokální modely, webové AI) jsou v [návodu](../trezor/01%20N%C3%A1vod.md).

## 🧩 Instalace přímo z Obsidianu

1. V Obsidianu: **Nastavení → Pluginy třetích stran → Procházet**, najdi **Second Brain for KISK**, klikni **Instalovat** a **Zapnout**.
2. Otevře se průvodce: jazyk, jazyk dokumentů ve Wordu, jméno, UČO, tvoje předměty a režim AI. Zkontroluje, že máš Python 3 (když ne, ukáže, kde ho stáhnout).
3. Klikni **🧠 Nastavit** – v trezoru vznikne Domov, Návod, šablony, předměty a skripty. Nic existujícího se nepřepíše.

Verzi z adresáře aktualizuje Obsidian (*Nastavení → Pluginy třetích stran → Zkontrolovat aktualizace*). Po aktualizaci rozšíření nabídne obnovení souborů v trezoru – předtím se zazálohují a poznámky, které sis upravil, zůstanou. Instalátor níže umí totéž a navíc aktualizace jedním klikem z GitHubu.

## ⚡ Instalace na pár kliknutí

1. **Stáhni:** zelené tlačítko **Code → Download ZIP** (nebo nejnovější vydání v *Releases*) a rozbal ho dvojklikem.
2. **Spusť instalátor:** ve složce dvakrát klikni na **`Instalovat.command`**.
   - macOS napoprvé ukáže varování, že soubor nejde ověřit (instalátor není podepsaný Applem – viz [SECURITY.md](SECURITY.cs.md)).
     Klikni **Hotovo**, otevři **Nastavení systému → Soukromí a zabezpečení**, sjeď dolů a u „Instalovat.command“ klikni
     **Přesto otevřít** → potvrď heslem/Touch ID.
   - Nechceš klikat v nastavení? Otevři Terminál, napiš `bash ` (s mezerou), přetáhni do okna soubor `Instalovat.command` a stiskni Enter.
3. **Odpověz na pár otázek v oknech:** jazyk, nový nebo existující trezor, kam ho uložit, jméno, UČO, tvoje předměty, jazyk dokumentů ve Wordu, AI, (volitelně) logo.
   - Chybí ti Python nebo Obsidian? Instalátor otevře stránku ke stažení a po instalaci klikneš **Hotovo – pokračovat**.
   - Když instalaci přerušíš, příště nabídne **Pokračovat od posledního kroku** – nic nevyplňuješ znovu.
4. **V Obsidianu:** *Otevřít složku jako trezor* → vyber nový trezor (cesta je ve schránce) →
   **Důvěřovat autorovi a povolit pluginy** → otevři **00 Domov** → **🩺 Zkontrolovat propojení**.

Hotovo. 🎉 Instalátor nic nestahuje, nic neodesílá, nepotřebuje heslo správce a nic existujícího nepřepíše.
Před instalací ověří kontrolní součty všech souborů. Co přesně dělá, je napsané na jeho začátku (otevři ho v TextEditu).

## 🔄 Aktualizace na novou verzi

1. Obsidian ukáže **🆕 Je dostupná nová verze druhého mozku** – **📋 Co je nového** otevře seznam změn ([CHANGELOG](../CHANGELOG.md)), **Teď ne** se zeptá znovu po dalším spuštění Obsidianu.
2. **⬇️ Stáhnout a nainstalovat** – rozšíření stáhne balík z Releases tohoto repozitáře a ověří ho: kontrolní součet ZIPu zveřejněný u vydání, kontrolní součty všech souborů (`SHA256SUMS.txt`) a číslo verze. Do té doby se v trezoru nic nemění a **Zrušit instalaci** vše zastaví.
3. **✅ Instalovat** – udělá se záloha trezoru, vymění se kód systému a rozšíření se znovu načte.

**Poznámky, materiály, předměty, nastavení a tvoje CSS předmětů zůstanou.** Systémové poznámky, které sis upravil (Domov, Návod, šablony, pravidla AI), se nepřepíšou – nová verze se uloží vedle s příponou „(nová verze)“. Když se instalace uprostřed pokazí, všechny změny se samy vrátí. Pro případ nouze je 7 dní k dispozici **↩️ Vrátit poslední aktualizaci** v *Nastavení → Second Brain for KISK → Aktualizace*; pak jde dočasná záloha z aktualizace (skrytá složka `.druhy-mozek-zaloha`) do koše. Klik na Instalovat potvrdí 🛡 jen u souborů shodných s ověřeným balíkem. Jde to i ručně: stáhni ZIP a spusť `Instalovat.command` → *Aktualizovat existující trezor*. Kontrolu jde vypnout v *Nastavení → Second Brain for KISK → Aktualizace*.

## 👥 Pro koho to je – a pro koho ne

- **Pro:** studenty a studentky KISK FF MU (nebo kohokoli, kdo si to upraví) na **macOS** s Obsidianem 1.9+ a Pythonem 3. Šablona Wordu, citace (ČSN ISO 690) a struktura předmětů vycházejí ze zvyklostí KISK.
- **Nepodporováno:** Windows, Linux, iPhone/iPad a Android – skripty, záloha a tlačítka AI potřebují macOS (v mobilu Obsidian poznámky jen zobrazí). Šablony jiných fakult a škol se neudržují; systém si můžeš upravit sám/sama.
- **S AI:** zpracovávané materiály se posílají poskytovateli AI, kterou sis vybral/a. Do trezoru se zapnutou AI nedávej citlivé dokumenty ani cizí soukromé materiály a nepřidávej do něj rozšíření, která spouštějí kód z poznámek (Dataview JS, Templater).
- **Tak, jak je, bez záruky:** nekomerční projekt jednoho studenta ([LICENSE](../LICENSE)). Každé vydání projde automatickými testy popsanými v [SECURITY.cs.md](SECURITY.cs.md), ale není to podporovaný produkt.
- **Chyby a pomoc:** přes [Issues](https://github.com/shadowsh1t/second-brain-kisk/issues) nebo **🐞 Nahlásit chybu nebo nápad** – odpovídám, jak to čas dovolí; bezpečnostní hlášení mají přednost (viz níže).
- **Tip:** nejdřív to vyzkoušej v testovacím trezoru se zapnutou zálohou a uprostřed zkouškového neaktualizuj v den vydání – nejdřív si přečti [CHANGELOG](../CHANGELOG.md).

## Požadavky

| Co | Odkaz | Poznámka |
|---|---|---|
| macOS | – | tlačítka s AI používají Terminál a AppleScript |
| Obsidian 1.9+ | [obsidian.md](https://obsidian.md/download) | potřebuje vestavěné *Bases* |
| Python 3 | [python.org](https://www.python.org/downloads/) nebo `brew install python` | jen standardní knihovna, nic dalšího se neinstaluje |
| *volitelně* AI | [Claude Code](https://claude.com/claude-code) (doporučeno), nebo jiná AI v Terminálu | jen pro tlačítka s AI; bez AI funguje vše ostatní |
| *volitelně* Poppler | `brew install poppler` | jen když má Claude Code prohlížet skenovaná PDF jako obrázky; text ve skenech a obrázcích rozpozná sám macOS (bez AI) |
| Microsoft Word | – | pro úkoly v šabloně |
| *volitelně* Neuro Roadmap | [GitHub](https://github.com/phenex80/obsidian-neuro-roadmap) | v Obsidianu: *Pluginy třetích stran → Procházet → Neuro Roadmap* |
| *volitelně* Spaced Repetition | v Obsidianu: *Pluginy třetích stran → Procházet* | opakování kartiček |

## Ruční instalace (bez instalátoru)

1. **Stáhni repozitář:** zelené tlačítko **Code → Download ZIP** a rozbal ho.
2. **Zkopíruj obsah složky `trezor/`** do svého trezoru Obsidianu (nebo složku rovnou otevři: *Obsidian → Otevřít složku jako trezor*).
   Složky `.obsidian` a `.claude` jsou skryté – ve Finderu je zobrazíš zkratkou **Cmd+Shift+.** (tečka).
3. **Osobní údaje:** v `_Systém/` přejmenuj `nastaveni.priklad.json` na `nastaveni.json` a vyplň jméno a UČO
   (`jazyk` a `jazyk_word`: `cs`, `sk`, `en` nebo `uk`). Pro jiný jazyk než češtinu pak v Obsidianu zvol jazyk v *Nastavení → Second Brain for KISK*
   – rozšíření přepíše systémové poznámky (Domov, Návod, šablony) do zvoleného jazyka.
4. **Logo (volitelné):** ulož logo své fakulty jako `_Systém/Word/logo-muni-arts.png` (PNG, průhledné pozadí).
   Logo MU v repozitáři není, protože je ochrannou známkou. Bez loga má záhlaví jen text.
5. **Vytvoř šablonu a frontu** – v Terminálu ve složce trezoru:
   ```bash
   python3 _Systém/Word/vytvor_sablonu.py
   python3 _Systém/priprav.py
   ```
6. **Zapni rozšíření:** *Obsidian → Nastavení → Pluginy třetích stran → Zapnout* a povol **Second Brain for KISK**.
   *Nastavení → Vzhled → CSS úryvky* → zapni **druhy-mozek**.
7. **Předměty:** v Obsidianu přidej každý svůj předmět tlačítkem **📚 Přidat předmět** (kód + název); ukázkový předmět odebereš v *Nastavení → Second Brain for KISK → Předměty*.
8. Otevři **🏠 00 Domov** a klikni na **🩺 Zkontrolovat propojení** – vše by mělo svítit ✅.
   Při prvním tlačítku s AI povol Obsidianu ovládání Terminálu (*Nastavení systému → Soukromí a zabezpečení → Automatizace*).

## Struktura

```
Instalovat.command              instalátor na pár kliknutí
SHA256SUMS.txt                  kontrolní součty všech souborů
README.md, SECURITY.md          popis a bezpečnost (anglicky)
docs/                           README a SECURITY česky, slovensky a ukrajinsky
tests/test_system.py            automatické testy (spouští je i GitHub)
nastroje/kontrolni_soucty.py    přepočet/ověření SHA256SUMS.txt
nastroje/aktualizace.py         aktualizace existujícího trezoru (volá ji instalátor)
CHANGELOG.md                    seznam změn v každé verzi
.github/workflows/              automatická kontrola a vydání na GitHubu
trezor/
├── 00 Domov.md                 přehled s tlačítky a kartami
├── 01 Návod.md                 návod k používání
├── Příklad předmětu/           vzor složky předmětu (Poznámky/, Úkoly/)
├── _Inbox/ _Pojmy/ _Přehledy/ _Zdroje/
├── _Systém/
│   ├── priprav.py              fronta a spořič tokenů (+ bezpečné --presun, --zmenene, --ukoly)
│   ├── novy_ukol.py            úkol ve Wordu / převod do šablony
│   ├── predmety.py             založení předmětu a vzhled předmětů v levém panelu
│   ├── Word/vytvor_sablonu.py  generátor Šablona KISK.dotx
│   ├── Studium.base            tabulky na Domově (Obsidian Bases)
│   ├── texty.json              texty skriptů a šablony Wordu ve 4 jazycích
│   ├── jazyky/                 jazykové balíčky systémových poznámek (cs, sk, en, uk)
│   ├── Šablony/                šablony poznámek
│   └── nastaveni.priklad.json  vzor osobního nastavení
├── .obsidian/
│   ├── plugins/druhy-mozek/    rozšíření (tlačítka, kontrola, hlídání kódu, preklady.json)
│   └── snippets/druhy-mozek.css
└── .claude/
    ├── CLAUDE.md               pravidla pro AI (vč. bezpečnosti)
    ├── commands/               /zpracuj, /tyden, /zkouska, /oprav-roadmap
    └── settings.json           přísná oprávnění AI
```

## Bezpečnost a soukromí

Jak si instalaci ověřit (kontrolní součty, automatické testy) a co instalátor nedělá: **[SECURITY.md](SECURITY.cs.md)**.

- **Nic se neodesílá jinam než do zvolené AI**, a to jen při tlačítkách s AI (v režimu bez AI vůbec nic). Rozšíření se jen 1× denně zeptá GitHubu na číslo poslední verze – jde to vypnout. Fronta, šablony a kontrola běží lokálně.
- AI smí bez ptaní jen upravovat poznámky a spouštět dva skripty systému. Mazání, stahování, `sudo`, `ssh` a čtení klíčů
  (`~/.ssh`, Klíčenka, `.env`, data pluginů) je zakázané; úpravy nastavení, skriptů a web vyžadují potvrzení.
- Obsah materiálů je pro AI **data, ne pokyny** – skryté instrukce v dokumentech AI neprovede a upozorní na ně.
- Rozšíření hlídá otisky skriptů a pravidel; při nepotvrzené změně je odmítne spustit a upozorní.
- `.gitignore` brání nahrání osobních údajů (`nastaveni.json`), studijních materiálů, vygenerovaných souborů a dat pluginů.

## Prohlášení

Vyžaduje je adresář rozšíření Obsidianu:
- **Síť:** verze z GitHubu se 1× denně zeptá `api.github.com` na číslo poslední verze a aktualizaci stáhne až po kliknutí na *Stáhnout a nainstalovat*. Verze z adresáře sama nic nestahuje (aktualizuje ji Obsidian). Tlačítka s AI spustí v Terminálu zvolený nástroj (např. Claude Code), který materiál posílá svému poskytovateli. Hlášení chyby jen otevře tvůj e-mail nebo GitHub s předvyplněným textem.
- **Soubory mimo trezor:** automatická záloha kopíruje trezor do složky, kterou zvolíš (OneDrive, Google Drive, iCloud…); aktualizace používá dočasnou složku; tlačítka s AI otevírají Terminál. Rozšíření spouští přibalené skripty v Pythonu 3, který máš nainstalovaný.
- **Žádná telemetrie, reklamy, účty ani platby.**

## 🐞 Našel jsi chybu nebo máš nápad?

- **Přímo v Obsidianu:** **🐞 Nahlásit chybu nebo nápad** (ikona 🧠, Cmd+P nebo *Nastavení → Second Brain for KISK*). Předvyplní technické údaje **bez osobních dat** (verze, jazyk, režim AI, výsledek kontroly, poslední chyby – žádné jméno, UČO, cesty ani obsah poznámek). Všechno vidíš a můžeš upravit; nic se neodešle samo. Odešleš e-mailem nebo na GitHubu.
- **Na GitHubu:** [Issues → New issue](https://github.com/shadowsh1t/second-brain-kisk/issues/new/choose) – formuláře pro chyby a nápady.
- **Bezpečnostní problémy soukromě:** [soukromé hlášení zranitelnosti](https://github.com/shadowsh1t/second-brain-kisk/security/advisories/new) nebo e-mail na `catty.skipping888@passinbox.com` s předmětem `[SECURITY]`.

## Poděkování

- **[Neuro Roadmap](https://github.com/phenex80/obsidian-neuro-roadmap)** – Matteo Rossi ([@phenex80](https://github.com/phenex80)). Plánovač úkolů, se kterým
  tenhle systém spolupracuje. Není součástí repozitáře, má vlastní licenci (PolyForm Noncommercial 1.0.0)
  a jeho rozhraní je jen anglicky (nemá podporu překladů, proto ho neupravujeme).
- Vzhled šablony Word vychází ze studentských prací ve stylu **MUNI ARTS**.
- Vytvořeno s pomocí [Claude Code](https://claude.com/claude-code).

## Licence

[PolyForm Noncommercial 1.0.0](../LICENSE) – zdarma pro osobní, studijní, výukové a jiné nekomerční použití včetně úprav a sdílení. Komerční použití jen se svolením autora.

© 2026 Jakub Josef Sova ([@shadowsh1t](https://github.com/shadowsh1t))
