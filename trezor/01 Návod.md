# 📖 Návod k druhému mozku

> [!tip] Nejkratší verze
> 1. Nový materiál ze školy ulož do složky předmětu (nebo do `_Inbox`).
> 2. Na [[00 Domov|🏠 Domově]] klikni **📥 Zpracovat nové materiály (AI)**.
> 3. Úkol do Wordu zakládej tlačítkem **📝 Nový úkol ve Wordu**.
> 4. Po odevzdání otevři poznámku úkolu a klikni **✅ Označit úkol jako odevzdaný**.
> 5. Co dělat dnes a co tento týden, ti řekne **🧭 Plán úkolů** (plugin Neuro Roadmap od Mattea Rossiho).

> [!note] Jazyk
> Rozhraní, Domov, tenhle návod a šablony se řídí jazykem v **Nastavení → Druhý mozek → Jazyk** (čeština, slovenština, angličtina, ukrajinština).
> Dokumenty ve Wordu mají vlastní jazyk (**Jazyk dokumentů ve Wordu**) – můžeš mít třeba rozhraní česky a práce anglicky.
> Názvy složek a systémových souborů (`_Systém`, `Poznámky`, `Úkoly`, `00 Domov`…) zůstávají ve všech jazycích česky, aby se nerozbily odkazy.

---

## 1. Co je co

| Část | K čemu je |
|---|---|
| **Obsidian – trezor** | všechny materiály, poznámky a úkoly na jednom místě (např. v OneDrive kvůli záloze) |
| **🏠 Domov** | přehled: tlačítka, termíny, fronta, předměty, poslední poznámky |
| **Rozšíření „Druhý mozek“** | tlačítka a příkazy (AI, Word, fronta, odevzdání, kontrola, záloha, jazyk) |
| **Neuro Roadmap** | plánování úkolů: přehled po předmětech, Gantt, Horizon, kalendář – od **Mattea Rossiho** |
| **Šablona KISK pro Word** | úkoly s logem MUNI ARTS, předmětem, jménem a UČO |
| **AI (Claude Code nebo jiná)** | dělá z materiálů poznámky, pojmy, myšlenkové mapy a kartičky – spouští se tlačítky |

Obě rozšíření čtou **stejné poznámky** – co založíš u nás, vidí i Neuro Roadmap, a naopak.

---

## 2. Mapa trezoru

| Složka / soubor | Co v ní je |
|---|---|
| `00 Domov` | hlavní přehled – začínej vždycky tady |
| `01 Návod` | tenhle návod |
| `<Předmět>/` | originály od vyučujících – **nikdy se nemažou ani nepřepisují** |
| `<Předmět>/<Předmět>.md` | přehled předmětu: kód, vyučující, ukončení, termíny, seznam přednášek a úkolů |
| `<Předmět>/Poznámky/` | poznámky z přednášek (vytváří AI, ty dopisuješ *Moje postřehy*) |
| `<Předmět>/Úkoly/` | tvoje práce ve Wordu + poznámky úkolů (`Úkol – …`) |
| `_Inbox/` | nové věci, u kterých nevíš, kam patří – AI je roztřídí |
| `_Pojmy/` | 1 pojem = 1 krátká poznámka, propojuje předměty (podívej se do grafu: Cmd+G) |
| `_Zdroje/` | obecné návody (jak psát esej, citovat…) |
| `_Přehledy/` | týdenní přehledy |
| `_Systém/` | technika – šablony, skripty, fronta, kontrola, jazykové balíčky. **Ručně needituj.** |

---

## 3. Tlačítka a příkazy

Najdeš je **nahoře na Domově**, pod **ikonou 🧠 v levém svislém panelu** a v paletě příkazů (**Cmd+P** → napiš „Druhý mozek“).

