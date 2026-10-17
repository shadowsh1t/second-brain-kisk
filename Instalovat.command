#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  Druhý mozek pro KISK – instalátor (macOS) · čeština, slovenčina, English, українська
#  Spuštění: dvojklik na tento soubor (napoprvé viz README – „Přesto otevřít“),
#  nebo v Terminálu:  bash Instalovat.command
#
#  Co dělá (a nic jiného):
#   0. zeptá se na jazyk
#   1. ověří kontrolní součty souborů a zkontroluje Python, Obsidian a Word
#   2. zeptá se, kam instalovat (nový / existující trezor) – nebo jestli aktualizovat existující instalaci
#   3. zeptá se na jméno, UČO, předměty (kolik chceš), jazyk dokumentů ve Wordu a práci s AI (Claude / jiná AI / bez AI)
#   4. zkopíruje systém ve zvoleném jazyce do cíle – NIC EXISTUJÍCÍHO NEPŘEPÍŠE
#   5. zapne rozšíření, uloží nastaveni.json, (volitelně) logo, vytvoří šablonu Wordu a frontu
#   6. otevře Obsidian a ukáže, kam kliknout
#  Aktualizace (nastroje/aktualizace.py): nahradí kód systému, neupravené systémové poznámky přepíše, upravené nechá
#  (nová verze se uloží vedle) a poznámek, materiálů ani nastaveni.json se nedotkne. Předtím zálohuje.
#  Nic nestahuje, nic neodesílá, nepoužívá sudo. Rozdělanou instalaci jde dokončit dalším spuštěním
#  (postup se ukládá do skrytého souboru .instalace-postup vedle instalátoru).
#  Testy: odpovědi lze předat proměnnými DM_* (DM_TEST=1), volby i jako kódy (novy, claude, jina, zadna, cs…).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
ZDROJ="$PWD/trezor"
POSTUP="$PWD/.instalace-postup"
JAZYK="cs"

# ── texty ve 4 jazycích (bash 3.2 na macOS nemá asociativní pole) ──
_t() {
  case "$1:$2" in
    cs:nazev) echo "Druhý mozek – instalace" ;;
    sk:nazev) echo "Druhý mozog – inštalácia" ;;
    en:nazev) echo "Second Brain – installation" ;;
    uk:nazev) echo "Другий мозок – встановлення" ;;
    cs:prerusit) echo "Přerušit" ;;  sk:prerusit) echo "Prerušiť" ;;  en:prerusit) echo "Stop" ;;  uk:prerusit) echo "Перервати" ;;
    cs:pokracovat) echo "Pokračovat" ;;  sk:pokracovat) echo "Pokračovať" ;;  en:pokracovat) echo "Continue" ;;  uk:pokracovat) echo "Продовжити" ;;
    cs:prerusena) echo "Instalace přerušena. Při dalším spuštění můžeš pokračovat, kde jsi skončil." ;;
    sk:prerusena) echo "Inštalácia prerušená. Pri ďalšom spustení môžeš pokračovať, kde si skončil." ;;
    en:prerusena) echo "Installation stopped. Next time you can continue where you left off." ;;
    uk:prerusena) echo "Встановлення перервано. Наступного разу можна продовжити з того ж місця." ;;
    cs:kroky) echo "|Kontrola požadavků|Umístění trezoru|Osobní údaje a AI|Kopírování souborů|Nastavení a šablona Wordu|Dokončení" ;;
    sk:kroky) echo "|Kontrola požiadaviek|Umiestnenie trezoru|Osobné údaje a AI|Kopírovanie súborov|Nastavenia a šablóna Wordu|Dokončenie" ;;
    en:kroky) echo "|Checking requirements|Vault location|Personal details and AI|Copying files|Settings and Word template|Finishing" ;;
    uk:kroky) echo "|Перевірка вимог|Розташування сховища|Особисті дані та ШІ|Копіювання файлів|Налаштування й шаблон Word|Завершення" ;;
    cs:rozdelana) echo "Našla jsem rozdělanou instalaci.

Hotovo: kroky 1–%s (naposledy „%s“)
Pokračovat se dá krokem %s: „%s“" ;;
    sk:rozdelana) echo "Našla som rozrobenú inštaláciu.

Hotovo: kroky 1–%s (naposledy „%s“)
Pokračovať sa dá krokom %s: „%s“" ;;
    en:rozdelana) echo "Found an unfinished installation.

Done: steps 1–%s (last: “%s”)
You can continue with step %s: “%s”" ;;
    uk:rozdelana) echo "Знайдено незавершене встановлення.

Виконано: кроки 1–%s (останній: «%s»)
Можна продовжити з кроку %s: «%s»" ;;
    cs:trezor) echo "Trezor" ;;  sk:trezor) echo "Trezor" ;;  en:trezor) echo "Vault" ;;  uk:trezor) echo "Сховище" ;;
    cs:zacit_znovu) echo "Začít znovu" ;;  sk:zacit_znovu) echo "Začať znova" ;;  en:zacit_znovu) echo "Start over" ;;  uk:zacit_znovu) echo "Почати знову" ;;
    cs:pokracovat_od) echo "Pokračovat od kroku %s" ;;  sk:pokracovat_od) echo "Pokračovať od kroku %s" ;;
    en:pokracovat_od) echo "Continue from step %s" ;;  uk:pokracovat_od) echo "Продовжити з кроку %s" ;;
    cs:soucty_chyba) echo "⚠️ Soubory instalace neodpovídají kontrolním součtům (SHA256SUMS.txt).

Stažení je poškozené nebo někdo soubory změnil. Instalace se z bezpečnostních důvodů nespustí – stáhni repozitář znovu z GitHubu." ;;
    sk:soucty_chyba) echo "⚠️ Súbory inštalácie nezodpovedajú kontrolným súčtom (SHA256SUMS.txt).

Stiahnutie je poškodené alebo niekto súbory zmenil. Inštalácia sa z bezpečnostných dôvodov nespustí – stiahni repozitár znova z GitHubu." ;;
    en:soucty_chyba) echo "⚠️ The installation files don't match the checksums (SHA256SUMS.txt).

The download is damaged or someone changed the files. For security reasons the installation won't run – download the repository again from GitHub." ;;
    uk:soucty_chyba) echo "⚠️ Файли встановлення не відповідають контрольним сумам (SHA256SUMS.txt).

Завантаження пошкоджене або хтось змінив файли. З міркувань безпеки встановлення не запуститься – завантаж репозиторій з GitHub ще раз." ;;
    cs:soucty_ok) echo "✅ Kontrolní součty souhlasí" ;;  sk:soucty_ok) echo "✅ Kontrolné súčty súhlasia" ;;
    en:soucty_ok) echo "✅ Checksums match" ;;  uk:soucty_ok) echo "✅ Контрольні суми збігаються" ;;
    cs:python_chybi) echo "Chybí Python 3 (nutný).

1. Klikni na „Otevřít stránku ke stažení“ (nebo potvrď instalaci vývojářských nástrojů, kterou macOS nabídne).
2. Nainstaluj ho.
3. Vrať se sem a klikni „Hotovo – pokračovat“." ;;
    sk:python_chybi) echo "Chýba Python 3 (nutný).

1. Klikni na „Otvoriť stránku na stiahnutie“ (alebo potvrď inštaláciu vývojárskych nástrojov, ktorú macOS ponúkne).
2. Nainštaluj ho.
3. Vráť sa sem a klikni „Hotovo – pokračovať“." ;;
    en:python_chybi) echo "Python 3 is missing (required).

1. Click “Open download page” (or confirm the developer tools installation macOS offers).
2. Install it.
3. Come back and click “Done – continue”." ;;
    uk:python_chybi) echo "Бракує Python 3 (обов’язково).

