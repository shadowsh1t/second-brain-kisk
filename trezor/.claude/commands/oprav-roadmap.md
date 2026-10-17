---
description: Opraví propojení druhého mozku s pluginem Neuro Roadmap po jeho aktualizaci
---
Plugin Neuro Roadmap (Matteo Rossi, https://github.com/phenex80/obsidian-neuro-roadmap) se změnil a naše propojení hlásí problém.

1. Přečti `_Systém/Kontrola druhého mozku.md` – co přesně selhalo a jaká je nová verze.
2. Zjisti, co se v pluginu změnilo: přečti `docs/configuration.md`, `docs/tasks-and-metadata.md` a release notes nové verze
   (raw soubory z větve `master` na GitHubu). Do `.obsidian/plugins/neuro-roadmap/data.json` NEČTI – mohou tam být přihlašovací údaje.
   `obsidian eval` je z bezpečnostních důvodů zakázaný – stav propojení zjistíš ze zprávy kontroly (krok 1) a z dokumentace.
   Když potřebuješ vědět víc o nastavení pluginu, popros uživatele, ať ti ho zkopíruje z *Nastavení → Neuro Roadmap*.
3. Uprav jen NAŠE soubory, aby zase spolupracovaly:
   - `.obsidian/plugins/druhy-mozek/main.js` (konstanty `MAPOVANI_VLASTNOSTI`, `MAPOVANI_HODNOT`, `ROADMAP_PRIKAZ`, funkce `kontrola`),
   - případně vlastnosti v poznámkách úkolů, šablonu `_Systém/Šablony/Úkol.md`, `_Systém/novy_ukol.py` a `.claude/CLAUDE.md`.
   Mattův plugin (`.obsidian/plugins/neuro-roadmap/`) nikdy neupravuj.
4. Požádej uživatele, ať v Obsidianu klikne na **🩺 Zkontrolovat propojení** (případně potvrď příkaz `obsidian plugin:reload id=druhy-mozek`).
   Ověř výsledek v `_Systém/Kontrola druhého mozku.md`.
5. Napiš uživateli krátce v jeho jazyce (`jazyk` v `_Systém/nastaveni.json`), co se změnilo a co jsi upravila, a upozorni ho, že změny kódu musí potvrdit (🛡). Mazat nic nesmíš.
