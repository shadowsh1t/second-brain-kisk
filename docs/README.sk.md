# 🧠 Druhý mozog pre KISK

<details>
<summary>🌐 <b>Jazyk</b> · Slovenčina</summary>

[English](../README.md) · [Čeština](README.cs.md) · [Українська](README.uk.md)

</details>

Študijný systém pre [Obsidian](https://obsidian.md) postavený na štúdium na **KISK FF MU** (dá sa upraviť pre akýkoľvek odbor).
Materiály zo školy na jednom mieste, poznámky a myšlienkové mapy vytvorené AI, úlohy vo Worde podľa vzoru MUNI ARTS
a plánovanie termínov – všetko ovládané tlačidlami priamo v Obsidiane.

> Neoficiálny študentský projekt, nie je produktom Masarykovej univerzity.
> V Obsidiane sa rozšírenie volá **Druhý mozek**; názvy priečinkov zostávajú v každom jazyku české.

## Čo vie

- **🏠 Domov** (`00 Domov`) – prehľad s tlačidlami, najbližšími termínmi (s odpočtom dní), frontom nespracovaných materiálov a predmetmi.
- **📥 Spracovanie materiálov AI** – z PDF, prezentácií, dokumentov a obrázkov vytvorí poznámky (zhrnutie, výpisky,
  myšlienková mapa v Mermaide, kartičky `Otázka::Odpoveď`) a prepojené pojmy – cez [Claude Code](https://claude.com/claude-code), inú AI alebo všetko ručne.
- **💸 Šetrič tokenov** – text sa z materiálov vytiahne lokálne (bez AI), duplicity a opakujúce sa päty sa zahodia,
  každý súbor sa spracuje len raz. Na reálnych materiáloch ~10× menej tokenov ako čítanie originálov.
- **📝 Úlohy vo Worde** – nová úloha z formulára v šablóne v štýle MUNI ARTS (hlavička s predmetom, menom a UČO,
  titulná strana), alebo prevod hotovej práce do šablóny (text, obrázky, odkazy, číslovanie, poznámky pod čiarou).
- **💾 Automatická záloha** – po každej zmene do OneDrive, Google Drive, Dropboxu, iCloudu, na externý disk
  alebo kamkoľvek; uchováva zvolený počet verzií, staré maže až po úspešnej novej.
- **✅ Odovzdanie jedným klikom** – úloha zmizne z termínov a zaškrtne sa v pláne.
- **🎓 Príprava na skúšku a 🗓 týždenný prehľad** generované AI z tvojich poznámok.
- **🧭 Spolupráca s [Neuro Roadmap](https://github.com/phenex80/obsidian-neuro-roadmap)** (plánovač od Mattea Rossiho –
  Gantt, Horizon, kalendár): rozšírenie ho naučí vlastnosti systému a po každej jeho aktualizácii skontroluje, že spolupráca funguje.
- **📚 Tvoje predmety** – pri inštalácii zadáš, koľko ich máš, ďalšie pridáš alebo odoberieš kedykoľvek v Obsidiane (odobratie po potvrdení presunie priečinok do koša v macOS). Riadi sa nimi Domov, termíny, formulár úlohy vo Worde, plán aj ľavý panel.
- **✍️ Užitočný aj bez AI** – nová poznámka k materiálu (predvyplnená zo šablóny), týždenný prehľad, príprava na skúšku (zhrnutia, pojmy a kartičky predmetu v jednej poznámke), opakovanie kartičiek, pripomienky termínov, termíny do kalendára (.ics), citácie podľa STN ISO 690, archív predmetov na konci semestra a odhad času čítania vo fronte – všetko lokálne, nič sa nikam neposiela.
- **🔄 Aktualizácia jedným klikom** – Obsidian 1× denne skontroluje, či nevyšla nová verzia, a ponúkne *Čo je nové*, *Stiahnuť a nainštalovať* a *Teraz nie*. Rozšírenie balík stiahne a overí, ty len klikneš na **Inštalovať** (alebo **Zrušiť inštaláciu**). Poznámky, materiály, predmety a nastavenia zostanú; vopred sa urobí záloha a aktualizáciu ide vrátiť.
- **🌐 Štyri jazyky** – rozhranie, Domov, návod, šablóny poznámok aj inštalátor po česky, slovensky, anglicky a ukrajinsky;
  jazyk prepneš kedykoľvek v nastaveniach. Jazyk dokumentov vo Worde sa volí zvlášť (raz dopredu) a AI píše poznámky v jazyku rozhrania.
- **🛡 Bezpečnosť** – stráženie neoprávnených zmien kódu, ochrana proti skrytým pokynom v materiáloch (prompt injection),
  zip bombám a podvrhnutým dokumentom, prísne oprávnenia AI.

Podrobný návod: poznámka **01 Návod** (nainštaluje sa vo zvolenom jazyku).

## 🤖 S AI, s inou AI, alebo úplne bez AI

Vyberieš si pri inštalácii a kedykoľvek zmeníš v Obsidiane (*Nastavenia → Druhý mozek*):

| Režim | Čo potrebuješ | Poznámka |
|---|---|---|
| **Claude Code** (odporúčané) | [Claude Code](https://claude.com/claude-code) + predplatné Claude | najlepšie výsledky, platia bezpečnostné pravidlá systému |
| **Iná AI v Termináli** | napr. [Gemini CLI](https://github.com/google-gemini/gemini-cli) alebo [Codex CLI](https://github.com/openai/codex) | dostane rovnaké inštrukcie; bezpečnostné pravidlá systému na ňu neplatia – nechaj v nej zapnuté potvrdzovanie |
| **Bez AI – ručne** | nič | zadarmo, nič sa neposiela von; poznámky zo šablón, materiály odškrtávaš ručne |

Domov, front, termíny, úlohy vo Worde, Neuro Roadmap aj kontroly fungujú vo všetkých režimoch.

## 🧩 Inštalácia priamo z Obsidianu

1. V Obsidiane: **Nastavenia → Pluginy tretích strán → Prehľadávať**, nájdi **Druhý mozek**, klikni **Inštalovať** a **Zapnúť**.
2. Otvorí sa sprievodca: jazyk, jazyk dokumentov vo Worde, meno, UČO, tvoje predmety a režim AI. Skontroluje, či máš Python 3 (ak nie, ukáže, kde ho stiahnuť).
3. Klikni **🧠 Nastaviť** – v trezore vznikne Domov, Návod, šablóny, predmety a skripty. Nič existujúce sa neprepíše.

Verziu z adresára aktualizuje Obsidian (*Nastavenia → Pluginy tretích strán → Skontrolovať aktualizácie*). Po aktualizácii rozšírenie ponúkne obnovenie súborov v trezore – predtým sa zazálohujú a poznámky, ktoré si upravil, zostanú. Inštalátor nižšie vie to isté a navyše aktualizácie jedným klikom z GitHubu.

## ⚡ Inštalácia na pár kliknutí

1. **Stiahni:** zelené tlačidlo **Code → Download ZIP** (alebo najnovšie vydanie v *Releases*) a rozbaľ ho dvojklikom.
2. **Spusti inštalátor:** v priečinku dvakrát klikni na **`Instalovat.command`**.
   - macOS napoprvé ukáže varovanie, že súbor nejde overiť (inštalátor nie je podpísaný Applom – pozri [SECURITY.sk.md](SECURITY.sk.md)).
     Klikni **Hotovo**, otvor **Nastavenia systému → Súkromie a bezpečnosť**, zíď dole a pri „Instalovat.command“ klikni
     **Aj tak otvoriť** → potvrď heslom/Touch ID.
   - Nechceš klikať v nastaveniach? Otvor Terminál, napíš `bash ` (s medzerou), pretiahni do okna súbor `Instalovat.command` a stlač Enter.
3. **Odpovedz na pár otázok v oknách:** jazyk, nový alebo existujúci trezor, kam ho uložiť, meno, UČO, tvoje predmety, jazyk dokumentov vo Worde, AI, (voliteľne) logo.
   - Chýba ti Python alebo Obsidian? Inštalátor otvorí stránku na stiahnutie a po inštalácii klikneš **Hotovo – pokračovať**.
   - Keď inštaláciu prerušíš, nabudúce ponúkne **Pokračovať od kroku …** – nič nevypĺňaš znova.
4. **V Obsidiane:** *Otvoriť priečinok ako trezor* → vyber nový trezor (cesta je v schránke) →
   **Dôverovať autorovi a povoliť pluginy** → otvor **00 Domov** → **🩺 Skontrolovať systém**.

Hotovo. 🎉 Inštalátor nič nesťahuje, nič neodosiela, nepotrebuje heslo správcu a nič existujúce neprepíše.
Pred inštaláciou overí kontrolné súčty všetkých súborov. Čo presne robí, je napísané na jeho začiatku (otvor ho v TextEdite).

## 🔄 Aktualizácia na novú verziu

1. Obsidian ukáže **🆕 Je dostupná nová verzia druhého mozgu** – **📋 Čo je nové** otvorí zoznam zmien ([CHANGELOG](../CHANGELOG.md)), **Teraz nie** sa opýta znova po ďalšom spustení Obsidianu.
2. **⬇️ Stiahnuť a nainštalovať** – rozšírenie stiahne balík z Releases tohto repozitára a overí ho: kontrolný súčet ZIPu zverejnený pri vydaní, kontrolné súčty všetkých súborov (`SHA256SUMS.txt`) a číslo verzie. Dovtedy sa v trezore nič nemení a **Zrušiť inštaláciu** všetko zastaví.
3. **✅ Inštalovať** – urobí sa záloha trezoru, vymení sa kód systému a rozšírenie sa znova načíta.

**Poznámky, materiály, predmety, nastavenia a tvoje CSS predmetov zostanú.** Systémové poznámky, ktoré si upravil (Domov, Návod, šablóny, pravidlá AI), sa neprepíšu – nová verzia sa uloží vedľa s príponou „(nová verzia)“. Keď sa inštalácia uprostred pokazí, všetky zmeny sa samy vrátia. Pre prípad núdze je 7 dní k dispozícii **↩️ Vrátiť poslednú aktualizáciu** v *Nastavenia → Druhý mozek → Aktualizácie*; potom ide dočasná záloha z aktualizácie (skrytý priečinok `.druhy-mozek-zaloha`) do koša. Klik na Inštalovať potvrdí 🛡 len pri súboroch zhodných s overeným balíkom. Ide to aj ručne: stiahni ZIP a spusti `Instalovat.command` → *Aktualizovať existujúci trezor*. Kontrolu ide vypnúť v *Nastavenia → Druhý mozek → Aktualizácie*.

## Požiadavky

| Čo | Odkaz | Poznámka |
|---|---|---|
| macOS | – | tlačidlá s AI používajú Terminál a AppleScript |
| Obsidian 1.9+ | [obsidian.md](https://obsidian.md/download) | potrebuje vstavané *Bases* |
| Python 3 | [python.org](https://www.python.org/downloads/) alebo `brew install python` | len štandardná knižnica, nič ďalšie sa neinštaluje |
| *voliteľne* AI | [Claude Code](https://claude.com/claude-code) (odporúčané) alebo iná AI v Termináli | len pre tlačidlá s AI; bez AI funguje všetko ostatné |
| Microsoft Word | – | pre úlohy v šablóne |
| *voliteľne* Neuro Roadmap | [GitHub](https://github.com/phenex80/obsidian-neuro-roadmap) | v Obsidiane: *Pluginy tretích strán → Prehľadávať → Neuro Roadmap* (len anglicky) |
| *voliteľne* Spaced Repetition | v Obsidiane: *Pluginy tretích strán → Prehľadávať* | opakovanie kartičiek |

## Ručná inštalácia (bez inštalátora)

1. **Stiahni repozitár:** **Code → Download ZIP** a rozbaľ ho.
2. **Skopíruj obsah priečinka `trezor/`** do svojho trezoru Obsidianu (alebo priečinok rovno otvor: *Obsidian → Otvoriť priečinok ako trezor*).
   Priečinky `.obsidian` a `.claude` sú skryté – vo Finderi ich zobrazíš skratkou **Cmd+Shift+.** (bodka).
3. **Osobné údaje:** v `_Systém/` premenuj `nastaveni.priklad.json` na `nastaveni.json` a vyplň meno a UČO
   (`jazyk` a `jazyk_word`: `cs`, `sk`, `en` alebo `uk`). Potom v Obsidiane zvoľ jazyk v *Nastavenia → Druhý mozek*
   – rozšírenie prepíše systémové poznámky (Domov, Návod, šablóny) do zvoleného jazyka.
4. **Logo (voliteľné):** ulož logo svojej fakulty ako `_Systém/Word/logo-muni-arts.png` (PNG, priehľadné pozadie).
   Logo MU v repozitári nie je, lebo je ochrannou známkou. Bez loga má hlavička len text.
5. **Vytvor šablónu a front** – v Termináli v priečinku trezoru:
   ```bash
   python3 _Systém/Word/vytvor_sablonu.py
   python3 _Systém/priprav.py
   ```
6. **Zapni rozšírenie:** *Obsidian → Nastavenia → Pluginy tretích strán → Zapnúť* a povoľ **Druhý mozek**.
   *Nastavenia → Vzhľad → CSS úryvky* → zapni **druhy-mozek**.
7. **Predmety:** v Obsidiane pridaj každý svoj predmet tlačidlom **📚 Pridať predmet** (kód + názov); ukážkový predmet odoberieš v *Nastavenia → Druhý mozek → Predmety*.
8. Otvor **🏠 00 Domov** a klikni na **🩺 Skontrolovať systém** – všetko by malo svietiť ✅.
   Pri prvom tlačidle s AI povoľ Obsidianu ovládanie Terminálu (*Nastavenia systému → Súkromie a bezpečnosť → Automatizácia*).

## Bezpečnosť a súkromie

Ako si inštaláciu overiť (kontrolné súčty, automatické testy) a čo inštalátor nerobí: **[SECURITY.sk.md](SECURITY.sk.md)**.

- **Nič sa neodosiela inam než do zvolenej AI**, a to len pri tlačidlách s AI (v režime bez AI vôbec nič). Rozšírenie sa len 1× denne opýta GitHubu na číslo poslednej verzie – dá sa to vypnúť.
- AI smie bez pýtania len upravovať poznámky a spúšťať dva skripty systému. Mazanie, sťahovanie, `sudo`, `ssh` a čítanie kľúčov
  (`~/.ssh`, Kľúčenka, `.env`, dáta pluginov) je zakázané; úpravy nastavení, skriptov a web vyžadujú potvrdenie.
- Obsah materiálov je pre AI **dáta, nie pokyny** – skryté inštrukcie v dokumentoch AI nevykoná a upozorní na ne.
- Rozšírenie stráži odtlačky skriptov a pravidiel; pri nepotvrdenej zmene ich odmietne spustiť a upozorní.
- `.gitignore` bráni nahraniu osobných údajov (`nastaveni.json`), študijných materiálov, vygenerovaných súborov a dát pluginov.

## Vyhlásenia

Vyžaduje ich adresár rozšírení Obsidianu:
- **Sieť:** verzia z GitHubu sa 1× denne opýta `api.github.com` na číslo poslednej verzie a aktualizáciu stiahne až po kliknutí na *Stiahnuť a nainštalovať*. Verzia z adresára sama nič nesťahuje (aktualizuje ju Obsidian). Tlačidlá s AI spustia v Termináli zvolený nástroj (napr. Claude Code), ktorý materiál posiela svojmu poskytovateľovi. Hlásenie chyby len otvorí tvoj e-mail alebo GitHub s predvyplneným textom.
- **Súbory mimo trezoru:** automatická záloha kopíruje trezor do priečinka, ktorý zvolíš (OneDrive, Google Drive, iCloud…); aktualizácia používa dočasný priečinok; tlačidlá s AI otvárajú Terminál. Rozšírenie spúšťa pribalené skripty v Pythone 3, ktorý máš nainštalovaný.
- **Žiadna telemetria, reklamy, účty ani platby.**

## 🐞 Našiel si chybu alebo máš nápad?

- **Priamo v Obsidiane:** **🐞 Nahlásiť chybu alebo nápad** (ikona 🧠, Cmd+P alebo *Nastavenia → Druhý mozek*). Predvyplní technické údaje **bez osobných dát** (verzia, jazyk, režim AI, výsledok kontroly, posledné chyby – žiadne meno, UČO, cesty ani obsah poznámok). Všetko vidíš a môžeš upraviť; nič sa neodošle samo. Odošleš e-mailom alebo na GitHube.
- **Na GitHube:** [Issues → New issue](https://github.com/shadowsh1t/second-brain-kisk/issues/new/choose) – formuláre pre chyby a nápady.
- **Bezpečnostné problémy súkromne:** [súkromné hlásenie zraniteľnosti](https://github.com/shadowsh1t/second-brain-kisk/security/advisories/new) alebo e-mail na `catty.skipping888@passinbox.com` s predmetom `[SECURITY]`.

## Poďakovanie

- **[Neuro Roadmap](https://github.com/phenex80/obsidian-neuro-roadmap)** – Matteo Rossi ([@phenex80](https://github.com/phenex80)). Plánovač úloh, s ktorým tento systém spolupracuje.
  Nie je súčasťou repozitára, má vlastnú licenciu (PolyForm Noncommercial 1.0.0) a jeho rozhranie je len anglicky.
- Vzhľad šablóny Word vychádza zo študentských prác v štýle **MUNI ARTS**.
- Vytvorené s pomocou [Claude Code](https://claude.com/claude-code).

## Licencia

[PolyForm Noncommercial 1.0.0](../LICENSE) – zadarmo na osobné, študijné, výučbové a iné nekomerčné použitie vrátane úprav a zdieľania. Komerčné použitie len so súhlasom autora.

© 2026 Jakub Josef Sova ([@shadowsh1t](https://github.com/shadowsh1t))
