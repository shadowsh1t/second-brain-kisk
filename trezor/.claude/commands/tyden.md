---
description: Týdenní přehled studia
---
Vytvoř týdenní přehled podle `.claude/CLAUDE.md`. Čti co nejméně souborů.

1. `python3 _Systém/priprav.py --zmenene 7` → co se tento týden změnilo.
2. `python3 _Systém/priprav.py --ukoly` → otevřené úkoly a jejich termíny.
3. Spusť `python3 _Systém/priprav.py` → kolik čeká ve frontě.
4. Ze změněných poznámek přečti jen sekce „Shrnutí“.
5. Zapiš `_Přehledy/Týden <rok>-W<číslo týdne>.md` (vlastnost `typ: prehled`) se sekcemi:
   Co jsem probral · Termíny na příští 2 týdny · Čeká na zpracování · 5 otázek na zopakování · Na co nezapomenout.
6. V chatu odpověz jen 3–5 řádky.