1. Натисни «Відкрити сторінку завантаження» (або підтверди встановлення інструментів розробника, яке запропонує macOS).
2. Встанови його.
3. Повернися сюди й натисни «Готово – продовжити»." ;;
    cs:otevrit_web) echo "Otevřít stránku ke stažení" ;;  sk:otevrit_web) echo "Otvoriť stránku na stiahnutie" ;;
    en:otevrit_web) echo "Open download page" ;;  uk:otevrit_web) echo "Відкрити сторінку завантаження" ;;
    cs:hotovo_pokracovat) echo "Hotovo – pokračovat" ;;  sk:hotovo_pokracovat) echo "Hotovo – pokračovať" ;;
    en:hotovo_pokracovat) echo "Done – continue" ;;  uk:hotovo_pokracovat) echo "Готово – продовжити" ;;
    cs:obsidian_chybi) echo "Nemáš nainstalovaný Obsidian (potřebuješ ho na otevření trezoru).

Stáhni ho, nainstaluj a klikni „Zkontrolovat znovu“. Instalovat ho můžeš i později – pak klikni „Pokračovat bez něj“." ;;
    sk:obsidian_chybi) echo "Nemáš nainštalovaný Obsidian (potrebuješ ho na otvorenie trezoru).

Stiahni ho, nainštaluj a klikni „Skontrolovať znova“. Nainštalovať ho môžeš aj neskôr – potom klikni „Pokračovať bez neho“." ;;
    en:obsidian_chybi) echo "Obsidian isn't installed (you need it to open the vault).

Download and install it, then click “Check again”. You can also install it later – then click “Continue without it”." ;;
    uk:obsidian_chybi) echo "Obsidian не встановлено (він потрібен, щоб відкрити сховище).

Завантаж і встанови його, потім натисни «Перевірити знову». Можна встановити й пізніше – тоді натисни «Продовжити без нього»." ;;
    cs:pokracovat_bez) echo "Pokračovat bez něj" ;;  sk:pokracovat_bez) echo "Pokračovať bez neho" ;;
    en:pokracovat_bez) echo "Continue without it" ;;  uk:pokracovat_bez) echo "Продовжити без нього" ;;
    cs:zkontrolovat_znovu) echo "Zkontrolovat znovu" ;;  sk:zkontrolovat_znovu) echo "Skontrolovať znova" ;;
    en:zkontrolovat_znovu) echo "Check again" ;;  uk:zkontrolovat_znovu) echo "Перевірити знову" ;;
    cs:obsidian_az) echo "Až bude Obsidian nainstalovaný v Aplikacích, klikni OK." ;;
    sk:obsidian_az) echo "Keď bude Obsidian nainštalovaný v Aplikáciách, klikni OK." ;;
    en:obsidian_az) echo "Click OK once Obsidian is installed in Applications." ;;
    uk:obsidian_az) echo "Коли Obsidian буде встановлено в Програмах, натисни OK." ;;
    cs:word_chybi) echo "ℹ️  Microsoft Word nenalezen – úkoly ve Wordu budou fungovat, až ho nainstaluješ." ;;
    sk:word_chybi) echo "ℹ️  Microsoft Word sa nenašiel – úlohy vo Worde budú fungovať, keď ho nainštaluješ." ;;
    en:word_chybi) echo "ℹ️  Microsoft Word not found – Word assignments will work once you install it." ;;
    uk:word_chybi) echo "ℹ️  Microsoft Word не знайдено – завдання у Word запрацюють після його встановлення." ;;
    cs:kam) echo "Kam chceš druhý mozek nainstalovat?

• Nový trezor – vytvoří novou složku pro Obsidian.
• Do existujícího trezoru – přidá systém k tvým poznámkám, nic nepřepíše.
• Aktualizovat existující trezor – nová verze systému; poznámky a nastavení zůstanou." ;;
    sk:kam) echo "Kam chceš druhý mozog nainštalovať?

• Nový trezor – vytvorí nový priečinok pre Obsidian.
• Do existujúceho trezoru – pridá systém k tvojim poznámkam, nič neprepíše.
• Aktualizovať existujúci trezor – nová verzia systému; poznámky a nastavenia zostanú." ;;
    en:kam) echo "Where do you want to install Second Brain?

• New vault – creates a new folder for Obsidian.
• Into an existing vault – adds the system to your notes, overwrites nothing.
• Update an existing vault – new version of the system; notes and settings stay." ;;
    uk:kam) echo "Куди встановити «другий мозок»?

• Нове сховище – створить нову папку для Obsidian.
• В наявне сховище – додасть систему до твоїх нотаток, нічого не перезапише.
• Оновити наявне сховище – нова версія системи; нотатки й налаштування залишаться." ;;
    cs:novy) echo "Nový trezor" ;;  sk:novy) echo "Nový trezor" ;;  en:novy) echo "New vault" ;;  uk:novy) echo "Нове сховище" ;;
    cs:existujici) echo "Do existujícího trezoru" ;;  sk:existujici) echo "Do existujúceho trezoru" ;;
    en:existujici) echo "Into an existing vault" ;;  uk:existujici) echo "В наявне сховище" ;;
    cs:aktualizace) echo "Aktualizovat existující trezor" ;;  sk:aktualizace) echo "Aktualizovať existujúci trezor" ;;
    en:aktualizace) echo "Update an existing vault" ;;  uk:aktualizace) echo "Оновити наявне сховище" ;;
    cs:vyber_aktualizace) echo "Vyber složku trezoru, který chceš aktualizovat:" ;;
    sk:vyber_aktualizace) echo "Vyber priečinok trezoru, ktorý chceš aktualizovať:" ;;
    en:vyber_aktualizace) echo "Choose the vault folder you want to update:" ;;
    uk:vyber_aktualizace) echo "Вибери папку сховища, яке хочеш оновити:" ;;
    cs:neni_instalace) echo "Ve vybrané složce druhý mozek není (chybí _Systém/nastaveni.json). Pro první instalaci zvol „Do existujícího trezoru“." ;;
    sk:neni_instalace) echo "Vo vybranom priečinku druhý mozog nie je (chýba _Systém/nastaveni.json). Na prvú inštaláciu zvoľ „Do existujúceho trezoru“." ;;
    en:neni_instalace) echo "Second Brain isn't in the chosen folder (_Systém/nastaveni.json is missing). For a first installation choose “Into an existing vault”." ;;
    uk:neni_instalace) echo "У вибраній папці немає «другого мозку» (бракує _Systém/nastaveni.json). Для першого встановлення обери «В наявне сховище»." ;;
    cs:akt_chyba) echo "Aktualizace se nepovedla – nic se nezměnilo, nebo je předchozí verze v záloze .druhy-mozek-zaloha.

%s" ;;
    sk:akt_chyba) echo "Aktualizácia sa nepodarila – nič sa nezmenilo, alebo je predchádzajúca verzia v zálohe .druhy-mozek-zaloha.

%s" ;;
    en:akt_chyba) echo "The update failed – nothing changed, or the previous version is in the .druhy-mozek-zaloha backup.

%s" ;;
    uk:akt_chyba) echo "Оновлення не вдалося – нічого не змінилося, або попередня версія є в резервній копії .druhy-mozek-zaloha.

%s" ;;
    cs:akt_ok) echo "✅ Aktualizováno: %s" ;;  sk:akt_ok) echo "✅ Aktualizované: %s" ;;  en:akt_ok) echo "✅ Updated: %s" ;;  uk:akt_ok) echo "✅ Оновлено: %s" ;;
    cs:akt_ponechano) echo "Tyhle soubory sis upravil, takže zůstaly beze změny – nová verze je uložená vedle nich s příponou „(nová verze)“:" ;;
    sk:akt_ponechano) echo "Tieto súbory si upravil, takže zostali bez zmeny – nová verzia je uložená vedľa nich s príponou „(nová verzia)“:" ;;
    en:akt_ponechano) echo "You edited these files, so they stayed unchanged – the new version is saved next to them with “(new version)”:" ;;
    uk:akt_ponechano) echo "Ці файли ти змінив, тому вони залишилися без змін – нова версія збережена поруч із позначкою «(нова версія)»:" ;;
    cs:akt_hotovo_okno) echo "Aktualizace hotová! 🎉 %s

