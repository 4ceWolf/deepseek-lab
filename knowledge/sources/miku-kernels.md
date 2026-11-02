# Zen with Miku; LTS without Plymouth

Prepared for the inspected systemd-boot UKI setup. No changes are made until:

```sh
sudo python3 /home/user/Projects/miku-plymouth/setup-kernels.py --apply
```

Close games and memory-heavy applications first. The installer requires 2 GiB
available RAM and 700 MiB free on the mounted EFI partition. The custom presets
use single-worker zstd compression. The initial Zen build additionally runs with
a 2 GiB memory cap, 256 MiB swap cap, and two CPUs worth of CPU quota. Normal future
package-manager rebuilds retain single-worker compression but not those cgroup caps.
Pacman's LTS installation/hooks run normally and require confirmation. No full
system upgrade or package database refresh is performed. If package downloads
fail, stop and review instead of performing a partial database refresh.

The installer preserves the original Zen image in a private root backup and as
an explicit recovery menu entry. It prepares LTS's preset BEFORE installing the
kernel so package hooks do not embed Plymouth. It verifies that the generated
LTS image contains the encryption hook but neither Plymouth nor Miku. DKMS users
also receive linux-lts-headers; otherwise only linux-lts is requested.

LTS has its own command line without quiet/splash and with plymouth.enable=0,
disabling the installed Plymouth system services on that boot too. Its config
excludes the Plymouth hook. Zen's config includes it immediately before encrypt.
The original encryption/root parameters are retained for both.

Zen is built into a staging image and checked before replacing its original UKI.
The two UKIs embed distinct PRETTY_NAME values, so systemd-boot auto-discovers:

- Arch Linux Zen (Miku), default, with a seven-second configured menu timeout.
- Arch Linux LTS (plain recovery).
- Arch Linux Zen (before Miku), a preserved copy via an explicit EFI entry.

Firmware menu-timeout/default overrides, if previously set, may override the
loader.conf settings. Inspect the actual boot menu. Select LTS first and confirm
it reaches the desktop before testing Zen/Miku. Image-content verification is
not a real boot test and does not prove Miku password rendering works.

The pre-Miku image is an immediate recovery aid, not a permanently maintained
kernel: future upgrades may remove its matching modules. LTS receives normal
kernel package updates and is the long-term alternative.

The installer copies the standalone revert-plymouth helper into /usr/local/sbin.
That helper restores Tribar and rebuilds Zen only. LTS stays unchanged. After
reverting, Zen's menu title may still say Miku; this is cosmetic, not activation.
See RECOVERY.md for the live-USB/chroot procedure.

If setup fails, its finally handler restores the original Zen preset, theme
configuration, loader configuration, and (if replaced) image. LTS package/config
and recovery copies remain for inspection. This handler cannot protect against
power loss or forced termination. Backups live under /var/lib/miku-boot-backup-*.
Do not blindly rerun an interrupted setup; it refuses existing managed/LTS
configuration rather than overwriting it. No automatic reboot occurs.
