# 🔒 Security and verification

<details>
<summary>🌐 <b>Language</b> · English</summary>

[Čeština](docs/SECURITY.cs.md) · [Slovenčina](docs/SECURITY.sk.md) · [Українська](docs/SECURITY.uk.md)

</details>

## How to verify the installation is OK

1. **Download only from this repository on GitHub** (Code → Download ZIP, or from [Releases](https://github.com/shadowsh1t/second-brain-kisk/releases)).
2. **A green tick ✅ next to the latest commit** means the automated check on a clean Mac on GitHub's servers
   passed: checksums, syntax, the installer (including resuming and protecting an existing vault), the Word template,
   the queue, conversion into the template, all four languages, rejection of forged documents and a check that the repository contains no personal data.
   The check uses no third-party actions – only `git` and files from the repository ([.github/workflows/kontrola.yml](.github/workflows/kontrola.yml)).
3. **Checksums:** in the unzipped folder run in Terminal
   ```bash
   shasum -a 256 -c SHA256SUMS.txt
   ```
   Every line must end with `OK`. The installer checks this itself and won't run if anything differs.
   To be sure, also compare the fingerprint of `SHA256SUMS.txt` itself with the one listed with the release in *Releases*:
   ```bash
   shasum -a 256 SHA256SUMS.txt
   ```
4. **Read the installer** – `Instalovat.command` is plain text (open it in TextEdit). At the beginning there is a list
   of everything it does.

## Why macOS warns when you run it

The installer isn't signed with an Apple Developer certificate (it costs $99 a year). That's why macOS says the first time
that the file can't be verified. Instead of Apple's signature, the checksums and the automated check above serve for verification.
How to run it is described in the [README](README.md#-installation-in-a-few-clicks).

## What the installer and the system DON'T do

- download nothing from the internet and send nothing (AI buttons send content only to the AI you chose, when you click them; once a day the plugin only asks GitHub for the latest version number; an update is downloaded only after you click *Download and install*),
- don't use `sudo` or administrator rights,
- don't overwrite existing files (copying with `--ignore-existing`),
- store personal data (name, UČO) only in `_Systém/nastaveni.json` in your vault.

## Protections in the system

- **AI permissions** (`trezor/.claude/settings.json`): without asking only two system scripts, `ls` and `date`;
  deleting, downloading, `sudo`, `ssh`, running arbitrary code (`python3 -c`, `bash -c`, `obsidian eval`…)
  and reading keys are forbidden; changes to settings and scripts and web access only with confirmation.
- **Prompt injection:** content of materials is data, not instructions for AI (rules in `trezor/.claude/CLAUDE.md`).
- **Integrity monitoring:** the plugin keeps fingerprints of scripts and rules; it won't act on unconfirmed changes. They can be confirmed
  only in an Obsidian window by retyping a random code – not by a command.
- **Automatic backup** copies only to the folder you choose; it may delete only its own backup folders
  (named by date) and always only after a new backup has been created successfully. Plugin data with keys is not backed up.
- **Document conversion** rejects zip bombs, links outside the document and unsupported embedded objects.
- **Language packs** are among the monitored files; when the language changes the plugin first makes a backup and writes only
  system notes inside the vault (paths with `..` are rejected). Your own notes and materials are not changed.
- **Updates** never start by themselves. The plugin only reads the latest version number from GitHub. After you click *Download and install*, it downloads only from this repository's Releases and verifies the ZIP checksum published with the release, the checksums of all files and the version; nothing changes until you click **Install**, and **Cancel installation** stops everything. Before installing, the vault is backed up; a failed installation reverts itself and **↩️ Undo the last update** is available for 7 days. Clicking Install confirms 🛡 only for files identical to the verified package. Notes, materials, `nastaveni.json` and files you have edited are never overwritten.

## Reporting a problem

Report a security problem **privately** – via [Security → Report a vulnerability](https://github.com/shadowsh1t/second-brain-kisk/security/advisories/new) in this repository, or by e-mail to `catty.skipping888@passinbox.com` with the subject `[SECURITY]` (not as a public Issue). Other bugs and ideas: **🐞 Report a bug or idea** right in Obsidian (technical details without personal data, you see everything before sending) or [Issues](https://github.com/shadowsh1t/second-brain-kisk/issues/new/choose) – in any of the four languages.