Starší verze nahrazených souborů je v záloze ve skryté složce .druhy-mozek-zaloha v trezoru.
%s
Teď otevři Obsidian a na Domově klikni na 🛡 Potvrdit změny kódu (opíšeš kód) – do potvrzení se skripty nespustí." ;;
    sk:akt_hotovo_okno) echo "Aktualizácia hotová! 🎉 %s

Staršia verzia nahradených súborov je v zálohe v skrytom priečinku .druhy-mozek-zaloha v trezore.
%s
Teraz otvor Obsidian a na Domove klikni na 🛡 Potvrdiť zmeny kódu (opíšeš kód) – do potvrdenia sa skripty nespustia." ;;
    en:akt_hotovo_okno) echo "Update done! 🎉 %s

The older version of replaced files is backed up in the hidden .druhy-mozek-zaloha folder in the vault.
%s
Now open Obsidian and on Home click 🛡 Confirm code changes (retype the code) – scripts won't run until you confirm." ;;
    uk:akt_hotovo_okno) echo "Оновлення готове! 🎉 %s

Стара версія замінених файлів збережена в прихованій папці .druhy-mozek-zaloha у сховищі.
%s
Тепер відкрий Obsidian і на Головній натисни 🛡 Підтвердити зміни коду (перепишеш код) – до підтвердження скрипти не запустяться." ;;
    cs:vyber_kde) echo "Vyber, KDE se má nový trezor vytvořit (např. Dokumenty nebo OneDrive):" ;;
    sk:vyber_kde) echo "Vyber, KDE sa má nový trezor vytvoriť (napr. Dokumenty alebo OneDrive):" ;;
    en:vyber_kde) echo "Choose WHERE to create the new vault (e.g. Documents or OneDrive):" ;;
    uk:vyber_kde) echo "Вибери, ДЕ створити нове сховище (напр. Документи або OneDrive):" ;;
    cs:jak_nazev) echo "Jak se má trezor (složka) jmenovat?" ;;  sk:jak_nazev) echo "Ako sa má trezor (priečinok) volať?" ;;
    en:jak_nazev) echo "What should the vault (folder) be called?" ;;  uk:jak_nazev) echo "Як назвати сховище (папку)?" ;;
    cs:vychozi_nazev) echo "Studium KISK" ;;  sk:vychozi_nazev) echo "Štúdium KISK" ;;  en:vychozi_nazev) echo "KISK Studies" ;;  uk:vychozi_nazev) echo "Навчання KISK" ;;
    cs:neprazdna) echo "Složka „%s“ už existuje a není prázdná. Spusť instalaci znovu a zvol jiný název, nebo „Do existujícího trezoru“." ;;
    sk:neprazdna) echo "Priečinok „%s“ už existuje a nie je prázdny. Spusti inštaláciu znova a zvoľ iný názov alebo „Do existujúceho trezoru“." ;;
    en:neprazdna) echo "The folder “%s” already exists and isn't empty. Run the installer again and choose another name, or “Into an existing vault”." ;;
    uk:neprazdna) echo "Папка «%s» вже існує й не порожня. Запусти встановлення знову й обери іншу назву або «В наявне сховище»." ;;
    cs:vyber_existujici) echo "Vyber složku svého trezoru Obsidianu:" ;;  sk:vyber_existujici) echo "Vyber priečinok svojho trezoru Obsidianu:" ;;
    en:vyber_existujici) echo "Choose your Obsidian vault folder:" ;;  uk:vyber_existujici) echo "Вибери папку свого сховища Obsidian:" ;;
    cs:neni_trezor) echo "Ve vybrané složce není .obsidian – asi to není trezor. Systém se do ní i tak nainstaluje." ;;
    sk:neni_trezor) echo "Vo vybranom priečinku nie je .obsidian – asi to nie je trezor. Systém sa doň aj tak nainštaluje." ;;
    en:neni_trezor) echo "The chosen folder has no .obsidian – it's probably not a vault. The system will be installed there anyway." ;;
    uk:neni_trezor) echo "У вибраній папці немає .obsidian – мабуть, це не сховище. Система все одно буде встановлена туди." ;;
    cs:jmeno) echo "Tvoje jméno a příjmení (jak je chceš mít v záhlaví prací):" ;;
    sk:jmeno) echo "Tvoje meno a priezvisko (ako ich chceš mať v hlavičke prác):" ;;
    en:jmeno) echo "Your full name (as you want it in the header of your work):" ;;
    uk:jmeno) echo "Твоє ім’я та прізвище (як має бути в заголовку робіт):" ;;
    cs:jmeno_chybi) echo "Jméno je potřeba vyplnit – spusť instalaci znovu." ;;  sk:jmeno_chybi) echo "Meno treba vyplniť – spusti inštaláciu znova." ;;
    en:jmeno_chybi) echo "The name is required – run the installer again." ;;  uk:jmeno_chybi) echo "Ім’я обов’язкове – запусти встановлення знову." ;;
    cs:uco) echo "Tvoje UČO (číslo studenta v ISu):" ;;  sk:uco) echo "Tvoje UČO (číslo študenta v IS):" ;;
    en:uco) echo "Your UČO (student number in the IS):" ;;  uk:uco) echo "Твій UČO (номер студента в IS):" ;;
    cs:uco_chyba) echo "UČO má být jen číslo (4–7 číslic) – spusť instalaci znovu." ;;  sk:uco_chyba) echo "UČO má byť len číslo (4–7 číslic) – spusti inštaláciu znova." ;;
    en:uco_chyba) echo "UČO must be a number only (4–7 digits) – run the installer again." ;;  uk:uco_chyba) echo "UČO має бути лише числом (4–7 цифр) – запусти встановлення знову." ;;
    cs:jmeno_soubor) echo "Jméno v názvu souborů (jak je odevzdáváš do ISu, obvykle Příjmení Jméno):" ;;
    sk:jmeno_soubor) echo "Meno v názve súborov (ako ich odovzdávaš do IS, zvyčajne Priezvisko Meno):" ;;
    en:jmeno_soubor) echo "Name in file names (as you submit them to the IS, usually Surname Name):" ;;
    uk:jmeno_soubor) echo "Ім’я в назвах файлів (як здаєш в IS, зазвичай Прізвище Ім’я):" ;;
    cs:predmet_dotaz) echo "Tvoje předměty – zadávej je po jednom ve tvaru KÓD Název, např.
ISKB02 Úvod do knihovnictví

Předmět č. %s (až zadáš všechny, nech pole prázdné a klikni Pokračovat; přidat i odebrat je jde i později v Obsidianu):" ;;
    sk:predmet_dotaz) echo "Tvoje predmety – zadávaj ich po jednom v tvare KÓD Názov, napr.
ISKB02 Úvod do knihovníctva

Predmet č. %s (keď zadáš všetky, nechaj pole prázdne a klikni Pokračovať; pridať aj odobrať ich ide aj neskôr v Obsidiane):" ;;
    en:predmet_dotaz) echo "Your courses – enter them one at a time as CODE Name, e.g.
ISKB02 Introduction to Librarianship

Course no. %s (when you've entered all of them, leave the field empty and click Continue; you can add and remove them later in Obsidian too):" ;;
    uk:predmet_dotaz) echo "Твої предмети – вводь по одному у форматі КОД Назва, напр.
ISKB02 Вступ до бібліотекознавства

