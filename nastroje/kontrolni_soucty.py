#!/usr/bin/env python3
"""Kontrolní součty SHA-256 všech souborů repozitáře (SHA256SUMS.txt).

  python3 nastroje/kontrolni_soucty.py            # vytvoří / aktualizuje SHA256SUMS.txt (po každé změně)
  python3 nastroje/kontrolni_soucty.py --kontrola # ověří, že soubory odpovídají SHA256SUMS.txt

Ověření bez Pythonu (macOS/Linux):  shasum -a 256 -c SHA256SUMS.txt
"""
import hashlib
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOUCTY = REPO / "SHA256SUMS.txt"
VYNECHAT = {".git", "__pycache__", ".DS_Store", "SHA256SUMS.txt", ".instalace-postup"}


def soubory():
    for p in sorted(REPO.rglob("*")):
        rel = p.relative_to(REPO)
        if p.is_file() and not (set(rel.parts) & VYNECHAT):
            yield unicodedata.normalize("NFC", rel.as_posix()), p


def soucty():
    return {rel: hashlib.sha256(p.read_bytes()).hexdigest() for rel, p in soubory()}


if __name__ == "__main__":
    aktualni = soucty()
    if "--kontrola" in sys.argv:
        ulozene = {}
        for radek in SOUCTY.read_text(encoding="utf8").splitlines():
            h, rel = radek.split("  ", 1)
            ulozene[unicodedata.normalize("NFC", rel)] = h
        zmenene = [r for r in ulozene if aktualni.get(r) != ulozene[r]]
        nove = [r for r in aktualni if r not in ulozene]
        for r in zmenene:
            print("❌ nesouhlasí nebo chybí:", r)
        for r in nove:
            print("❌ není v SHA256SUMS.txt:", r)
        if zmenene or nove:
            sys.exit(1)
        print(f"✅ všech {len(ulozene)} souborů odpovídá SHA256SUMS.txt")
    else:
        SOUCTY.write_text("".join(f"{h}  {rel}\n" for rel, h in aktualni.items()), encoding="utf8")
        print(f"SHA256SUMS.txt: {len(aktualni)} souborů")
