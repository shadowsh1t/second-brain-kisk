# Changelog

All notable changes to Second Brain for KISK. The newest version is at the top.
When a new version is released, Obsidian offers it under **🆕 A new version of Second Brain is available** with a link to this list.

## 1.0.6 – 2026-10-18

- Fixed: courses whose names contain diacritics (e.g. *Úvod do knihovnictví*) now get the orange bar and the course code in the left panel too – before, only names without diacritics did, because macOS reports folder names in a different Unicode form than Obsidian uses.
- Fixed: a material with a line break in its name no longer breaks the queue on every following run.
- Fixed: a new assignment with control characters, a line break or a very long title (or such a UČO/name in the settings) now gets a clean, shortened Word file name instead of failing; a missing or invalid source document for conversion shows a clear message.
- Fixed: a citation with unusual characters, empty arguments of the overview script, an invalid number of days or file path in the queue script, and `nastaveni.json` that is not an object no longer crash the scripts – they show a message or carry on with default settings.

## 1.0.5 – 2026-10-18

- **Changing the language keeps your edits** – system notes you have edited (Home, guide, templates) stay and the translation is saved next to them with “(new version)”; Inbox, Concepts and Overviews with your own content are not touched. Replaced files are backed up to the hidden `.druhy-mozek-zaloha` folder first, even when automatic backup is off. Before, the language switch overwrote them.
- Security: a citation can no longer create a note outside `_Zdroje` (author and year are now cleaned up in the file name like the title).
- Fixed: a damaged or missing `nastaveni.json` no longer crashes the queue and overviews; the Word scripts say which setting is missing. A name containing `&` or `<` no longer breaks the Word template.
- README: new section *Who it's for – and who it isn't* (macOS only, no warranty, how bugs are handled, AI and sensitive materials).

## 1.0.4 – 2026-10-18

- The plugin no longer restarts itself (the Obsidian directory does not allow it). After changing the language, command names are translated right away. After an update or a revert, a notice asks you to restart Obsidian to load the new version.

## 1.0.3 – 2026-10-17

- **Smarter token saver** – the text prepared for the AI now includes slide titles as structure, **tables** from presentations and Word documents as Markdown tables, **chart data**, **speaker notes** and **links**. Slides and pages that are mostly a picture are marked, and their images are unpacked so the AI looks only at those.
- **Text recognition on your Mac** – text in scanned PDFs, photos and screenshots is recognised by macOS itself (free, no AI, no internet), so the AI reads cheap text instead of images. Materials still waiting in the queue are prepared again with the new extraction; processed ones stay as they are.
- **Queue** shows how many `/zpracuj` batches are waiting and the estimated tokens including writing the notes, with a tip to start each batch in a new session.
- **Guide**: new section *Saving your limits* (batches, a new session for every button, Sonnet is enough, why long chats are expensive) and optional Poppler for viewing scans as images.
- AI rules: scripts are always run with a relative path (no more permission prompts because of absolute paths or `| head`), the overview and course scripts are allowed, and the AI never installs other programs without explaining why and asking first.
- Fixed: after an update without restarting Obsidian, the plugin showed the old version number (in the update check, settings, diagnostics and bug reports).
- Fixed: notifications piled up when the plugin was reloaded.
- Bug report by e-mail now says that the recipient will see your e-mail address and offers GitHub instead.

## 1.0.2 – 2026-10-17

- The plugin is now called **Second Brain for KISK** in Obsidian (the directory only allows names without diacritics); settings are under *Settings → Second Brain for KISK*.
- Updates keep the Inbox, Concepts and Overviews hub notes untouched (you drop files there), and always refresh the dashboard tables (Obsidian reformats them itself) – no more “(new version)” copies of them.

## 1.0.1 – 2026-10-17

- **Available in the Obsidian plugin directory** – install *Second Brain for KISK* in Obsidian (Settings → Community plugins → Browse). On first start a setup guide asks for language, name, UČO, courses and AI mode and creates Home, the guide, templates and scripts in your vault. The directory version is updated by Obsidian; after an update it offers to refresh the files in your vault (edited notes stay).
- The GitHub installer and one-click updates keep working as before.
- Settings and dialogs follow Obsidian's plugin guidelines (headings, no inline styles).
- Guide: what to do when Claude Code asks you to `/login` again.

## 1.0.0 – 2026-10-17

First public release.

- **Obsidian plugin “Second Brain for KISK”** – buttons on Home, system check with alerts, integrity guard for code and AI rules, automatic backup (OneDrive, Google Drive, Dropbox, iCloud, external drive or any folder).
- **AI processing of course materials** – notes, mind maps and flashcards via Claude Code, another AI in Terminal, or everything by hand; local token saver.
- **Word assignments** in the MUNI ARTS style, and conversion of finished work into the template.
- **Courses** – enter as many as you have during installation, add or remove them later in Obsidian (removing moves the folder to the macOS Trash after confirmation).
- **Useful without AI too** – new note for a material, weekly overview, exam preparation, flashcard review, deadline reminders, deadlines to calendar (.ics), citations in ISO 690, archiving courses at the end of the semester, reading-time estimates in the queue.
- **Four languages** – Czech, Slovak, English and Ukrainian; the language of Word documents is chosen separately.
- **Updates in one click** – Obsidian checks once a day for a new version and offers what's new and *Download and install*; the plugin downloads and verifies the package and installs it after you click **Install** (or **Cancel installation**). Notes, materials and settings stay, edited system notes are kept (the new version is saved next to them), a failed installation reverts itself and **↩️ Undo the last update** is available for 7 days. Manual update with the installer works too.
- **Installer** with checksum verification and resume after installing prerequisites.
- Works with **Neuro Roadmap** by Matteo Rossi ([@phenex80](https://github.com/phenex80)) (optional).
- Licence: **PolyForm Noncommercial 1.0.0** – free for non-commercial use.