Предмет № %s (коли введеш усі, залиш поле порожнім і натисни Продовжити; додати й вилучити їх можна й пізніше в Obsidian):" ;;
    cs:predmety_ok) echo "✅ Předměty: %s" ;;  sk:predmety_ok) echo "✅ Predmety: %s" ;;  en:predmety_ok) echo "✅ Courses: %s" ;;  uk:predmety_ok) echo "✅ Предмети: %s" ;;
    cs:predmety_chyba) echo "Některé předměty se nepodařilo založit (ostatní ano). Opravit je můžeš v Obsidianu: Nastavení → Druhý mozek → Předměty.

%s" ;;
    sk:predmety_chyba) echo "Niektoré predmety sa nepodarilo založiť (ostatné áno). Opraviť ich môžeš v Obsidiane: Nastavenia → Druhý mozek → Predmety.

%s" ;;
    en:predmety_chyba) echo "Some courses couldn't be created (the others were). You can fix them in Obsidian: Settings → Druhý mozek → Courses.

%s" ;;
    uk:predmety_chyba) echo "Деякі предмети не вдалося створити (інші – так). Виправити їх можна в Obsidian: Налаштування → Druhý mozek → Предмети.

%s" ;;
    cs:jazyk_word) echo "V jakém jazyce budeš psát práce ve Wordu? (nadpisy a předvyplněné texty v šabloně – změníš i později v Obsidianu)" ;;
    sk:jazyk_word) echo "V akom jazyku budeš písať práce vo Worde? (nadpisy a predvyplnené texty v šablóne – zmeníš aj neskôr v Obsidiane)" ;;
    en:jazyk_word) echo "In which language will you write your Word documents? (headings and pre-filled texts in the template – can be changed later in Obsidian)" ;;
    uk:jazyk_word) echo "Якою мовою писатимеш роботи у Word? (заголовки й заповнені тексти шаблону – можна змінити пізніше в Obsidian)" ;;
    cs:ai) echo "Jak chceš pracovat s AI? (kdykoli změníš v Obsidianu: Nastavení → Druhý mozek)

• Claude Code – nejlepší výsledky, platí bezpečnostní pravidla systému (potřeba předplatné Claude)
• Jiná AI – Gemini CLI, Codex nebo vlastní program v Terminálu
• Bez AI – vše ručně ze šablon, nic se nikam neposílá" ;;
    sk:ai) echo "Ako chceš pracovať s AI? (kedykoľvek zmeníš v Obsidiane: Nastavenia → Druhý mozek)

• Claude Code – najlepšie výsledky, platia bezpečnostné pravidlá systému (potrebné predplatné Claude)
• Iná AI – Gemini CLI, Codex alebo vlastný program v Termináli
• Bez AI – všetko ručne zo šablón, nič sa nikam neposiela" ;;
    en:ai) echo "How do you want to work with AI? (change any time in Obsidian: Settings → Druhý mozek)

• Claude Code – best results, the system's security rules apply (needs a Claude subscription)
• Another AI – Gemini CLI, Codex or your own program in Terminal
• No AI – everything by hand from templates, nothing is sent anywhere" ;;
    uk:ai) echo "Як працювати зі ШІ? (можна змінити будь-коли в Obsidian: Налаштування → Druhý mozek)

• Claude Code – найкращі результати, діють правила безпеки системи (потрібна передплата Claude)
• Інший ШІ – Gemini CLI, Codex або власна програма в Терміналі
• Без ШІ – усе вручну із шаблонів, нічого не надсилається" ;;
    cs:ai_claude) echo "Claude Code (doporučeno)" ;;  sk:ai_claude) echo "Claude Code (odporúčané)" ;;
    en:ai_claude) echo "Claude Code (recommended)" ;;  uk:ai_claude) echo "Claude Code (рекомендовано)" ;;
    cs:ai_jina) echo "Jiná AI v Terminálu" ;;  sk:ai_jina) echo "Iná AI v Termináli" ;;  en:ai_jina) echo "Another AI in Terminal" ;;  uk:ai_jina) echo "Інший ШІ в Терміналі" ;;
    cs:ai_zadna) echo "Bez AI – vše ručně" ;;  sk:ai_zadna) echo "Bez AI – všetko ručne" ;;  en:ai_zadna) echo "No AI – everything by hand" ;;  uk:ai_zadna) echo "Без ШІ – усе вручну" ;;
    cs:ktera_ai) echo "Kterou AI používáš?" ;;  sk:ktera_ai) echo "Ktorú AI používaš?" ;;  en:ktera_ai) echo "Which AI do you use?" ;;  uk:ktera_ai) echo "Який ШІ ти використовуєш?" ;;
    cs:vlastni) echo "Vlastní příkaz" ;;  sk:vlastni) echo "Vlastný príkaz" ;;  en:vlastni) echo "Custom command" ;;  uk:vlastni) echo "Власна команда" ;;
    cs:prikaz) echo "Příkaz AI – na místo {prompt} se vloží zadání. Jen písmena, čísla, mezery a . _ / = : -" ;;
    sk:prikaz) echo "Príkaz AI – na miesto {prompt} sa vloží zadanie. Len písmená, číslice, medzery a . _ / = : -" ;;
    en:prikaz) echo "AI command – {prompt} is replaced by the task. Only letters, digits, spaces and . _ / = : -" ;;
    uk:prikaz) echo "Команда ШІ – замість {prompt} вставляється завдання. Лише літери, цифри, пробіли та . _ / = : -" ;;
    cs:prikaz_neplatny) echo "Příkaz AI je neplatný – nastavím „Bez AI“. Opravit ho můžeš později v Obsidianu: Nastavení → Druhý mozek." ;;
    sk:prikaz_neplatny) echo "Príkaz AI je neplatný – nastavím „Bez AI“. Opraviť ho môžeš neskôr v Obsidiane: Nastavenia → Druhý mozek." ;;
    en:prikaz_neplatny) echo "The AI command is invalid – setting “No AI”. You can fix it later in Obsidian: Settings → Druhý mozek." ;;
    uk:prikaz_neplatny) echo "Команда ШІ недійсна – буде встановлено «Без ШІ». Виправити можна пізніше в Obsidian: Налаштування → Druhý mozek." ;;
    cs:jina_varovani) echo "⚠️ Bezpečnostní pravidla druhého mozku platí jen pro Claude Code. U jiné AI nech zapnuté potvrzování příkazů a nikdy nepoužívej režim bez potvrzování (např. --yolo)." ;;
    sk:jina_varovani) echo "⚠️ Bezpečnostné pravidlá druhého mozgu platia len pre Claude Code. Pri inej AI nechaj zapnuté potvrdzovanie príkazov a nikdy nepoužívaj režim bez potvrdzovania (napr. --yolo)." ;;
    en:jina_varovani) echo "⚠️ Second Brain's security rules apply only to Claude Code. With another AI keep command confirmation on and never use a no-confirmation mode (e.g. --yolo)." ;;
    uk:jina_varovani) echo "⚠️ Правила безпеки «другого мозку» діють лише для Claude Code. В іншому ШІ залиш увімкнене підтвердження команд і ніколи не використовуй режим без підтвердження (напр. --yolo)." ;;
    cs:claude_chybi) echo "Claude Code zatím nemáš nainstalovaný.

Nainstaluj ho podle https://claude.com/claude-code a klikni „Hotovo – pokračovat“ – nebo pokračuj bez něj (tlačítka s AI začnou fungovat po instalaci)." ;;
    sk:claude_chybi) echo "Claude Code zatiaľ nemáš nainštalovaný.

Nainštaluj ho podľa https://claude.com/claude-code a klikni „Hotovo – pokračovať“ – alebo pokračuj bez neho (tlačidlá s AI začnú fungovať po inštalácii)." ;;
    en:claude_chybi) echo "Claude Code isn't installed yet.

