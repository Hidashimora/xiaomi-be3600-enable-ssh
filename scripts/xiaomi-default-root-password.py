#!/usr/bin/env python3
"""Derive the default root password of a Xiaomi router from its serial number.

Background
----------
On first boot the stock firmware runs ``mkxqimage -I``, which reads ``nvram get SN``
and writes an 8-character password into ``/etc/shadow`` for the ``root`` account.
The algorithm is the first 8 hex characters of ``MD5(SN + salt)``, where the salt is
built from a GUID string found inside ``/bin/mkxqimage``:

    string in firmware : d44fb0960aa0-a5e6-4a30-250f-6d2df50a
    salt actually used : 6d2df50a-250f-4a30-a5e6-d44fb0960aa0   (dash parts reversed)
    password           : md5(SN + salt)[:8]

Verified on Xiaomi BE3600 Pro / BE3600 2.5G (RD15) stock firmware, and used by
xmir-patcher (``gateway.py``) for the same purpose.

The serial number keeps its slash, e.g. ``12345/A1B2C3D4E5F6``.

Security
--------
This is for recovering the root password of **your own** device. The serial number
derives the password directly, so treat the SN as a secret and change the root
password as soon as you log in.

Usage
-----
    python3 xiaomi-default-root-password.py 12345/A1B2C3D4E5F6
    python3 xiaomi-default-root-password.py --selftest

No third-party packages required.
"""

from __future__ import annotations

import hashlib
import sys

# The raw GUID string as it appears in the firmware's /bin/mkxqimage.
SALT_RAW = "d44fb0960aa0-a5e6-4a30-250f-6d2df50a"

# The salt that actually goes into the hash: dash-separated parts reversed.
SALT = "-".join(reversed(SALT_RAW.split("-")))

# Known-good samples (SN -> password). The SNs are fictional placeholders; the
# expected values were produced by running the firmware's own mkxqimage under QEMU.
SELFTEST = {
    "": "8a6b71bb",
    "a": "09c1df40",
    "b": "d5b672c8",
    "c": "5962111a",
    "aa": "1b24ec19",
    "ab": "c29bad13",
    "ba": "582df6b0",
    "0": "fc07eefb",
    "1": "49c5beb1",
    "01": "8757a5f5",
    "10": "99cbd03d",
    "12345/A1B2C3D4E5F6": "71499649",
    "12345/A1B2C3D4E5F7": "604ba36d",
    "12346/A1B2C3D4E5F6": "068cdd41",
}


def root_password(sn: str) -> str:
    """Return the 8-character factory root password for serial number *sn*."""
    return hashlib.md5((sn + SALT).encode("utf-8")).hexdigest()[:8]


def selftest() -> int:
    ok = 0
    print("Self-test against values produced by the firmware's own mkxqimage:\n")
    for sn, expected in SELFTEST.items():
        got = root_password(sn)
        good = got == expected
        ok += good
        print(f"  [{'OK ' if good else 'FAIL'}] SN={sn!r:22} expected={expected}  got={got}")
    print(f"\n  Result: {ok}/{len(SELFTEST)}")
    return 0 if ok == len(SELFTEST) else 1


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        print("Hint: the '/' is part of the serial number - do not drop it.")
        return 2

    if argv[0] in ("--selftest", "-t"):
        return selftest()

    sn = argv[0].strip()
    if "/" not in sn:
        print(f"[!] Warning: SN {sn!r} has no '/'; a full Xiaomi SN looks like 12345/A1B2C3D4E5F6.\n")

    print(f"SN       : {sn}")
    print("Username : root")
    print(f"Password : {root_password(sn)}")
    print()
    print("Log in with (dropbear 2017.75 only speaks ssh-rsa):")
    print("  ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa \\")
    print("      -o StrictHostKeyChecking=no root@192.168.31.1")
    print()
    print("If this password is rejected, set your own through the exploit instead:")
    print("  ... exploit_set_macfilter_rules.py --cmd \"printf 'NEW\\nNEW\\n' | passwd root\"")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
