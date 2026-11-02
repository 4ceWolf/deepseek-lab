# Read-only host observations — 2026-10-14

Commands ran through `flatpak-spawn --host` as the normal user. No OS configuration changed.

| Check | Result |
|---|---|
| `uname -r` | `7.2.9-zen1-1-zen` |
| `systemctl is-active machine-care-firewall.service` | active; does not verify live packet behavior |
| `systemctl is-enabled fstrim.timer` | enabled |
| `systemctl is-active fstrim.timer` | active; does not verify a trim run or encrypted discard |
| `findmnt -n -o FSTYPE /` | btrfs |
| `ls -l /usr/local/sbin/revert-plymouth` | no such file; do not assume historical helper is installed |
| `bootctl is-installed` | permission denied accessing EFI filesystem; bootloader state unverified |
| user `plasma-plasmashell.service` | inactive |
| user `niri.service` | active; does not identify every running desktop component |

These observations supersede older records only for the exact facts checked. LTS boot and current Plymouth rendering were not tested. The absence of the recovery helper was documented, not repaired: installing it or rebuilding boot images is outside this AI-control-layer upgrade.