Install it from https://claude.com/claude-code and click “Done – continue” – or continue without it (AI buttons will work after installation)." ;;
    uk:claude_chybi) echo "Claude Code ще не встановлено.

Встанови його за https://claude.com/claude-code і натисни «Готово – продовжити» – або продовжуй без нього (кнопки зі ШІ запрацюють після встановлення)." ;;
    cs:jina_info) echo "ℹ️  Program „%s“ zatím není nainstalovaný – tlačítka s AI začnou fungovat po jeho instalaci." ;;
    sk:jina_info) echo "ℹ️  Program „%s“ zatiaľ nie je nainštalovaný – tlačidlá s AI začnú fungovať po jeho inštalácii." ;;
    en:jina_info) echo "ℹ️  The program “%s” isn't installed yet – AI buttons will work after you install it." ;;
    uk:jina_info) echo "ℹ️  Програму «%s» ще не встановлено – кнопки зі ШІ запрацюють після її встановлення." ;;
    cs:rezim_ai) echo "✅ Režim AI: %s" ;;  sk:rezim_ai) echo "✅ Režim AI: %s" ;;  en:rezim_ai) echo "✅ AI mode: %s" ;;  uk:rezim_ai) echo "✅ Режим ШІ: %s" ;;
    cs:zavri_obsidian) echo "Zavři prosím Obsidian (Cmd+Q) a pak klikni OK – jinak by si nastavení mohl přepsat." ;;
    sk:zavri_obsidian) echo "Zavri prosím Obsidian (Cmd+Q) a potom klikni OK – inak by si nastavenia mohol prepísať." ;;
    en:zavri_obsidian) echo "Please quit Obsidian (Cmd+Q) and then click OK – otherwise it might overwrite the settings." ;;
    uk:zavri_obsidian) echo "Будь ласка, закрий Obsidian (Cmd+Q) і натисни OK – інакше він може перезаписати налаштування." ;;
    cs:zkopirovano) echo "✅ Soubory zkopírovány do: %s" ;;  sk:zkopirovano) echo "✅ Súbory skopírované do: %s" ;;
    en:zkopirovano) echo "✅ Files copied to: %s" ;;  uk:zkopirovano) echo "✅ Файли скопійовано до: %s" ;;
    cs:zapnuto) echo "✅ Rozšíření zapnuto, osobní nastavení uloženo (_Systém/nastaveni.json – zůstává jen u tebe)" ;;
    sk:zapnuto) echo "✅ Rozšírenie zapnuté, osobné nastavenia uložené (_Systém/nastaveni.json – zostávajú len u teba)" ;;
    en:zapnuto) echo "✅ Plugin enabled, personal settings saved (_Systém/nastaveni.json – stays only with you)" ;;
    uk:zapnuto) echo "✅ Розширення ввімкнено, особисті налаштування збережено (_Systém/nastaveni.json – лише у тебе)" ;;
    cs:logo) echo "Chceš v záhlaví prací logo fakulty?

Logo MU není součástí instalace (ochranná známka). Pokud ho máš jako PNG, vyber ho – jinak bude záhlaví jen textové." ;;
    sk:logo) echo "Chceš v hlavičke prác logo fakulty?

Logo MU nie je súčasťou inštalácie (ochranná známka). Ak ho máš ako PNG, vyber ho – inak bude hlavička len textová." ;;
    en:logo) echo "Do you want the faculty logo in the header of your work?

The MU logo isn't included (it's a trademark). If you have it as a PNG, choose it – otherwise the header is text only." ;;
    uk:logo) echo "Додати логотип факультету в заголовок робіт?

Логотипу MU немає у встановленні (торговельна марка). Якщо маєш його у PNG, вибери – інакше заголовок буде лише текстовим." ;;
    cs:bez_loga) echo "Bez loga" ;;  sk:bez_loga) echo "Bez loga" ;;  en:bez_loga) echo "No logo" ;;  uk:bez_loga) echo "Без логотипа" ;;
    cs:vybrat_logo) echo "Vybrat logo" ;;  sk:vybrat_logo) echo "Vybrať logo" ;;  en:vybrat_logo) echo "Choose logo" ;;  uk:vybrat_logo) echo "Вибрати логотип" ;;
    cs:logo_vyber) echo "Vyber logo fakulty (PNG s průhledným pozadím):" ;;  sk:logo_vyber) echo "Vyber logo fakulty (PNG s priehľadným pozadím):" ;;
    en:logo_vyber) echo "Choose the faculty logo (PNG with a transparent background):" ;;  uk:logo_vyber) echo "Вибери логотип факультету (PNG з прозорим тлом):" ;;
    cs:logo_ok) echo "✅ Logo přidáno" ;;  sk:logo_ok) echo "✅ Logo pridané" ;;  en:logo_ok) echo "✅ Logo added" ;;  uk:logo_ok) echo "✅ Логотип додано" ;;
    cs:sablona_ok) echo "✅ Šablona Wordu vytvořena" ;;  sk:sablona_ok) echo "✅ Šablóna Wordu vytvorená" ;;
    en:sablona_ok) echo "✅ Word template created" ;;  uk:sablona_ok) echo "✅ Шаблон Word створено" ;;
    cs:fronta_ok) echo "✅ Fronta materiálů připravena" ;;  sk:fronta_ok) echo "✅ Front materiálov pripravený" ;;
    en:fronta_ok) echo "✅ Material queue ready" ;;  uk:fronta_ok) echo "✅ Черга матеріалів готова" ;;
    cs:hotovo) echo "🎉 Hotovo! Cesta k trezoru je ve schránce: %s" ;;  sk:hotovo) echo "🎉 Hotovo! Cesta k trezoru je v schránke: %s" ;;
    en:hotovo) echo "🎉 Done! The vault path is on the clipboard: %s" ;;  uk:hotovo) echo "🎉 Готово! Шлях до сховища скопійовано: %s" ;;
    cs:hotovo_okno) echo "Hotovo! 🎉 Teď v Obsidianu:

1. Otevři trezor: v okně se seznamem trezorů klikni na „Otevřít“ u „Otevřít složku jako trezor“ a vyber:
%s
(cesta je ve schránce – v okně výběru dej Cmd+Shift+G a Cmd+V)

2. Obsidian se zeptá, jestli trezoru důvěřuješ → „Důvěřovat autorovi a povolit pluginy“.

3. Otevři „00 Domov“ a klikni na 🩺 Zkontrolovat propojení.

Volitelně si v Nastavení → Pluginy třetích stran → Procházet nainstaluj „Neuro Roadmap“ (plánování) a „Spaced Repetition“ (kartičky).
AI, jazyk a místo zálohy změníš kdykoli: Nastavení → Druhý mozek. Automatická záloha se zapne sama.
Návod k používání: poznámka „01 Návod“." ;;
    sk:hotovo_okno) echo "Hotovo! 🎉 Teraz v Obsidiane:

1. Otvor trezor: v okne so zoznamom trezorov klikni na „Otvoriť“ pri „Otvoriť priečinok ako trezor“ a vyber:
%s
(cesta je v schránke – v okne výberu daj Cmd+Shift+G a Cmd+V)

2. Obsidian sa opýta, či trezoru dôveruješ → „Dôverovať autorovi a povoliť pluginy“.

3. Otvor „00 Domov“ a klikni na 🩺 Skontrolovať systém.

Voliteľne si v Nastaveniach → Pluginy tretích strán → Prehľadávať nainštaluj „Neuro Roadmap“ (plánovanie) a „Spaced Repetition“ (kartičky).
AI, jazyk a miesto zálohy zmeníš kedykoľvek: Nastavenia → Druhý mozek. Automatická záloha sa zapne sama.
Návod na používanie: poznámka „01 Návod“." ;;
    en:hotovo_okno) echo "Done! 🎉 Now in Obsidian:

