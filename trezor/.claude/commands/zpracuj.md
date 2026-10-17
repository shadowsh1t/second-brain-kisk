---
description: Zpracuje nové materiály do poznámek v Obsidianu (šetrně k tokenům)
---
Zpracuj nové studijní materiály podle `.claude/CLAUDE.md`.

1. Spusť `python3 _Systém/priprav.py` (přesně takhle – relativní cesta, bez pipe) a přečti `_Systém/fronta.json`. Když je fronta prázdná, napiš to a skonči.
2. Soubory z `_Inbox/`: podle obsahu cache urči předmět, přesuň originál příkazem
   `python3 _Systém/priprav.py --presun "_Inbox/<soubor>" "<Předmět>"` (ne `mv`) a spusť `priprav.py` znovu.
3. Pro každou položku fronty (nejdřív zadání úkolů a osnovy, pak učivo):
   - přečti jen cache (originál nebo `obrazky` jen podle pravidel v CLAUDE.md); tabulky, data grafů, `[poznámky řečníka]`
     a `[odkazy]` v cache patří do výpisků,
   - rozhodni typ: přednáška/učivo → poznámka `prednaska`; zadání → `ukol`; osnova → doplň přehled předmětu;
     vlastní práce nebo odkaz `.webloc` → zapiš do přehledu předmětu (sekce Odevzdáno / Odkazy);
   - vytvoř nebo doplň poznámky a pojmy,
   - označ hotovo: `python3 _Systém/priprav.py --hotovo "<cesta>"` (vlastní práce: `--preskoc`).
4. Pokud je ve frontě víc než 8 položek, zpracuj 8 a zeptej se, jestli pokračovat.
5. Nakonec spusť `priprav.py` ještě jednou (aktualizuje dashboard) a napiš krátký souhrn:
   co vzniklo, nové termíny, co zbývá.

$ARGUMENTS