| Tlačítko | Co udělá | AI? | Kdy použít |
|---|---|---|---|
| 📥 **Zpracovat nové materiály** | z nových materiálů udělá poznámky, pojmy, mapy, kartičky; roztřídí `_Inbox` | ✅ | když přibydou přednášky (třeba 1× týdně) |
| 🔎 **Co čeká na zpracování** | ukáže frontu a kolik to bude stát tokenů | ❌ zdarma | kdykoli |
| ✔️ **Označit materiál jako zpracovaný** | ruční odškrtnutí materiálu ve frontě | ❌ | když zpracováváš bez AI |
| 📝 **Nový úkol ve Wordu** | formulář → dokument ze šablony KISK (v jazyce Wordu) + poznámka úkolu + termín | ❌ | když začínáš psát úkol |
| 📄 **Převést hotovou práci do šablony KISK** | vloží tvůj hotový .docx do šablony (originál zůstane) | ❌ | když už máš úkol napsaný jinde |
| ✅ **Označit úkol jako odevzdaný** | nastaví `stav: hotovo` a zaškrtne „Odevzdat“ | ❌ | po odevzdání do ISu (měj otevřenou poznámku úkolu) |
| 🧭 **Plán úkolů (Neuro Roadmap)** | otevře Matteův plánovač | ❌ | plánování týdne |
| 🗓 **Týdenní přehled** | souhrn týdne, termíny, otázky na zopakování | ✅ / ❌ | v neděli |
| 🎓 **Příprava na zkoušku** | souhrn předmětu, 15 otázek, kartičky, myšlenková mapa na plátně | ✅ / ❌ | před zkouškou |
| 💾 **Zálohovat teď** | okamžitá záloha (jinak se zálohuje samo) | ❌ | před velkou změnou |
| 📚 **Přidat předmět** | založí složku a přehled předmětu (kód + název); odebrání v ⚙️ Nastavení → Předměty | ❌ | nový semestr |
| 🔄 **Zkontrolovat novou verzi** | zeptá se GitHubu, jestli nevyšla nová verze druhého mozku | ❌ | kdykoli (jinak se ptá samo 1× denně) |
| 📝 **Nová poznámka k materiálu** | vybereš materiál z fronty → poznámka ze šablony s vyplněným předmětem, kódem a zdrojem; materiál se otevře vedle a ve frontě se odškrtne | ❌ | ruční zpracování |
| 🃏 **Opakovat kartičky** | kartičky `Otázka::Odpověď` ze všech poznámek; co umíš, se vrátí za 1, 2, 4, 8… dní | ❌ | denně pár minut |
| 📅 **Termíny do kalendáře** | vytvoří `_Systém/Termíny.ics` a otevře import do Kalendáře (odtud i do Googlu a telefonu) | ❌ | po přidání úkolů |
| 📚 **Citace zdroje (ČSN ISO 690)** | formulář → hotová citace ve schránce + poznámka v `_Zdroje` | ❌ | při psaní prací |
| ⏰ **Blížící se termíny** | úkoly a zkoušky do 3 dnů a po termínu (jinak se ukáže samo 1× denně) | ❌ | kdykoli |
| ⚙️ **Nastavení** | AI, záloha, jazyky, jméno a UČO | ❌ | kdykoli |
| 🩺 **Zkontrolovat propojení** | kontrola celého systému (viz kapitola 9) | ❌ | když něco nefunguje |
| 🛡 **Potvrdit změny kódu** | potvrdí, že změny skriptů/pravidel byly tvoje | ❌ | jen když to kontrola žádá a víš, odkud změna je |
| 🔧 **Nechat AI opravit propojení s Neuro Roadmap** | AI opraví spolupráci po aktualizaci Neuro Roadmap | ✅ | když kontrola hlásí ⚠️/❌ u Neuro Roadmap |

**Tlačítka s AI** otevřou Terminál s Claudem (levnější model Sonnet), nebo s AI, kterou máš nastavenou. Při prvním použití macOS zobrazí dotaz, jestli Obsidian smí ovládat Terminál → **Povolit**. Claude se tě zeptá, než sáhne na nastavení, skripty nebo web – čti, co chce udělat, a potvrď jen to, čemu rozumíš.