1. Open the vault: in the vault list window click “Open” next to “Open folder as vault” and choose:
%s
(the path is on the clipboard – in the picker press Cmd+Shift+G and Cmd+V)

2. Obsidian asks whether you trust the vault → “Trust author and enable plugins”.

3. Open “00 Domov” (Home) and click 🩺 Run system check.

Optionally install “Neuro Roadmap” (planning) and “Spaced Repetition” (flashcards) in Settings → Community plugins → Browse.
Change AI, language and backup location any time: Settings → Druhý mozek. Automatic backup turns on by itself.
User guide: the “01 Návod” note." ;;
    uk:hotovo_okno) echo "Готово! 🎉 Тепер в Obsidian:

1. Відкрий сховище: у вікні зі списком сховищ натисни «Відкрити» біля «Відкрити папку як сховище» й вибери:
%s
(шлях у буфері обміну – у вікні вибору натисни Cmd+Shift+G і Cmd+V)

2. Obsidian запитає, чи довіряєш сховищу → «Довіряти автору й увімкнути плагіни».

3. Відкрий «00 Domov» (Головна) і натисни 🩺 Перевірити систему.

За бажання встанови в Налаштування → Сторонні плагіни → Огляд «Neuro Roadmap» (планування) та «Spaced Repetition» (картки).
ШІ, мову й місце резервних копій змінюй будь-коли: Налаштування → Druhý mozek. Автоматичне резервне копіювання ввімкнеться саме.
Посібник: нотатка «01 Návod»." ;;
  esac
}
t() { local s; s="$(_t "$JAZYK" "$1")"; [[ -n "$s" ]] || s="$(_t cs "$1")"; echo "$s"; }
tf() { local f; f="$(t "$1")"; shift; printf "$f" "$@"; }  # text s %s
krok_nazev() { t kroky | cut -d'|' -f$(( $1 + 1 )); }

zrusit() { echo; t prerusena; exit 0; }

# ── dialogy (v testovacím režimu DM_TEST se odpovědi berou z proměnných DM_*) ──
okno_text() {   # $1 otázka, $2 výchozí odpověď, $3 proměnná pro test
  local test="${3:-}"; if [[ -n "$test" && -n "${!test:-}" ]]; then echo "${!test}"; return; fi
  osascript - "$1" "$2" "$(t nazev)" "$(t prerusit)" "$(t pokracovat)" <<'AS' 2>/dev/null || zrusit
on run argv
  set r to display dialog (item 1 of argv) default answer (item 2 of argv) with title (item 3 of argv) buttons {item 4 of argv, item 5 of argv} default button 2 cancel button 1
  return text returned of r
end run
AS
}
okno_volba() {  # $1 text, $2 tlačítko A, $3 tlačítko B (výchozí), $4 proměnná pro test
  local test="${4:-}"; if [[ -n "$test" && -n "${!test:-}" ]]; then echo "${!test}"; return; fi
  osascript - "$1" "$2" "$3" "$(t nazev)" "$(t prerusit)" <<'AS' 2>/dev/null || zrusit
on run argv
  set r to display dialog (item 1 of argv) with title (item 4 of argv) buttons {item 5 of argv, item 2 of argv, item 3 of argv} default button 3 cancel button 1
  return button returned of r
end run
AS
}
okno_info() {
  [[ -n "${DM_TEST:-}" ]] && { echo "ℹ️  $1"; return; }
  osascript - "$1" "$(t nazev)" <<'AS' >/dev/null 2>&1 || true
on run argv
  display dialog (item 1 of argv) with title (item 2 of argv) buttons {"OK"} default button 1
end run
AS
}
okno_seznam() { # $1 výzva, $2 proměnná pro test, další argumenty = položky (v testu bez odpovědi = první položka)
  local vyzva="$1" test="$2"; shift 2
  if [[ -n "$test" && -n "${!test:-}" ]]; then echo "${!test}"; return; fi
  if [[ -n "${DM_TEST:-}" ]]; then echo "$1"; return; fi
  osascript - "$vyzva" "$(t nazev)" "$(t pokracovat)" "$(t prerusit)" "$@" <<'AS' 2>/dev/null || zrusit
on run argv
  set polozky to items 5 thru -1 of argv
  set r to choose from list polozky with prompt (item 1 of argv) with title (item 2 of argv) default items {item 1 of polozky} OK button name (item 3 of argv) cancel button name (item 4 of argv)
  if r is false then error number -128
  return item 1 of r
end run
AS
}
vyber_slozku() { # $1 výzva, $2 proměnná pro test
  local test="${2:-}"; if [[ -n "$test" && -n "${!test:-}" ]]; then echo "${!test}"; return; fi
  osascript - "$1" <<'AS' 2>/dev/null || zrusit
on run argv
  return POSIX path of (choose folder with prompt (item 1 of argv) default location (path to documents folder))
end run
AS
}
vyber_png() {
  if [[ -n "${DM_TEST:-}" ]]; then echo "${DM_LOGO:-}"; return; fi
  osascript - "$(t logo_vyber)" <<'AS' 2>/dev/null || true
on run argv
  return POSIX path of (choose file with prompt (item 1 of argv) of type {"public.png"})
end run
AS
}
otevri_web() { [[ -z "${DM_TEST:-}" ]] && open "$1" 2>/dev/null || true; }
kod_jazyka() {  # název nebo kód jazyka → kód
  case "$1" in sk|Slovenčina) echo sk ;; en|English) echo en ;; uk|Українська) echo uk ;; *) echo cs ;; esac
}

# ── uložený postup: jen povolené klíče, nic se nespouští ──
KROK=0; REZIM=""; CIL=""; JMENO=""; UCO=""; JMENO_SOUBOR=""; AI="claude"; AI_PRIKAZ=""; JAZYK_WORD=""; PREDMETY=""
uloz_postup() {
  KROK="$1"
  { for k in KROK REZIM CIL JMENO UCO JMENO_SOUBOR AI AI_PRIKAZ JAZYK JAZYK_WORD PREDMETY; do printf '%s\t%s\n' "$k" "${!k}"; done; } > "$POSTUP"
  chmod 600 "$POSTUP" 2>/dev/null || true
}
nacti_postup() {
  while IFS=$'\t' read -r k v; do
    case "$k" in KROK|REZIM|CIL|JMENO|UCO|JMENO_SOUBOR|AI|AI_PRIKAZ|JAZYK|JAZYK_WORD|PREDMETY) printf -v "$k" '%s' "$v" ;; esac
  done < "$POSTUP"
  [[ "$KROK" =~ ^[0-6]$ ]] || KROK=0
  JAZYK="$(kod_jazyka "$JAZYK")"
  [[ -z "$JAZYK_WORD" ]] || JAZYK_WORD="$(kod_jazyka "$JAZYK_WORD")"
  case "$REZIM" in novy|"Nový trezor") REZIM="novy" ;; aktualizace) ;; *) REZIM="existujici" ;; esac
}

echo "🧠 Druhý mozek pro KISK"
echo

# ── rozdělaná instalace? ──
if [[ -f "$POSTUP" ]]; then
  nacti_postup
  if (( KROK > 0 )); then
    DALSI=$((KROK + 1))
    TEXT="$(tf rozdelana "$KROK" "$(krok_nazev "$KROK")" "$DALSI" "$(krok_nazev "$DALSI")")${CIL:+

$(t trezor): $CIL}"
    VOLBA=$(okno_volba "$TEXT" "$(t zacit_znovu)" "$(tf pokracovat_od "$DALSI")" DM_POKRACOVANI)
    if [[ "$VOLBA" == "$(t zacit_znovu)" || "$VOLBA" == "znovu" ]]; then
      KROK=0; REZIM=""; CIL=""; JMENO=""; UCO=""; JMENO_SOUBOR=""; AI="claude"; AI_PRIKAZ=""; JAZYK_WORD=""; PREDMETY=""
    fi
  fi
