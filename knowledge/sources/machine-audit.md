# Kyo's laptop: storage and performance audit

September 26, 2026, approximately 14:38–14:47 PKT. Host measurements, not the Flatpak's private filesystem. All sizes below are GiB unless otherwise stated; 1 GiB = 1,073,741,824 bytes.

## The important result

Your drive is not close to full: approximately **135 GiB used of 476 GiB**, with **340 GiB available**. The mysterious usage is largely identifiable files, caches, and restore-point retention—not unexplained missing storage.

After your explicit approval, Trash was emptied permanently through the desktop's trash service. Its file and metadata directories are now empty. Reviewed developer caches were also cleaned. Together, the targeted live directories shrank by about **46.4 GiB**:

| Action | Live-directory reduction | What remains |
|---|---:|---|
| Empty Trash | 42.84 GiB | Empty Trash; 4 KiB of directory metadata |
| Remove 14 reviewed old AUR archives/downloads | 2.41 GiB | Three newest built packages each for Claude Desktop and Antigravity, their current downloads, recipes, and source trees |
| Clear pip download/wheel cache | 0.37 GiB | Installed Python packages and environments untouched |
| Clear npm download cache | 0.57 GiB | Installed dependencies and npx tools untouched |
| Clear Go compilation cache | 0.16 GiB | Go itself, source code, and module downloads untouched |

The measured user-home directory total fell from approximately **93.5 GiB to 47.0 GiB**. Some additional change is ordinary activity in running applications, so that whole difference is not attributed to this cleanup.

**Actual free disk space did not meaningfully increase.** After deletion finished and the filesystem was flushed, the filesystem still reported about 135 GiB used. This is not a claim of 46 GiB physically reclaimed.

### Why the disk meter did not move

Snapper is configured to snapshot both `/` and `/home` hourly. Each configuration retains up to 10 hourly, 10 daily, 10 monthly, and 10 yearly timeline snapshots. Cleanup is enabled and its most recent run succeeded, but retained restore points can still reference deleted files.

Snapshots sharing the deleted files' blocks are the leading explanation for the unchanged disk usage. The snapshot directories are root-only, and the unprivileged snapshot inventory was denied, so I could not verify which individual snapshots retain those blocks or measure their exclusive space. [Btrfs documents how snapshots share blocks with their source](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html).

Emptying Trash removes its recovery entries; it does not erase copies in existing restore points. Snapshots are local restore points, not independent backups against drive failure. None were deleted or modified.

## Where the space was going

Directory measurements are useful attribution, not an additive accounting of the filesystem's physical usage: Btrfs compression, shared extents, hard links, and inaccessible snapshots affect the totals.

| Location before cleanup | Approximate size | Decision |
|---|---:|---|
| `/home/user/.local/share/Trash` | 42.8 GiB | Emptied with explicit approval |
| `/home/user/Downloads` | 14.8 GiB | Preserved: videos, OS installers, phone firmware, and other downloads |
| `/usr` | 13.5 GiB | Installed system software; untouched |
| `/var/cache/pacman/pkg` | 8.6 GiB | Administrator-owned package cache; untouched |
| `/home/user/.var/app` | 6.7 GiB | Flatpak applications, data, and runtimes; preserved |
| `/home/user/Projects` | 6.2 GiB | All existing projects preserved |
| `/home/user/.cache/yay` | 6.1 GiB | Reduced to approximately 3.7 GiB while retaining rollback packages |
| `/var/lib/libvirt/images` | 5.0 GiB | Virtual-machine disks; preserved |
| `/home/user/.local/share/flatpak` | 4.5 GiB | Installed user Flatpaks; no unused runtimes found |
| `/home/user/s7_firmware` | 2.6 GiB | Phone firmware; preserved |
| `/var/lib/waydroid` | 2.2 GiB | Android environment; preserved |
| `/var/log/journal` | 0.7 GiB | System logs; preserved |

Within Projects, the original Echo Rust folder accounts for about 3.5 GiB and Echo Next about 2.5 GiB, largely build outputs. Both were left intact. The original Echo Rust remains read-only for this work, and its freeze file was not edited.

Within Flatpak app data, Sober accounts for roughly 3.0 GiB and this assistant app roughly 3.4 GiB. Much of the assistant app's space is its active development runtime and browser-testing tools—not disposable junk. Browser profiles, sessions, passwords, chats, model files, saves, and active application caches were not cleared.

## The machine itself

- Lenovo model identifier **82TT**.
- **Intel Core i5-1235U**, 10 cores / 12 hardware threads.
- **7.5 GiB usable RAM**.
- **512 GB-class SK hynix NVMe SSD**, approximately 476 GiB available to the encrypted root filesystem.
- Arch Linux, kernel **7.2.6-zen2-1-zen**.
- Niri desktop with Dank Material Shell; PipeWire audio.
- LUKS-encrypted Btrfs with `zstd:3` compression already enabled.
- **3.7 GiB zram swap**, using zstd compression.

