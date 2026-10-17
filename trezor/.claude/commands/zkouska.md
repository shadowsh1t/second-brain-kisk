---
description: Studijní balíček na zkoušku z jednoho předmětu
argument-hint: <název předmětu>
---
Připrav podklady na zkoušku z předmětu: **$ARGUMENTS**. Postupuj podle `.claude/CLAUDE.md`.

1. Čti jen poznámky v `$ARGUMENTS/Poznámky/` a přehled `$ARGUMENTS/$ARGUMENTS.md` – ne originály.
   Pokud poznámky chybí, řekni, že je nejdřív potřeba spustit `/zpracuj`.
2. Vytvoř `$ARGUMENTS/Zkouška – $ARGUMENTS.md` (`typ: zkouska`):
   - podmínky ukončení a termíny (z přehledu předmětu),
   - souhrn celého předmětu na 1 stranu,
   - Mermaid mindmap celého předmětu,
   - 15 zkouškových otázek s krátkými odpověďmi (rozbalovací callout `> [!question]-`),
   - 15 kartiček `Otázka::Odpověď` pod nadpisem s tagem `#flashcards/<KÓD>`.
3. Vytvoř plátno `$ARGUMENTS/Mapa – $ARGUMENTS.canvas`: střed předmět, kolem přednášky (uzly typu file), pod nimi pojmy.
