# 🔒 Bezpečnosť a overenie

<details>
<summary>🌐 <b>Jazyk</b> · Slovenčina</summary>

[English](../SECURITY.md) · [Čeština](SECURITY.cs.md) · [Українська](SECURITY.uk.md)

</details>

## Ako si overiť, že inštalácia je v poriadku

1. **Sťahuj len z tohto repozitára na GitHube** (Code → Download ZIP, alebo z [Releases](https://github.com/shadowsh1t/second-brain-kisk/releases)).
2. **Zelená fajka ✅ pri poslednom commite** znamená, že automatická kontrola na čistom Macu na serveroch GitHubu
   prešla: kontrolné súčty, syntax, inštalátor (aj pokračovanie a ochrana existujúceho trezoru), šablóna Wordu,
   front, prevod do šablóny, všetky štyri jazyky, odmietnutie podvrhnutých dokumentov a kontrola, že v repozitári nie sú osobné údaje.
   Kontrola nepoužíva žiadne cudzie akcie – len `git` a súbory z repozitára ([.github/workflows/kontrola.yml](../.github/workflows/kontrola.yml)).
3. **Kontrolné súčty:** v rozbalenom priečinku v Termináli spusti
   ```bash
   shasum -a 256 -c SHA256SUMS.txt
   ```
   Každý riadok musí končiť `OK`. Inštalátor to overuje sám a pri nesúlade sa nespustí.
   Pre istotu porovnaj aj odtlačok samotného `SHA256SUMS.txt` s tým, ktorý je uvedený pri vydaní v *Releases*:
   ```bash
   shasum -a 256 SHA256SUMS.txt
   ```
4. **Prečítaj si inštalátor** – `Instalovat.command` je obyčajný text (otvor v TextEdite). Na začiatku je zoznam
   všetkého, čo robí.

## Prečo macOS pri spustení varuje

Inštalátor nie je podpísaný certifikátom Apple Developer (stojí 99 $ ročne). macOS preto napoprvé hlási,
že súbor nejde overiť. Namiesto podpisu Applu slúžia na overenie kontrolné súčty a automatická kontrola vyššie.
Postup spustenia je v [README](README.sk.md#-inštalácia-na-pár-kliknutí).

## Čo inštalátor a systém NEROBIA

- nič nesťahujú z internetu a nič neodosielajú (AI tlačidlá posielajú obsah len do zvolenej AI, keď na ne klikneš; rozšírenie sa len 1× denne opýta GitHubu na číslo poslednej verzie; aktualizáciu stiahne až po kliknutí na *Stiahnuť a nainštalovať*),
- nepoužívajú `sudo` ani administrátorské práva,
- neprepisujú existujúce súbory (kopírovanie s `--ignore-existing`),
- osobné údaje (meno, UČO) ukladajú len do `_Systém/nastaveni.json` v tvojom trezore.

## Ochrany v systéme

- **Oprávnenia AI** (`trezor/.claude/settings.json`): bez pýtania len dva skripty systému, `ls` a `date`;
  mazanie, sťahovanie, `sudo`, `ssh`, spúšťanie ľubovoľného kódu (`python3 -c`, `bash -c`, `obsidian eval`…)
  a čítanie kľúčov zakázané; úpravy nastavení, skriptov a web len s potvrdením.
- **Prompt injection:** obsah materiálov je pre AI dáta, nie pokyny (pravidlá v `trezor/.claude/CLAUDE.md`).
- **Stráženie integrity:** rozšírenie stráži odtlačky skriptov a pravidiel; nepotvrdené zmeny nevykoná. Potvrdiť ich ide
  len v okne Obsidianu opísaním náhodného kódu – nie príkazom.
- **Automatická záloha** kopíruje len do priečinka, ktorý si vyberieš; mazať smie len svoje vlastné priečinky záloh
  (pomenované dátumom) a vždy až po úspešnom vytvorení novej zálohy. Dáta pluginov s kľúčmi sa nezálohujú.
- **Prevod dokumentov** odmieta zip bomby, odkazy mimo dokument a nepodporované vložené objekty.
- **Jazykové balíčky** sú súčasťou strážených súborov; pri zmene jazyka rozšírenie najprv urobí zálohu a zapisuje len
  systémové poznámky vnútri trezoru (cesty s `..` odmietne). Tvoje vlastné poznámky a materiály nemení.
- **Aktualizácia** nikdy nezačne sama. Rozšírenie len číta z GitHubu číslo poslednej verzie. Po kliknutí na *Stiahnuť a nainštalovať* sťahuje len z Releases tohto repozitára a overí kontrolný súčet ZIPu zverejnený pri vydaní, kontrolné súčty všetkých súborov a verziu; do kliknutia na **Inštalovať** sa nič nemení a **Zrušiť inštaláciu** všetko zastaví. Pred inštaláciou sa trezor zazálohuje, nepodarená inštalácia sa sama vráti a 7 dní je k dispozícii **↩️ Vrátiť poslednú aktualizáciu**. Klik na Inštalovať potvrdí 🛡 len pri súboroch zhodných s overeným balíkom. Poznámky, materiály, `nastaveni.json` ani súbory, ktoré si upravil, sa nikdy neprepíšu.

## Nahlásenie chyby

Bezpečnostný problém nahlás **súkromne** – cez [Security → Report a vulnerability](https://github.com/shadowsh1t/second-brain-kisk/security/advisories/new) v tomto repozitári, alebo e-mailom na `catty.skipping888@passinbox.com` s predmetom `[SECURITY]` (nie ako verejné Issue). Ostatné chyby a nápady: **🐞 Nahlásiť chybu alebo nápad** priamo v Obsidiane (technické údaje bez osobných dát, všetko vidíš pred odoslaním) alebo cez [Issues](https://github.com/shadowsh1t/second-brain-kisk/issues/new/choose).