## Performance findings

### Memory matters more than disk fullness here

During inspection, Sober/Roblox was the largest resident-memory process: roughly 2 GiB at the first sample, varying later. Firefox, this assistant app, and the Qt-based desktop/messaging apps consume additional memory. Per-process RSS is not additive because shared pages can be counted more than once.

Available RAM varied around 1.8–2.3 GiB. Zram held roughly 2.1–3.6 GiB of swapped data during the session; in one sample 3.1 GiB compressed to about 839 MiB. Brief memory pressure was observed, but the final 10-second pressure average was zero. This is a workload snapshot, not a benchmark establishing a speedup.

For heavy gaming alongside browser tabs and development tools, closing apps you are not using is the practical immediate lever. No apps were killed, no tabs closed, and no sessions interrupted. Swapping was not disabled and Linux's useful filesystem caches were not forcibly dropped.

### Power profile deserves a deliberate choice

TuneD is active with the manually selected `throughput-performance` profile; both the CPU governor and energy-performance preference reported `performance`. This favors throughput rather than laptop efficiency. For everyday use, `balanced` is a reasonable option to evaluate, not a guaranteed gaming-speed improvement. The laptop was plugged in at 99% during this audit, and the existing preference was left intact. [TuneD's profile documentation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/monitoring_and_managing_system_status_and_performance/optimizing-system-performance-with-tuned).

Changing this system-wide setting requires administrator access. If you choose to try it later in your own terminal, `sudo tuned-adm profile balanced` selects it; `sudo tuned-adm profile throughput-performance` restores the observed profile. Neither command was run.

### SSD maintenance needs an encryption-aware review

The SSD supports discard, but the encrypted mapping currently reports zero discard capability, and the weekly `fstrim.timer` is disabled. Merely enabling the timer would not address the mapping. Enabling discard through encryption also exposes allocation information, so I did not change encryption, boot options, mount settings, or timers. [Arch's SSD guidance](https://wiki.archlinux.org/title/Solid_state_drive) and [encrypted-discard considerations](https://wiki.archlinux.org/title/Dm-crypt/Specialties#Discard/TRIM_support_for_solid_state_drives_(SSD)).

### Other checks

- No failed system services or user services were reported at the initial check; user services remained healthy afterward.
- Docker reported no images, containers, volumes, or build cache to reclaim.
- Flatpak reported no unused user runtimes. Duplicated-looking system/user runtime entries were not manually removed.
- Baloo is not running, though its approximately 1 GiB index remains available for KDE use. It was preserved rather than forcing a future reindex.
- Nine orphan packages were detected, but not removed: dependency status alone does not establish that you no longer want a tool.
- No hardware health certification is implied; privileged SSD health and snapshot accounting were not available.

## Finishing the storage recovery in your own terminal

The biggest next step is **reviewing home restore points**, not more indiscriminate cache deletion. This read-only helper obtains the missing administrator-only inventory:

```sh
sudo sh /home/user/Projects/machine-care/admin-review.sh 
```

It only prints filesystem usage and the home/system snapshot lists. Share that output before selecting restore points for removal. Removing snapshots loses those recovery versions; do not delete all snapshots blindly, remove live subvolumes, or grant this assistant unrestricted administrator access as a workaround.

The system package cache offers a smaller, separate opportunity: a read-only version comparison found **53 old archives totaling about 1.14 GiB** beyond the newest three versions per package/architecture. `paccache` is not currently installed. Once `pacman-contrib` is installed through your normal package-management workflow, the conservative commands are:

```sh
sudo paccache -d -k 3
sudo paccache -r -k 3
```

The first previews candidates; the second removes them while retaining three versions. No package installation or system cache removal was performed here. Avoid an all-cache purge that removes rollback options. [Official paccache manual](https://man.archlinux.org/man/paccache.8).

For prevention, review snapshot retention and consider a planned, administrator-managed layout that excludes disposable Trash/cache data from future home snapshots. Nested Btrfs subvolumes provide a snapshot boundary, but migrating active directories warrants a separate careful change; it was not attempted during this cleanup. [Btrfs nested-subvolume behavior](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html#nested-subvolumes).

## Audit trail and verification

- `/home/user/Projects/machine-care/clean-reviewed-caches.py` previews by default. It is a dated, narrowly reviewed cleanup, not a general-purpose automatic cleaner.
- `/home/user/Projects/machine-care/cleanup-20260926-144242.json` records all 14 removed archive paths, command results, and filesystem measurements. All three cache-tool commands exited successfully.
- Desktop Trash enumeration returned zero items; its files and info directories were empty after asynchronous deletion completed.
- Package checks reported **zero missing installed files** for Claude Desktop and Antigravity. Three rollback package archives for each remain.
- No installed applications, user documents, downloads, game data, project contents, startup entries, kernel settings, or freeze files were removed or modified. No sudo commands were executed.
- New report/helper files live only under `/home/user/Projects/machine-care`.
