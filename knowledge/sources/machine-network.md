# Wi-Fi, AdGuard DNS, and SSD TRIM

September 26, 2026. Your `throughput-performance` power profile and all snapshots/retention settings remain unchanged.

## Applied without administrator access

- Removed the inactive duplicate **Archer** profile (`ac4ba292-a894-4342-8a49-a6071a729046`). The working profile (`26f43e8c-7ebc-4ea4-812c-699bb60724b4`) remains active, with its password preserved. The relevant network identity settings matched before removal. No new profiles were created.
- Set **AdGuard's standard ad/tracker-blocking DNS**, not the family-protection variant, on all seven existing Wi-Fi/Ethernet profiles.
- Enabled authenticated DNS-over-TLS for those profiles, using `94.140.14.14#dns.adguard-dns.com` and `94.140.15.15#dns.adguard-dns.com`.
- Disabled automatically supplied DNS for both IPv4 and IPv6 on those profiles. IP addressing, routes, and IPv6 networking itself are unchanged.
- Applied DNS live without disconnecting Wi-Fi or restarting NetworkManager.
- Left VPN, loopback, Docker, and virtual-machine bridge configurations untouched.

Final uncached checks resolved `example.org` to both IPv4 and IPv6 addresses in about 204 ms, and returned AdGuard's blocked responses (`0.0.0.0` and `::`) for `doubleclick.net` in about 249 ms. Both reported encrypted/local transport, and the active link explicitly reported DNS-over-TLS with the named AdGuard servers. These are successful functional checks, not a controlled speed benchmark.

The router currently advertises an IPv6 default route, but the Wi-Fi interface has no global IPv6 address. Both AdGuard IPv6 TLS endpoints timed out in direct probes. IPv6 DNS servers were therefore removed from the final configuration to avoid that timeout path. DNS over IPv4 resolves both IPv4 and IPv6 host addresses. A future genuinely IPv6-only network would need reachable IPv6 DNS endpoints configured separately.

Global AdGuard DNS-over-TLS was already present before this work, but there was no global default routing domain, other profiles accepted automatic DNS, and the compiled-in non-AdGuard fallback list remained. The administrator step below completes the global default for future connections and removes that fallback list. More-specific VPN/private DNS routes and applications using their own secure DNS are not forcibly overridden; this is an operating-system resolver configuration, not a DNS-blocking firewall.

