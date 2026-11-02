# Plus Five · Machine Care

A local, read-only maintenance dashboard, matching Plus Five's charcoal and lime palette. Python standard library backend; no package installation, external scripts, fonts, analytics, or cloud services.

Run on the host, as your regular user:

```sh
sh /home/user/Projects/machine-care/dashboard/start.sh
```

Open http://127.0.0.1:5186. Stop with Ctrl+C. No autostart installed. Inside Flatpak, launch with `flatpak-spawn --host sh /home/user/Projects/machine-care/dashboard/start.sh`.

The server binds to IPv4 loopback only, validates Host/Origin, rejects cross-site browser requests, and serves only three fixed assets and two read-only endpoints. It refuses root. No command input, arbitrary file access, cleanup, firmware flashing, or settings changes are exposed. Local applications running as your user can still read its data; this is not an authentication boundary against local malware.

Checks refresh manually (15-second cache). Folder measurement is opt-in, bounded to selected non-overlapping home directories, cached five minutes, and limited to 12 seconds per folder. Permission-limited or timed-out sizes are explicitly incomplete. Btrfs shared extents and snapshots prevent summing folder sizes into physical drive use. No deep scan runs at startup.

Firewall service success is not live packet-filter verification. SMART, snapshot-exclusive usage, and external backup verification are not assumed. DNS status is configuration evidence, not a fresh lookup or guarantee that browser/VPN traffic uses it. Full command evidence remains visible, including permission errors.

## Post-reboot check · 2026-09-27

- Current boot began 11:14:32 PKT.
- fstrim.timer enabled/active, next run September 28 at 00:50:12 PKT.
- Encrypted root still advertises 512-byte discard granularity and 2 TiB maximum: discard passthrough persisted.
- machine-care-firewall.service enabled and active; successful nft load at 11:14:54 PKT. Unprivileged live rule inspection denied, so traffic behavior was not retested.
- Global and Wi-Fi resolvers report AdGuard named endpoints with DNS-over-TLS; fresh example.org lookup succeeded and reported local/encrypted transport. LLMNR disabled.
- Removed Samsung USB rule remains absent. No failed system units.
- No post-reboot trim invocation observed yet; the next weekly run is still pending.

Power profile, snapshots, original echo_rust, and project freeze file remain unchanged.

## Validation

Python compilation, JavaScript syntax, live status and storage endpoints, security response headers, Host/Origin/cross-site rejection, fixed-route restrictions, and simulated permission-denied states passed. The live collector confirms encrypted-root discard capability. A real folder scan completed with partial results explicitly labeled for Projects and .local/share.

Browser inspection was blocked by the app's browser security-policy verification. No bypass was attempted. Visual, keyboard, narrow-screen, and zoom checks remain unverified; responsive styling and semantic controls are implemented but not a completed accessibility audit.