fi

# ── 0) jazyk (první okno je vícejazyčné) ──
if (( KROK < 1 )); then
  JAZYK="$(kod_jazyka "$(okno_seznam "Jazyk · Jazyk · Language · Мова" DM_JAZYK "Čeština" "Slovenčina" "English" "Українська")")"
fi

# ── 1) ověření souborů a požadavků ──
if (( KROK < 1 )); then
  if [[ -f SHA256SUMS.txt ]] && ! shasum -a 256 -c --quiet SHA256SUMS.txt >/dev/null 2>&1; then
    okno_info "$(t soucty_chyba)"
    exit 1
  fi
  t soucty_ok

  until python3 --version >/dev/null 2>&1; do
    V=$(okno_volba "$(t python_chybi)" "$(t otevrit_web)" "$(t hotovo_pokracovat)" DM_VOLBA_PYTHON)
    [[ "$V" == "$(t otevrit_web)" ]] && otevri_web "https://www.python.org/downloads/"
    [[ -n "${DM_TEST:-}" ]] && break
  done
  echo "✅ Python: $(python3 --version 2>&1)"

  while [[ ! -d "/Applications/Obsidian.app" && -z "${DM_TEST:-}" ]]; do
    V=$(okno_volba "$(t obsidian_chybi)" "$(t pokracovat_bez)" "$(t zkontrolovat_znovu)")
    [[ "$V" == "$(t pokracovat_bez)" ]] && break
    otevri_web "https://obsidian.md/download"
    okno_info "$(t obsidian_az)"
  done
  [[ -d "/Applications/Microsoft Word.app" ]] || t word_chybi
  uloz_postup 1
fi

# ── 2) kam instalovat ──
if (( KROK < 2 )); then
  VOLBA=$(okno_seznam "$(t kam)" DM_REZIM "$(t novy)" "$(t existujici)" "$(t aktualizace)")
  if [[ "$VOLBA" == "aktualizace" || "$VOLBA" == "$(t aktualizace)" ]]; then
    REZIM="aktualizace"
    CIL=$(vyber_slozku "$(t vyber_aktualizace)" DM_CIL)
    CIL="${CIL%/}"
    [[ -f "$CIL/_Systém/nastaveni.json" ]] || { okno_info "$(t neni_instalace)"; exit 1; }
  elif [[ "$VOLBA" == "novy" || "$VOLBA" == "$(t novy)" || "$VOLBA" == "Nový trezor" ]]; then
    REZIM="novy"
    RODIC=$(vyber_slozku "$(t vyber_kde)" DM_RODIC)
    JMENO_TREZORU=$(okno_text "$(t jak_nazev)" "$(t vychozi_nazev)" DM_NAZEV_TREZORU)
    CIL="${RODIC%/}/$JMENO_TREZORU"
    if [[ -d "$CIL" && -n "$(ls -A "$CIL" 2>/dev/null)" ]]; then
      okno_info "$(tf neprazdna "$CIL")"
      exit 1
    fi
  else
    REZIM="existujici"
    CIL=$(vyber_slozku "$(t vyber_existujici)" DM_CIL)
    CIL="${CIL%/}"
    [[ -d "$CIL/.obsidian" ]] || okno_info "$(t neni_trezor)"
  fi
  uloz_postup 2
fi

# ── 3) osobní údaje, jazyk Wordu, AI (při aktualizaci se přeskočí – údaje už jsou v nastaveni.json) ──
if (( KROK < 3 )) && [[ "$REZIM" != "aktualizace" ]]; then
  JMENO=$(okno_text "$(t jmeno)" "$JMENO" DM_JMENO)
  [[ -n "$JMENO" ]] || { okno_info "$(t jmeno_chybi)"; exit 1; }
  UCO=$(okno_text "$(t uco)" "$UCO" DM_UCO)
  [[ "$UCO" =~ ^[0-9]{4,7}$ ]] || { okno_info "$(t uco_chyba)"; exit 1; }
  PRIJMENI="${JMENO##* }"; JMENA="${JMENO% *}"; [[ "$PRIJMENI" == "$JMENO" ]] && JMENA=""
  JMENO_SOUBOR=$(okno_text "$(t jmeno_soubor)" "$PRIJMENI${JMENA:+ $JMENA}" DM_JMENO_SOUBOR)

  # předměty: kolik kdo má – po jednom, prázdné pole = hotovo (v testu jako DM_PREDMETY="KÓD Název;KÓD Název")
  if [[ -n "${DM_TEST:-}" ]]; then
    PREDMETY="${DM_PREDMETY:-}"
  else
    PREDMETY=""
    for (( i = 1; i <= 40; i++ )); do
      P=$(okno_text "$(tf predmet_dotaz "$i")" "" "")
      P="${P//;/,}"; P="${P//$'\t'/ }"
      [[ -z "${P// /}" ]] && break
      PREDMETY="${PREDMETY:+$PREDMETY;}$P"
    done
  fi

  # jazyk dokumentů ve Wordu se volí jednou dopředu; v seznamu je první jazyk rozhraní
  case "$JAZYK" in
    sk) POLOZKY=("Slovenčina" "Čeština" "English" "Українська") ;;
    en) POLOZKY=("English" "Čeština" "Slovenčina" "Українська") ;;
    uk) POLOZKY=("Українська" "English" "Čeština" "Slovenčina") ;;
    *)  POLOZKY=("Čeština" "Slovenčina" "English" "Українська") ;;
  esac
  JAZYK_WORD="$(kod_jazyka "$(okno_seznam "$(t jazyk_word)" DM_JAZYK_WORD "${POLOZKY[@]}")")"

  VOLBA_AI=$(okno_seznam "$(t ai)" DM_AI "$(t ai_claude)" "$(t ai_jina)" "$(t ai_zadna)")
  if [[ "$VOLBA_AI" == "claude" || "$VOLBA_AI" == "$(t ai_claude)" ]]; then AI="claude"; AI_PRIKAZ=""
  elif [[ "$VOLBA_AI" == "zadna" || "$VOLBA_AI" == "$(t ai_zadna)" ]]; then AI="zadna"; AI_PRIKAZ=""
  else
    AI="jina"
    PRESET=$(okno_seznam "$(t ktera_ai)" DM_AI_PRESET "Gemini CLI" "OpenAI Codex CLI" "$(t vlastni)")
    case "$PRESET" in
      Gemini*) AI_PRIKAZ="gemini -i {prompt}" ;;
      OpenAI*) AI_PRIKAZ="codex {prompt}" ;;
      *)       AI_PRIKAZ=$(okno_text "$(t prikaz)" "program {prompt}" DM_AI_PRIKAZ) ;;
    esac
    if [[ ! "$AI_PRIKAZ" =~ ^[A-Za-z0-9\ _./=:-]*\{prompt\}[A-Za-z0-9\ _./=:-]*$ ]]; then
      okno_info "$(t prikaz_neplatny)"
      AI="zadna"; AI_PRIKAZ=""
    else
      okno_info "$(t jina_varovani)"
    fi
  fi
  if [[ "$AI" == "claude" ]]; then
    until command -v claude >/dev/null 2>&1 || [[ -x "$HOME/.local/bin/claude" || -x /opt/homebrew/bin/claude || -x /usr/local/bin/claude ]]; do
      V=$(okno_volba "$(t claude_chybi)" "$(t pokracovat_bez)" "$(t hotovo_pokracovat)" DM_VOLBA_CLAUDE)
      [[ "$V" == "$(t pokracovat_bez)" || "$V" == "bez" ]] && break
      otevri_web "https://claude.com/claude-code"
    done
  elif [[ "$AI" == "jina" ]] && ! command -v "${AI_PRIKAZ%% *}" >/dev/null 2>&1; then
    tf jina_info "${AI_PRIKAZ%% *}"; echo
  fi
  tf rezim_ai "$AI${AI_PRIKAZ:+ ($AI_PRIKAZ)}"; echo
  uloz_postup 3
