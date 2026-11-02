# Security fixes and bounded Docker test

## What actually happened

The user authorized a Docker privilege test. Docker created a single marker in an otherwise isolated test directory. A **host-side** ownership check reported numeric UID **0**, GID **0**, and mode **600**. This demonstrates that the existing rootful Docker permissions allow host writes as root; it is not an unknown Docker vulnerability or an escape from an otherwise unprivileged container.

Only `/home/user/Projects/machine-care/docker-proof` was mounted. The container had no network, a read-only container root filesystem, a PID/memory limit, no-new-privileges, and all capabilities dropped except the specific DAC override needed to write into the test directory. It did not mount the host root directory, credentials, Docker socket, or sensitive data. No persistent shell, account, key, setuid executable, or administrator permission was installed.

The root-owned marker was removed. The automatically removed container and newly pulled test image were also cleaned up. The assistant's host identity remained **kyo, UID 1000**. The test used Docker's official BusyBox image pinned to digest `sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e`.

**The underlying Docker access remains.** A firewall does not remove the local root-equivalent authority of a user who controls the Docker daemon. Changing to rootless Docker or removing direct daemon access is a separate decision; this task requested a test, not removal of your development workflow. Rootless prerequisites `newuidmap`, `newgidmap`, and subordinate UID/GID ranges exist, but rootlesskit and Docker's rootless setup helper are absent. No rootless migration was attempted. [Docker's security model](https://docs.docker.com/engine/security/) and [rootless mode](https://docs.docker.com/engine/security/rootless/).

## USB rule and firewall: ready for your terminal

The protected host configuration has **not yet been changed** by the assistant. Run:

```sh
sudo python3 /home/user/Projects/machine-care/apply-security-fixes.py --apply
```

Use a terminal on the laptop, not SSH. After a temporary firewall trial starts, check your browser and type **KEEP** within 100 seconds. Without confirmation, the script rolls back; a separate systemd timer also stops the trial firewall after 180 seconds if the script disappears. A confirmed firewall is enabled for future boots.

### Firewall policy

- A dedicated `inet machine_care_guard` table filters both IPv4 and IPv6. No global ruleset flush and no replacement of Docker/libvirt's NAT rules.
- Default-deny new inbound host connections, including unsolicited SSH and development-server access from the LAN.
- Default-deny new forwarded connections from outside into containers/VMs, including Docker-style DNAT/published-port access.
- Preserve loopback and replies to established/related connections.
- Permit outbound host traffic, and container/VM initiated forwarding through the inspected Docker bridge naming patterns and `virbr0`; their existing forwarding/NAT rules still apply.
- Preserve ICMP/ICMPv6, DHCP clients, libvirt guest DNS/DHCP, and link-local multicast mDNS discovery. mDNS remains intentionally available for local-device discovery; this is not a stealth policy.
- Disable LLMNR through a separate resolver drop-in while retaining the existing encrypted AdGuard DNS setup.
- Rate-limit logging of dropped traffic to avoid filling logs.

The firewall blocks new LAN connections to hosted game servers, file-sharing servers, remote desktop, SSH, and LAN-published containers until explicit exceptions are added. Most client-initiated browsing/gaming traffic remains allowed, but peer-to-peer games/calls can need additional rules. Outbound traffic is not application-filtered, and the firewall cannot make malicious programs harmless or prevent a Docker-authorized user from undoing it.

This deliberately protects the forwarding path, not just host INPUT: Docker publishing uses forwarding/NAT, which can bypass simplistic host-only firewall assumptions. [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/) and [nftables workstation policy](https://wiki.nftables.org/wiki-nftables/index.php/Simple_ruleset_for_a_workstation).

### USB rule removal

After the firewall is confirmed, the helper backs up and removes exactly `/etc/udev/rules.d/60-odin4.rules`, only if it still matches the reviewed Samsung rule. It reloads rules without triggering a USB bus reset. This removes the nonexistent `plugdev` reference and the vendor-wide `0666` permission request.

An already connected Samsung device can retain its old permissions until unplugged/replugged. Replug it only when no flashing or transfer is in progress. Odin access might then require administrator rights; no broad replacement access grant is added. Because the rule belongs to `odin4-cli`, a later package upgrade could recreate it. Its backup stays in the root-only `security-backup-*` folder.

## Verification and rollback

The ruleset was syntax-checked, loaded, reloaded, and removed successfully inside an isolated unprivileged user/network namespace. IPv4 traffic tests passed for baseline host and DNAT reachability, blocked host ingress, blocked published-port ingress, allowed loopback, allowed host outbound, allowed container outbound, and restored reachability after removing the guard table. These do not constitute an external penetration test of the live laptop.

Seven additional IPv6 checks passed for baseline host/guest reachability, blocked host/guest ingress, allowed loopback, and allowed host/guest outbound connections. The first IPv6 lab attempt timed out establishing baseline reachability before the firewall was loaded; after allowing namespace/neighbor startup time and a longer socket timeout, the combined 15-case IPv4/IPv6 run passed. No test changed the live host firewall.

The privileged installer is syntax-checked and has a preview mode. Its actual systemd timed rollback, USB removal, and host installation need verification when you run it; they have not been executed by the assistant.

Emergency firewall undo:

```sh
sudo systemctl disable --now machine-care-firewall.service
```

If systemd cannot stop it, remove only its dedicated table:

```sh
sudo nft destroy table inet machine_care_guard
```

Do not flush the entire ruleset or blindly restore an old full ruleset over newer Docker/VM networking. The backup's previous-ruleset file is for review, not automatic replay.

The LLMNR change is separate: removing `/etc/systemd/resolved.conf.d/91-machine-care-discovery.conf` and restarting `systemd-resolved` undoes it. Restore the saved USB rule only if you deliberately want its old permissive behavior. If a post-confirmation step fails, the already-confirmed firewall remains enabled and the backup folder records completed steps.

## Firmware findings—not a cosmetic suppression

Installed BIOS: **JKCN52WW**, Lenovo V15 G3 IAP (82TT). Lenovo lists **JKCN53WW** for this model family. The official README confirms model applicability, describes security updates and an embedded-controller key-handling change, and specifies a **Windows 10/11 updater**. It does not promise to resolve these ACPI duplicate-object/name-lookup warnings. [Lenovo release listing](https://pcsupport.lenovo.com/sg/en/products/laptops-and-netbooks/3-series/ideapad-3-15iau7/downloads/ds556359-bios-update-for-windows-11-64-bit-ideapad-3-14iau7-ideapad-3-15iau7-ideapad-3-17iau7-v14-g3-iap-v15-g3-iap-v17-g3-iap-ideapad-1-14iau7-ideapad-1-15iau7?category=BIOS) and [official README](https://download.lenovo.com/consumer/mobiles/jkcn53ww.txt).

No BIOS updater was downloaded or executed, no firmware was flashed, and boot/kernel logging was not weakened. Do not run the firmware updater through Wine or a virtual machine. Updating firmware should be a separate, attended procedure using Lenovo's supported method, with stable power, recovery access, and your disk-unlock passphrase available.

The earlier `qat_6xxx` initramfs warning concerns an optional accelerator module, with no matching active device identified in the inspection. No driver blacklist or unnecessary firmware package was added solely to silence it. Existing journal entries are historical records and have not been erased.

Your power profile, snapshots, and original Echo Rust project remain unchanged.
