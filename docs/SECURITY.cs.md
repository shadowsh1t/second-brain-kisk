# 🔒 Bezpečnost a ověření

<details>
<summary>🌐 <b>Jazyk</b> · Čeština</summary>

[English](../SECURITY.md) · [Slovenčina](SECURITY.sk.md) · [Українська](SECURITY.uk.md)

</details>

## Jak si ověřit, že instalace je v pořádku

1. **Stahuj jen z tohoto repozitáře na GitHubu** (Code → Download ZIP, nebo z [Releases](https://github.com/shadowsh1t/second-brain-kisk/releases)).
2. **Zelená fajfka ✅ u posledního commitu** znamená, že automatická kontrola na čistém Macu na serverech GitHubu
   prošla: kontrolní součty, syntaxe, instalátor (i pokračování a ochrana existujícího trezoru), šablona Wordu,
   fronta, převod do šablony, všechny čtyři jazyky, odmítnutí podvržených dokumentů a kontrola, že v repozitáři nejsou osobní údaje.
   Kontrola nepoužívá žádné cizí akce – jen `git` a soubory z repozitáře ([.github/workflows/kontrola.yml](../.github/workflows/kontrola.yml)).
3. **Kontrolní součty:** v rozbalené složce v Terminálu spusť
   ```bash
   shasum -a 256 -c SHA256SUMS.txt
   ```
   Každý řádek musí končit `OK`. Instalátor to ověřuje sám a při nesouladu se nespustí.
   Pro jistotu porovnej i otisk samotného `SHA256SUMS.txt` s tím, který je uvedený u vydání v *Releases*:
   ```bash
   shasum -a 256 SHA256SUMS.txt
   ```
4. **Přečti si instalátor** – `Instalovat.command` je obyčejný text (otevři v TextEditu). Na začátku je seznam
   všeho, co dělá.

## Proč macOS při spuštění varuje

Instalátor není podepsaný certifikátem Apple Developer (stojí 99 $ ročně). macOS proto napoprvé hlásí,
že soubor nejde ověřit. Místo podpisu Applu slouží k ověření kontrolní součty a automatická kontrola výše.
Postup spuštění je v [README](README.cs.md#-instalace-na-pár-kliknutí).

## Co instalátor a systém NEDĚLAJÍ

- nic nestahují z internetu a nic neodesílají (AI tlačítka posílají obsah jen do zvolené AI, když na ně klikneš; rozšíření se jen 1× denně zeptá GitHubu na číslo poslední verze; aktualizaci stáhne až po kliknutí na *Stáhnout a nainstalovat*),
- nepoužívají `sudo` ani administrátorská práva,
- nepřepisují existující soubory (kopírování s `--ignore-existing`),
- osobní údaje (jméno, UČO) ukládají jen do `_Systém/nastaveni.json` ve tvém trezoru.

## Ochrany v systému

- **Oprávnění AI** (`trezor/.claude/settings.json`): bez ptaní jen dva skripty systému, `ls` a `date`;
  mazání, stahování, `sudo`, `ssh`, spouštění libovolného kódu (`python3 -c`, `bash -c`, `obsidian eval`…)
  a čtení klíčů zakázané; úpravy nastavení, skriptů a web jen s potvrzením.
- **Prompt injection:** obsah materiálů je pro AI data, ne pokyny (pravidla v `trezor/.claude/CLAUDE.md`).
- **Hlídání integrity:** rozšíření hlídá otisky skriptů a pravidel; nepotvrzené změny neprovede. Potvrdit je jde
  jen v okně Obsidianu opsáním náhodného kódu – ne příkazem.
- **Automatická záloha** kopíruje jen do složky, kterou si vybereš; mazat smí jen své vlastní složky záloh
  (pojmenované datem) a vždy až po úspěšném vytvoření nové zálohy. Data pluginů s klíči se nezálohují.
- **Převod dokumentů** odmítá zip bomby, odkazy mimo dokument a nepodporované vložené objekty.
- **Jazykové balíčky** jsou součástí hlídaných souborů; při změně jazyka rozšíření nejdřív udělá zálohu a zapisuje jen
  systémové poznámky uvnitř trezoru (cesty s `..` odmítne). Tvoje vlastní poznámky a materiály nemění.
- **Aktualizace** nikdy nezačne sama. Rozšíření jen čte z GitHubu číslo poslední verze. Po kliknutí na *Stáhnout a nainstalovat* stahuje jen z Releases tohoto repozitáře a ověří kontrolní součet ZIPu zveřejněný u vydání, kontrolní součty všech souborů a verzi; do kliknutí na **Instalovat** se nic nemění a **Zrušit instalaci** vše zastaví. Před instalací se trezor zazálohuje, nepovedená instalace se sama vrátí a 7 dní je k dispozici **↩️ Vrátit poslední aktualizaci**. Klik na Instalovat potvrdí 🛡 jen u souborů shodných s ověřeným balíkem. Poznámky, materiály, `nastaveni.json` ani soubory, které sis upravil, se nikdy nepřepíšou.

## Nahlášení chyby

Bezpečnostní problém nahlas **soukromě** – přes [Security → Report a vulnerability](https://github.com/shadowsh1t/second-brain-kisk/security/advisories/new) v tomto repozitáři, nebo e-mailem na `catty.skipping888@passinbox.com` s předmětem `[SECURITY]` (ne jako veřejné Issue). Ostatní chyby a nápady: **🐞 Nahlásit chybu nebo nápad** přímo v Obsidianu (technické údaje bez osobních dat, vše vidíš před odesláním) nebo přes [Issues](https://github.com/shadowsh1t/second-brain-kisk/issues/new/choose).