Provider addresses: [AdGuard public DNS documentation](https://adguard-dns.io/en/public-dns.html). Profile behavior: [NetworkManager settings](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html). Global routing: [systemd-resolved documentation](https://man.archlinux.org/man/systemd-resolved.8).

## What the Wi-Fi checks showed

- Intel Wireless-AC 9560 using `iwlwifi`; connected to Archer at 5 GHz, channel 149, 80 MHz width.
- Signal was approximately **−72 to −74 dBm** during inspection. This leaves less signal margin than a strong nearby connection, but did not demonstrate a broken driver.
- A short 12-packet router test had **0% loss**, approximately **2.25 ms average**, and **4.73 ms maximum** latency.
- A separate 12-packet Internet test had **0% loss**, approximately **40 ms average**, and a **133 ms spike**. These short tests do not isolate ISP congestion, game-server routing, or intermittent faults.
- The sampled kernel history showed a successful access-point change earlier in the session, not a firmware crash. Two access points advertising the same SSID are separate from duplicated *saved profiles*; deleting a saved duplicate does not remove physical access points.
- No band/BSSID lock, transmit-power change, driver reload, arbitrary module tweak, or Wi-Fi power-save change was made. The working connection remained associated throughout the DNS/profile changes.
- `wireless-regdb` is missing, and the kernel logged a missing regulatory database. The Intel radio nevertheless already reports a self-managed **PK** domain. Installing the database is sensible maintenance, not proof of a fix for an unspecified Wi-Fi symptom; no region was spoofed.

## Administrator-only step: SSD and global DNS

TRIM is **not enabled yet**. The SSD supports it, but the encrypted root mapping does not pass it through, and the weekly timer is disabled. These operations cannot be completed through this unprivileged app session.

Run this in your own terminal:

```sh
sudo python3 /home/user/Projects/machine-care/apply-admin-fixes.py --apply --install-regdb
```

The helper previews its plan and asks for confirmation. It may also request your disk-unlock passphrase; enter passwords only in your own terminal, never in chat. The optional regulatory database installation uses pacman's normal confirmation prompt.

It will:

1. Verify the real root mapping uses LUKS2 with no unexpected activation flags or integrity configuration. An unexpected setup stops for review.
2. Create a **root-only LUKS header backup** and action record under this folder.
3. Enable discard persistently through `cryptsetup refresh --allow-discards --persistent root`. This avoids modifying kernel command lines, rebuilding the boot image, or unmounting the live root filesystem. [Cryptsetup's refresh documentation](https://gitlab.com/cryptsetup/cryptsetup/-/blob/main/man/cryptsetup-refresh.8.adoc).
4. Enable the weekly `fstrim.timer` and run an initial trim of the Btrfs filesystem.
5. Install a separate resolved configuration drop-in that makes AdGuard the default DNS route, retains TLS, and clears the non-AdGuard fallback list. It restarts only the resolver, tests resolution, and restores that drop-in's prior state if the DNS step fails.
6. If `--install-regdb` is included, offer installation of `wireless-regdb`. No driver reload or Wi-Fi reconnect is forced; the next normal boot provides a clean opportunity for the kernel to load it.

**Privacy tradeoff:** TRIM allows the SSD to observe which encrypted blocks are unused. It does not expose their plaintext. This tradeoff is inherent to enabling encrypted-device discard. [Cryptsetup option documentation](https://man7.org/linux/man-pages/man8/cryptsetup-refresh.8.html).

The helper does not delete snapshots, change the power profile, repartition, reformat, perform a Btrfs balance, or replace boot files. TRIM also does not free blocks still referenced by your retained snapshots, and its reported trimmed byte count is not newly recovered filesystem space.

The administrator operations were **prepared, not executed**. Python syntax and five preflight parser cases were checked; actual privileged hardware changes still need execution and verification on this machine. If any step fails, the action record lists completed steps; earlier successful SSD changes are not silently undone. Review the printed error rather than rerunning blindly.

Afterward, and again after your next reboot, verify:

```sh
lsblk -D /dev/mapper/root
systemctl list-timers fstrim.timer
resolvectl status
```

The encrypted mapping should show nonzero discard capability, the timer should have a future run, and global DNS should show AdGuard with a `~.` routing domain and no third-party fallback list.

## Recovery and records

Original profile DNS settings are in `/home/user/Projects/machine-care/network-before-20260926-145939.json`; the later intermediate backup contains the briefly tested IPv6 DNS entries and is not the original baseline. To restore the original DNS settings without recreating the obsolete duplicate:

```sh
python3 /home/user/Projects/machine-care/configure-network.py --restore /home/user/Projects/machine-care/network-before-20260926-145939.json
```

The obsolete profile's non-secret metadata is in `/home/user/Projects/machine-care/obsolete-archer-metadata.json`. It is not a full credential backup; the retained working profile holds the network password.

If the administrator helper was applied, its root-only `admin-backup-*` directory records whether the DNS drop-in existed previously and whether the trim timer was previously enabled. Restore or remove only `/etc/systemd/resolved.conf.d/90-machine-care-adguard.conf` according to that record, then restart `systemd-resolved` to undo that global DNS change. Profile rollback alone does not undo the global drop-in.

For this inspected setup only, with no additional flags since the change, disabling the persistent discard flag uses `sudo cryptsetup refresh --persistent root`; disable the timer only if its record confirms it was previously disabled. Review the current flags first because refresh can reset other activation flags. Do **not** restore a LUKS header blindly onto a mounted disk.

Keep the header backup private: together with a passphrase valid at backup time it can unlock the volume, even after that passphrase is later changed. Do not upload it with diagnostic output. [Header-backup security note](https://gitlab.com/cryptsetup/cryptsetup/-/blob/main/man/cryptsetup-luksHeaderBackup.8.adoc).
