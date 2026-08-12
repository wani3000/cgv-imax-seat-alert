"""Read the owner's Toss identification fields from macOS Keychain.

This module deliberately has no command-line mode and never prints values.
Browser automation may import these functions only while filling Toss Pay.
"""

from __future__ import annotations

import subprocess


KEYCHAIN_ACCOUNT = "cgv-imax-seat-alert"
TOSS_PHONE_SERVICE = "cgv-imax-seat-alert.toss-phone"
TOSS_BIRTHDATE_SERVICE = "cgv-imax-seat-alert.toss-birthdate"


def _read_keychain(service: str) -> str:
    result = subprocess.run(
        [
            "/usr/bin/security",
            "find-generic-password",
            "-a",
            KEYCHAIN_ACCOUNT,
            "-s",
            service,
            "-w",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_toss_phone() -> str:
    value = _read_keychain(TOSS_PHONE_SERVICE)
    if not (value.isdigit() and 10 <= len(value) <= 11):
        raise ValueError("Invalid Toss phone number stored in Keychain")
    return value


def get_toss_birthdate() -> str:
    value = _read_keychain(TOSS_BIRTHDATE_SERVICE)
    if not (value.isdigit() and len(value) == 6):
        raise ValueError("Invalid Toss birthdate stored in Keychain")
    return value

