# Working Miku boot snapshot

Saved on 2026-09-29 at the user's request after a successful Zen boot.
The user confirmed the disk-unlock prompt appeared and successfully unlocked
the system. They also reported liking its gradient/blur-like background.
This is user-reported runtime verification, not an independently captured
screenshot or automated UI test. LTS boot verification has not been reported.

Observed after reboot: kernel 7.2.7-zen1-1-zen and Theme=miku-safe.
This folder preserves the full staged project, including 912 animation frames,
theme script, pinned download manifest, installer, and recovery instructions.
Existing README/KERNELS notes about pending runtime testing describe the earlier
staging state; this record updates that status for the user-confirmed Zen boot.

Source: /home/user/Projects/miku-plymouth
Installed theme: /usr/share/plymouth/themes/miku-safe
Recovery command: sudo revert-plymouth
Inside a root chroot with /boot mounted: revert-plymouth

This is an archive, not an instruction to rerun setup-kernels.py on the already
configured system. Original Echo source and freeze notices were not changed.