---

## 4. Práce s AI – s Claudem, s jinou AI, nebo ručně

Vybereš si při instalaci a **kdykoli AI přidáš, změníš nebo odebereš**: **Nastavení → Druhý mozek** (nebo **⚙️ Nastavení**). Uložení provede jen kliknutí – AI ho změnit nemůže.

| Režim | Pro koho | Výhody | Na co myslet |
|---|---|---|---|
| **Claude Code** (doporučeno) | máš předplatné Claude | nejlepší výsledky, čte PDF i obrázky, šetření tokenů, **platí bezpečnostní pravidla systému** | potřeba [Claude Code](https://claude.com/claude-code); limity předplatného |
| **Jiná AI v Terminálu** | máš jinou AI s nástrojem pro Terminál – [Gemini CLI](https://github.com/google-gemini/gemini-cli), [Codex CLI](https://github.com/openai/codex) nebo vlastní program | využiješ předplatné, které už máš; dostane stejné instrukce jako Claude | **bezpečnostní pravidla systému na ni neplatí** – nech v ní zapnuté potvrzování příkazů, nikdy nepoužívej režim bez potvrzování (`--yolo` apod.); kvalita se liší |
| **Bez AI – ručně** | chceš se učit psaním, nemáš AI, nebo nechceš nic posílat ven | zdarma, maximální soukromí, nejvíc si zapamatuješ | víc práce; tlačítka s AI se skryjí |

**Co funguje vždy, i bez AI:** Domov, fronta materiálů, termíny s odpočtem, úkoly a převod do šablony Wordu, odevzdání, Neuro Roadmap, kontrola, hlídání kódu a záloha.

### Tipy
- **Ruční režim:** poznámku založ přes **Cmd+P → Šablony: Vložit šablonu → Přednáška**. Myšlenkovou mapu nakresli v *Canvasu* (Cmd+P → *Nové plátno*) nebo napiš jako `mindmap` v Mermaidu (vzor je v šabloně). Kartičky piš jako `Otázka::Odpověď`. Zpracovaný materiál odškrtni tlačítkem **✔️ Označit materiál jako zpracovaný**.
- **Nejlepší kombinace:** AI udělá kostru (shrnutí, pojmy, mapu), ty dopíšeš *Moje postřehy* – AI šetří čas, psaní tě učí.
- **Lokální AI (soukromí, offline):** když máš model v počítači (např. přes Ollama nebo llama.cpp) a nástroj pro Terminál, který s ním umí pracovat, zadej ho jako *Vlastní příkaz*. Na dlouhá PDF bývají lokální modely slabší.
- **Webové AI (ChatGPT, Gemini, NotebookLM):** napojit nejdou, ale můžeš jim ručně vložit text materiálu – vytažený text najdeš v `_Systém/cache`. Výsledek si vlož do poznámky ze šablony.
- **Soukromí:** s AI se obsah zpracovávaných materiálů posílá jejímu poskytovateli. Bez AI se nic nikam neposílá.
- **Vlastní příkaz jiné AI:** musí obsahovat značku `{prompt}` (např. `gemini -i {prompt}`) a jen písmena, čísla, mezery a `. _ / = : -`, aby do něj nešlo nic propašovat.
- **Jazyk poznámek od AI:** AI píše poznámky v jazyce rozhraní.

### ✍️ Bez AI – co máš navíc
- **📝 Nová poznámka k materiálu** – poznámka ze šablony, která se sama zařadí k předmětu (Domov ji ukáže); materiál se otevře vedle, takže čteš a píšeš zároveň.
- **🗓 Týdenní přehled** – termíny na 14 dní, co je po termínu, nové materiály a co jsi za týden napsal. Tvoje poznámky pod vygenerovaným blokem zůstávají.
- **🎓 Příprava na zkoušku** – shrnutí, klíčové pojmy a všechny kartičky předmětu v jedné poznámce „Zkouška – předmět“.
- **🃏 Opakovat kartičky** – bez dalšího pluginu; co umíš, se vrací v delších intervalech.
- **⏰ Připomínky** – 1× denně upozornění na termíny do 3 dnů a po termínu (**⚙️ Nastavení → Připomínky termínů**).
- **📅 Termíny do kalendáře** a **📚 Citace podle ČSN ISO 690**.
- **🔍 Hledání v materiálech** – text z PDF a prezentací je v `_Systém/cache`, takže **Cmd+Shift+F** najde slovo i uvnitř přednášek.
- **Fronta** ukazuje místo tokenů odhad času čtení.
- **🗄 Konec semestru** – **⚙️ Nastavení → Předměty → 🗄 Archivovat**: předmět se přesune do `_Archiv` (nic se nemaže) a zmizí z Domova, výběrů, plánu i fronty. Vrátit ho jde tamtéž.

---

## 5. Automatická záloha

Rozšíření zálohuje trezor samo – nemusíš na nic myslet.

- **Co:** poznámky, pojmy, úkoly, Domov, systém, nastavení a **tvoje vlastní práce** (soubory začínající tvým UČO). Materiály od vyučujících (PDF, prezentace…) jen když to zapneš – když je trezor v OneDrive/Google Drive/iCloudu, už tam jsou.
- **Kdy:** 10 minut po poslední změně, hned po potvrzení změn kódu nebo nastavení a aspoň jednou denně (když je Obsidian spuštěný). Ručně kdykoli tlačítkem **💾 Zálohovat teď**.
- **Kam:** **Nastavení → Druhý mozek → Automatická záloha → Kam zálohovat** – OneDrive, Google Drive, Dropbox, iCloud Drive, Dokumenty, externí disk nebo vlastní složka. Výchozí je první nalezený cloud.
- **Změna místa:** zeptá se, co se starými zálohami – *ponechat*, nebo *smazat staré po úspěšné záloze do nové* (nejdřív vznikne nová záloha, staré se smažou jen když se povede).
- **Počet záloh:** 1 (jen nejnovější) až 30. Nejstarší se maže vždy až **po** úspěšném vytvoření nové – a jen vlastní složky záloh pojmenované datem.
- **Obnova:** ve složce záloh je soubor *OBNOVA – přečti mě* – zkopíruješ obsah nejnovější zálohy zpět do trezoru.
- **Hlídání:** 🩺 kontrola upozorní, když záloha selže, je vypnutá nebo je starší než 3 dny.

---

## 6. Typické situace krok za krokem

### 📚 Nový semestr – přidat nebo odebrat předmět
1. **📚 Přidat předmět** (ikona 🧠 v levém panelu, **Cmd+P**, nebo **⚙️ Nastavení → Předměty**) → vyplň kód (např. `ISKB02`) a název → **Přidat**.
2. Vznikne složka předmětu s podsložkami `Poznámky` a `Úkoly` a přehled předmětu. Předmět se hned objeví na Domově, ve výběru u úkolů ve Wordu, v plánu i v levém panelu (s kódem a oranžovým pruhem).
3. **Odebrání:** **⚙️ Nastavení → Předměty → 🗑 Odebrat** → potvrď. Celá složka předmětu jde **do koše v macOS** – dokud ho nevysypeš, můžeš ji vrátit.

### 🔄 Vyšla nová verze
1. Obsidian sám ukáže okno **🆕 Je dostupná nová verze** (kontroluje 1× denně; vypnout jde v **⚙️ Nastavení → Aktualizace**).
2. **📋 Co je nového** ukáže seznam změn. **Teď ne** – zeptá se znovu po dalším spuštění Obsidianu.
3. **⬇️ Stáhnout a nainstalovat** → rozšíření balík stáhne z GitHubu a ověří (kontrolní součty, verze). Do té doby se nic nemění; **Zrušit instalaci** vše zastaví.
4. **✅ Instalovat** → udělá se záloha, vymění se kód a rozšíření se znovu načte. Hotovo.

**Poznámky, materiály, předměty, nastavení a CSS předmětů zůstanou.** Systémové poznámky (Domov, Návod, šablony), do kterých jsi psal, se nepřepíšou – nová verze se uloží vedle s příponou „(nová verze)“. Když se instalace pokazí, změny se samy vrátí. **Pro případ nouze:** 7 dní je v **⚙️ Nastavení → Aktualizace** tlačítko **↩️ Vrátit poslední aktualizaci**; pak jde dočasná záloha (skrytá složka `.druhy-mozek-zaloha`) do koše.

### 📚 Přibyla přednáška / materiál
1. Stáhni ho z ISu do složky předmětu (nebo do `_Inbox`). Fronta se přepočítá sama.
2. Na Domově vidíš v kartě **📥 Čeká na zpracování**, kolik toho čeká.
3. Klikni **📥 Zpracovat nové materiály** → v Terminálu sleduj, co AI dělá (zpracuje max. 8 souborů a zeptá se, jestli pokračovat).
4. Výsledek: poznámka v `<Předmět>/Poznámky/`, nové pojmy v `_Pojmy`, doplněný přehled předmětu. Zadání úkolů se rovnou objeví v termínech.
5. Přečti si poznámku a **dopiš vlastní postřehy** – to je pro učení nejdůležitější.

### 📝 Začínám psát úkol
1. **📝 Nový úkol ve Wordu** → vyplň předmět, název, (typ práce) a termín → **Vytvořit**. Dokument je v jazyce z **⚙️ Nastavení → Jazyk dokumentů ve Wordu**.
2. Otevře se Word s hotovou hlavičkou (logo, předmět s kódem, jméno, UČO, název) a titulní stranou. Piš.
3. V Obsidianu vznikne poznámka `Úkol – název` s kontrolním seznamem. Termín se ukáže na Domově i v Neuro Roadmap.
4. Soubor se jmenuje `<UČO>-<Příjmení Jméno> KÓD Název.docx` (údaje z `_Systém/nastaveni.json`) – stejně, jak se odevzdává do ISu.

### 📄 Úkol už mám napsaný jinde
1. Ulož ho (.docx) do složky předmětu → **📄 Převést hotovou práci do šablony KISK** → vyber soubor → doplň název.
2. Vznikne nový dokument v šabloně; tvůj originál zůstane beze změny.
3. Přenese se text, obrázky, odkazy, číslování i poznámky pod čarou. Komentáře se vynechají. Dokument s **grafem nebo vloženým objektem** převod odmítne – ten vlož do šablony ručně.

### ✅ Odevzdal jsem
Otevři poznámku úkolu → **✅ Označit úkol jako odevzdaný**. Úkol zmizí z termínů na Domově a v Neuro Roadmap se zaškrtne.

### 🎓 Blíží se zkouška
**🎓 Příprava na zkoušku** → vyber předmět. Vznikne `Zkouška – <předmět>` (souhrn, mapa, otázky, kartičky) a plátno `Mapa – <předmět>`. Funguje jen z poznámek, takže předmět musí mít nejdřív zpracované materiály.

### ✍️ Chci si psát poznámky sám (bez AI)
Nová poznámka → **Cmd+P → Šablony: Vložit šablonu** → vyber *Přednáška*, *Úkol*, *Pojem* nebo *Zdroj*. Vyplň vlastnosti nahoře (hlavně `typ`, `predmet`, `kod`) – podle nich se poznámka objeví na Domově.

---

## 7. Neuro Roadmap (plugin od Mattea Rossiho)

Plánovač úkolů pro studium – ukazuje, **co, kdy a v jakém pořadí** dělat. Otevřeš ho tlačítkem **🧭 Plán úkolů** nebo ikonou **⌃** v levém panelu.

| Pohled | Co ukazuje |
|---|---|
| **Dashboard** | karta za každý předmět: kolik úkolů je hotovo, nejbližší termín, co je po termínu, malá časová osa |
| **Gantt** | úkoly na časové ose po předmětech; měřítka *Fit / Weeks / Months / Semester*; svislá čára = dnes. **Úkol přetáhneš myší na jiný den** – plugin sám přepíše termín v poznámce |
| **Horizon** | *Now*, *Next* (příštích 7 dní), *Later*, *Unscheduled* – nejlepší na otázku „co mám dělat teď“ |
| **Kalendář** | volitelný export do kalendáře (ICS) nebo Google Kalendáře – vyžaduje vlastní nastavení Google |

**Jak se do něj dostanou úkoly:** sám je najde v poznámkách. Každá poznámka úkolu má `kod` (předmět), `termin` a `stav`, poslední krok má termín v hranatých závorkách:
```
- [ ] Odevzdat do Odevzdávárny v ISu [due:: 2026-10-25]
```
Kroky bez data skončí v *Unscheduled* – když chceš, dopiš jim vlastní `[due:: RRRR-MM-DD]` nebo `[start:: …]`.

**Co v něm nastaví rozšíření Druhý mozek:** naučí ho rozumět vlastnostem systému (`kod`, `termin`, `stav`, `typ: ukol`, hodnoty *otevreno/rozpracovano/hotovo*) a vyloučí složku `_Systém`, aby šablony nebral jako úkoly. Jeho kód se **nemění** – aktualizace ti budou chodit normálně a naše rozšíření po každé zkontroluje, jestli spolupráce pořád funguje (kapitola 9).

Licence: PolyForm Noncommercial – pro osobní studium v pořádku. Zdroj: [GitHub phenex80/obsidian-neuro-roadmap](https://github.com/phenex80/obsidian-neuro-roadmap).

---

## 8. Jak vypadá poznámka a vlastnosti

**Poznámka z přednášky** (vytváří AI): shrnutí v 5 bodech → výpisky → klíčové pojmy jako odkazy → myšlenková mapa → kartičky `Otázka::Odpověď` → *Moje postřehy*.

> [!note] Myšlenkové mapy
> Při první mapě se Obsidian zeptá *„Zobrazit diagramy Mermaid v tomto trezoru?“* → **Povolit** (jednou pro celý trezor).

> [!note] Kartičky
> Kartičky jsou připravené pro plugin **Spaced Repetition** (opakování s rozestupy). Až budeš chtít opakovat, nainstaluj ho v *Nastavení → Pluginy třetích stran*.

**Vlastnosti (nahoře v poznámce)** – podle nich funguje Domov i Neuro Roadmap. Jejich názvy a hodnoty jsou ve všech jazycích stejné:

| Vlastnost | Příklad | Kde |
|---|---|---|
| `typ` | `prednaska`, `ukol`, `predmet`, `pojem`, `zdroj`, `zkouska` | všude |
| `predmet` | `"[[Psaní odborných textů]]"` | přednáška, úkol |
| `kod` | `ISKB04` | přednáška, úkol, předmět |
| `termin` | `2026-10-25` (vždy RRRR-MM-DD) | úkol |
| `stav` | `otevreno` / `rozpracovano` / `hotovo` | úkol |
| `zdroj` | `"[[original.pptx]]"` | z čeho poznámka vznikla |

Hodnotu s dvojtečkou dávej do uvozovek (`nazev: "DigCompEdu: Technologie…"`), jinak se vlastnosti rozbijí.

---

## 9. Kontrola, upozornění a bezpečnost

**Stavový řádek** vpravo dole ukazuje `🧠 ✅ Kontrola` – klik otevře podrobnou zprávu. Na Domově je nahoře barevný banner.

| Ikona | Význam | Co dělat |
|---|---|---|
| ✅ | vše funguje | nic |
| 🔧 | něco se po aktualizaci rozbilo, ale **opravilo se samo** | nic, jen pro informaci |
| ⚠️ / ❌ u Neuro Roadmap | po aktualizaci Matteova pluginu něco nefunguje | klikni **🔧 Nechat AI opravit** |
| ⚠️ **Integrita kódu** | změnil se skript, rozšíření nebo pravidla pro AI | upravoval jsi to ty (nebo AI na tvůj pokyn)? → **🛡 Potvrdit změny kódu** a opiš kód. Nevíš, odkud změna je? **Nepotvrzuj** – do potvrzení se skripty nespustí |

Kontrola běží **sama při spuštění Obsidianu a každých 6 hodin**, ručně přes **🩺 Zkontrolovat propojení**.

**Bezpečnostní pravidla, která platí:**
- AI smí bez ptaní jen vytvářet a upravovat poznámky a spouštět naše dva skripty. Na nastavení, skripty, pluginy a web se **musí zeptat**.
- Mazání, stahování, `sudo`, `ssh`, spouštění libovolného kódu a čtení klíčů (`~/.ssh`, Klíčenka, `.env`, klíče pluginů) má AI **zakázané úplně**.
- Text v materiálech jsou pro AI **data, ne pokyny**. Kdyby se nějaký dokument snažil AI něco nakázat, AI to neudělá a v souhrnu tě upozorní.
- Převod do šablony odmítne podezřelé dokumenty (obří po rozbalení, odkazy mimo dokument).

- Kontrola nové verze se jen **zeptá GitHubu na číslo poslední verze** – nic neodesílá, nic sama nestahuje ani neinstaluje. Aktualizace se stáhne až po tvém kliknutí, ověří se kontrolní součty a nainstaluje se až po kliknutí na **Instalovat**.
---

## 10. Když něco nefunguje

| Problém | Řešení |
|---|---|
| Tlačítko s AI nic neudělá | *Nastavení systému → Soukromí a zabezpečení → Automatizace* → u Obsidianu povol **Terminál** |
| Úkol se neukazuje v termínech | v poznámce úkolu zkontroluj `typ: ukol`, `kod`, `termin` (RRRR-MM-DD) a `stav: otevreno` |
| Myšlenková mapa se nezobrazí | povol diagramy Mermaid (kapitola 8) |
| Fronta se nehýbe | 🔎 *Co čeká na zpracování*; když hlásí 🛡, viz kapitola 9 |
| Word hlásí chybu dokumentu | převod originál nikdy nemění – vlož obsah do šablony ručně a nahlas chybu v Issues na GitHubu |
| Banner nebo stavový řádek svítí ⚠️/❌ | klikni na něj a postupuj podle zprávy (kapitola 9) |
| Chci AI přidat, změnit nebo odebrat | **⚙️ Nastavení** → Režim AI → Uložit |
| Chci jiný jazyk rozhraní nebo Wordu | **⚙️ Nastavení** → Jazyk / Jazyk dokumentů ve Wordu (před změnou jazyka se udělá záloha) |
| Chci zálohovat jinam / jen jednu zálohu | **⚙️ Nastavení** → Automatická záloha |
| Něco jsem smazal | Koš na Macu, koš v cloudu, nebo záloha (kapitola 5) |
| Chci přidat nebo odebrat předmět | **📚 Přidat předmět**; odebrání v **⚙️ Nastavení → Předměty → 🗑 Odebrat** (jde do koše) |
| Vyšla nová verze | okno **🆕 Je dostupná nová verze** → ⬇️ Stáhnout → `Instalovat.command` → *Aktualizovat existující trezor* |
| Něco nefunguje a nevím proč | **🐞 Nahlásit chybu nebo nápad** (🧠 / Cmd+P / ⚙️ Nastavení) – technické údaje bez osobních dat předvyplní samo, vše vidíš a odešleš sám e-mailem nebo na GitHubu |
| Terminál hlásí `Please run /login` nebo `OAuth access token has expired` | vypršelo přihlášení ke Claude: v tom okně Terminálu napiš `/login`, přihlas se v prohlížeči a pak zopakuj příkaz (např. `/zpracuj`) |

---

## 11. Co nedělat

- Neupravuj ručně nic v `_Systém/` – jméno, UČO, AI, zálohu a jazyky měň v **⚙️ Nastavení**.
- Neměň kód Matteova pluginu v `.obsidian/plugins/neuro-roadmap/`.
- Nepotvrzuj **🛡 změny kódu**, o kterých nevíš.
- Nevkládej do poznámek hesla ani osobní údaje spolužáků.
- Originály od vyučujících nepřejmenovávej zbytečně – AI je podle názvu sleduje (přejmenování nevadí, jen se soubor objeví ve frontě znovu).

---

## 12. Pro pokročilé – soubory systému

| Soubor | Účel |
|---|---|
| `.obsidian/plugins/druhy-mozek/` | rozšíření „Druhý mozek“ (tlačítka, kontrola, hlídání kódu, záloha, překlady) |
| `.obsidian/snippets/druhy-mozek.css` | vzhled Domova a barevné složky |
| `.obsidian/snippets/druhy-mozek-predmety.css` | barevný pruh a kód předmětů v levém panelu (generuje se sám; pod značkou konce můžeš psát vlastní CSS) |
| `_Systém/predmety.py` | založení předmětu a vzhled předmětů v levém panelu |
| `_Systém/prehledy.py` | bez AI: poznámka k materiálu, týdenní přehled, příprava na zkoušku, kalendář, citace |
| `_Archiv/` | ukončené předměty (nic se nemaže; nezobrazují se na Domově, ve výběrech, plánu ani frontě) |
| `_Systém/instalace.json` | co bylo nainstalováno – podle toho aktualizace pozná, co sis upravil |
| `.druhy-mozek-zaloha/` | skrytá záloha souborů nahrazených při aktualizaci |
| `_Systém/priprav.py` | fronta a spořič tokenů; `--presun`, `--zmenene N`, `--ukoly` |
| `_Systém/novy_ukol.py` | nový úkol a převod do šablony Word (`--jazyk` jednorázově změní jazyk Wordu) |
| `_Systém/Word/vytvor_sablonu.py` | vygeneruje `Šablona KISK.dotx` |
| `_Systém/nastaveni.json` | tvoje jméno, UČO, režim AI, jazyk rozhraní a Wordu (jediné místo s osobními údaji) |
| `_Systém/texty.json` | texty skriptů a šablony Wordu ve 4 jazycích |
| `_Systém/jazyky/` | jazykové balíčky systémových poznámek (cs, sk, en, uk) |
| `_Systém/Studium.base` | tabulky na Domově (termíny, předměty, poznámky) |
| `_Systém/Šablony/` | šablony poznámek pro ruční psaní |
| `.claude/CLAUDE.md` | pravidla pro AI |
| `.claude/commands/` | příkazy AI: `/zpracuj`, `/tyden`, `/zkouska`, `/oprav-roadmap` |
| `.claude/settings.json` | oprávnění AI |

---

## 13. První kroky po instalaci

- [ ] Ve Finderu nastav složku trezoru na **„Vždy ponechat na tomto zařízení“** (pokud je v OneDrive/iCloudu).
- [ ] Povol diagramy Mermaid při první myšlenkové mapě.
- [ ] Zkontroluj, že máš všechny předměty (**⚙️ Nastavení → Předměty**); chybějící přidej tlačítkem **📚 Přidat předmět**. Ukázkový předmět můžeš odebrat.
- [ ] (volitelně) Nainstaluj plugin **Neuro Roadmap** na plánování a **Spaced Repetition** na kartičky.
