---
description: Zpracuje nové materiály do poznámek v Obsidianu (šetrně k tokenům)
---
Zpracuj nové studijní materiály podle `.claude/CLAUDE.md`.

1. Spusť `python3 _Systém/priprav.py` (přesně takhle – relativní cesta, bez pipe) a přečti `_Systém/fronta.json`. Když je fronta prázdná, napiš to a skonči.
2. Soubory z `_Vkládání učiva/` a soubory ležící přímo v kořeni předmětu: podle cache urči předmět a název z nadpisu dokumentu
   (`python3 _Systém/priprav.py --navrh "<soubor>"` dá návrh) a zařaď je příkazem
   `python3 _Systém/priprav.py --presun "<soubor>" "<Předmět>" "<Název>"` (ne `mv`), pak spusť `priprav.py` znovu.
   Název: `Téma – KÓD`, u interaktivní osnovy `IO – Téma – KÓD` (přípona se doplní sama). Zadání úkolu nezařazuj do Učiva, patří k úkolu.
3. Pro každou položku fronty (nejdřív zadání úkolů a osnovy, pak učivo):
   - přečti jen cache (originál nebo `obrazky` jen podle pravidel v CLAUDE.md); tabulky, data grafů, `[poznámky řečníka]`
     a `[odkazy]` v cache patří do výpisků,
   - rozhodni typ: přednáška/učivo → poznámka `prednaska`; zadání → `ukol`; osnova → doplň přehled předmětu;
     vlastní práce nebo odkaz `.webloc` → zapiš do přehledu předmětu (sekce Odevzdáno / Odkazy);
   - vytvoř nebo doplň poznámky a pojmy (poznámka má `zdroj: "[[<název souboru>]]"`),
   - **kontrola úplnosti:** `python3 _Systém/priprav.py --kontrola "<cesta>"`. Když poznámka nemá `zdroj` s tímhle souborem
     (osnova → přehled předmětu, sloučené verze), přidej cestu poznámky jako druhý argument. Každou položku `✗` doplň
     do poznámky (Edit), nebo když do výpisků opravdu nepatří (logo, hlavička, číslo bez významu), zdůvodni ji:
     `python3 _Systém/priprav.py --vynech "<cesta>" ID[,ID] "důvod"`. Kontrolu opakuj, dokud nic nechybí.
   - **druhé čtení:** projdi cache po oddílech proti poznámce – chybí definice, vztah, příklad, krok nebo požadavek, který by
     byl potřeba u zkoušky nebo k úkolu? Doplň ho. Co z cache nejde jistě vyložit (nečitelné OCR, rozpor, graf bez dat),
     zapiš: `python3 _Systém/priprav.py --k-overeni "<cesta>" "co a kde"` – ukáže se uživateli ve Frontě.
   - označ hotovo: `python3 _Systém/priprav.py --hotovo "<cesta>"` (+ stejná cesta poznámky jako u kontroly).
     Projde jen po úplné kontrole. Vlastní práce: `--preskoc`.
4. Pokud je ve frontě víc než 8 položek, zpracuj 8 a zeptej se, jestli pokračovat.
5. Nakonec spusť `priprav.py` ještě jednou (aktualizuje dashboard) a napiš krátký souhrn:
   co vzniklo, nové termíny, co zbývá.

$ARGUMENTS