fi

# ── 4) kopírování (nic existujícího se nepřepíše): nejdřív poznámky ve zvoleném jazyce, pak zbytek systému ──
AKT_SHRNUTI=""; AKT_PONECHANO=""
if (( KROK < 4 )); then
  if [[ "$REZIM" != "novy" ]] && pgrep -x Obsidian >/dev/null 2>&1 && [[ -z "${DM_TEST:-}" ]]; then
    okno_info "$(t zavri_obsidian)"
  fi
fi
if (( KROK < 4 )) && [[ "$REZIM" == "aktualizace" ]]; then
  if ! VYSLEDEK=$(python3 "$PWD/nastroje/aktualizace.py" --cil "$CIL" --pro-instalator 2>&1); then
    okno_info "$(tf akt_chyba "$VYSLEDEK")"
    exit 1
  fi
  AKT_SHRNUTI=$(printf '%s\n' "$VYSLEDEK" | head -1)
  AKT_PONECHANO=$(printf '%s\n' "$VYSLEDEK" | tail -n +2)
  tf akt_ok "$AKT_SHRNUTI"; echo
  [[ -n "$AKT_PONECHANO" ]] && { t akt_ponechano; echo "$AKT_PONECHANO"; }
  uloz_postup 4
fi
if (( KROK < 4 )) && [[ "$REZIM" != "aktualizace" ]]; then
  mkdir -p "$CIL"
  DM_BALICEK="$ZDROJ/_Systém/jazyky/$JAZYK.json" DM_CIL_ABS="$CIL" DM_BEZ_UKAZKY="${PREDMETY:+1}" python3 - <<'PY'
import json, os
balicek = json.load(open(os.environ["DM_BALICEK"], encoding="utf8"))
cil = os.path.realpath(os.environ["DM_CIL_ABS"])
for rel, obsah in balicek["soubory"].items():
    p = os.path.realpath(os.path.join(cil, rel))
    if os.path.isabs(rel) or ".." in rel.split("/") or not p.startswith(cil + os.sep):
        continue
    if os.environ.get("DM_BEZ_UKAZKY") and rel.startswith("Příklad předmětu/"):
        continue
    if not os.path.exists(p):  # existující soubory se nepřepisují
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf8") as f:
            f.write(obsah)
PY
  BEZ_UKAZKY=(); [[ -n "$PREDMETY" ]] && BEZ_UKAZKY=(--exclude 'Příklad předmětu/')
  rsync -a --ignore-existing --exclude '.DS_Store' ${BEZ_UKAZKY[@]+"${BEZ_UKAZKY[@]}"} "$ZDROJ/" "$CIL/"
  tf zkopirovano "$CIL"; echo
  uloz_postup 4
fi

# ── 5) zapnutí rozšíření, osobní nastavení, logo, šablona Wordu, fronta ──
if (( KROK < 5 )); then
  DM_CIL_ABS="$CIL" DM_JMENO="$JMENO" DM_UCO="$UCO" DM_JS="$JMENO_SOUBOR" DM_AI_REZIM="$AI" DM_AI_CMD="$AI_PRIKAZ" \
  DM_JAZ="$JAZYK" DM_JAZ_WORD="${JAZYK_WORD:-$JAZYK}" DM_REZIM_INST="$REZIM" python3 - <<'PY'
import json, os
cil = os.environ["DM_CIL_ABS"]; o = os.path.join(cil, ".obsidian")
def nacti(n, vychozi):
    try:
        return json.load(open(os.path.join(o, n)))
    except Exception:
        return vychozi
def uloz(n, d):
    json.dump(d, open(os.path.join(o, n), "w"), ensure_ascii=False, indent=2)
cp = nacti("community-plugins.json", [])
if "druhy-mozek" not in cp: cp.append("druhy-mozek")
uloz("community-plugins.json", cp)
ap = nacti("appearance.json", {})
ap.setdefault("enabledCssSnippets", [])
for snippet in ("druhy-mozek", "druhy-mozek-predmety"):
    if snippet not in ap["enabledCssSnippets"]: ap["enabledCssSnippets"].append(snippet)
uloz("appearance.json", ap)
core = nacti("core-plugins.json", {})
if isinstance(core, dict):
    for k in ("bases", "templates", "properties", "canvas"): core[k] = True
    uloz("core-plugins.json", core)
tp = nacti("templates.json", {})
tp.setdefault("folder", "_Systém/Šablony"); tp.setdefault("dateFormat", "YYYY-MM-DD")
uloz("templates.json", tp)
if os.environ["DM_REZIM_INST"] != "aktualizace":
  json.dump({"jmeno": os.environ["DM_JMENO"], "jmeno_soubor": os.environ["DM_JS"], "uco": os.environ["DM_UCO"],
           "ai": os.environ["DM_AI_REZIM"], "ai_prikaz": os.environ["DM_AI_CMD"],
           "jazyk": os.environ["DM_JAZ"], "jazyk_word": os.environ["DM_JAZ_WORD"]},
          open(os.path.join(cil, "_Systém", "nastaveni.json"), "w"), ensure_ascii=False, indent=2)
PY
  t zapnuto

  LOGO_VOLBA="bez"
  [[ "$REZIM" == "aktualizace" ]] || LOGO_VOLBA=$(okno_volba "$(t logo)" "$(t bez_loga)" "$(t vybrat_logo)" DM_LOGO_VOLBA)
  if [[ "$LOGO_VOLBA" == "$(t vybrat_logo)" || "$LOGO_VOLBA" == "logo" ]]; then
    LOGO=$(vyber_png)
    [[ -n "$LOGO" && -f "$LOGO" ]] && cp "$LOGO" "$CIL/_Systém/Word/logo-muni-arts.png" && t logo_ok
  fi
  python3 "$CIL/_Systém/Word/vytvor_sablonu.py" >/dev/null && t sablona_ok
  if [[ -n "$PREDMETY" && "$REZIM" != "aktualizace" ]]; then
    IFS=';' read -r -a POLE_PREDMETU <<< "$PREDMETY"
    if VYSTUP=$(python3 "$CIL/_Systém/predmety.py" --pridat "${POLE_PREDMETU[@]}" 2>&1); then
      tf predmety_ok "${#POLE_PREDMETU[@]}"; echo
    else
      okno_info "$(tf predmety_chyba "$VYSTUP")"
    fi
  else
    python3 "$CIL/_Systém/predmety.py" --css >/dev/null 2>&1 || true
  fi
  python3 "$CIL/_Systém/priprav.py" >/dev/null && t fronta_ok
  # evidence nainstalovaných souborů – podle ní příští aktualizace pozná, co sis upravil
  [[ "$REZIM" == "aktualizace" ]] || python3 "$PWD/nastroje/aktualizace.py" --cil "$CIL" --jen-zapis
  uloz_postup 5
fi

# ── 6) hotovo ──
rm -f "$POSTUP"
printf '%s' "$CIL" | pbcopy 2>/dev/null || true
echo
tf hotovo "$CIL"; echo
if [[ -z "${DM_TEST:-}" ]]; then
  open -R "$CIL" 2>/dev/null || true
  [[ -d "/Applications/Obsidian.app" ]] && open -a Obsidian 2>/dev/null || true
fi
if [[ "$REZIM" == "aktualizace" ]]; then
  okno_info "$(tf akt_hotovo_okno "$AKT_SHRNUTI" "${AKT_PONECHANO:+
$(t akt_ponechano)
$AKT_PONECHANO
}")"
else
  okno_info "$(tf hotovo_okno "$CIL")"
fi
