# One-command Plymouth recovery

Install the helper NOW, before activating Miku:

```sh
sudo install -m 0755 /home/user/Projects/miku-plymouth/revert-plymouth /usr/local/sbin/revert-plymouth
```

This copies a standalone script onto the root filesystem, so recovery does not
need /home mounted, this project, networking, or any animation assets.
Installing the helper does not switch themes or rebuild anything.

If Miku prevents a usable boot, boot an Arch live USB. For THIS laptop's current
partition layout (verify with `lsblk -f` before proceeding):

```sh
cryptsetup open /dev/disk/by-partuuid/3b599111-aff6-48d1-a7ba-5e6e6123b469 root
mount -o subvol=@ /dev/mapper/root /mnt
mount /dev/disk/by-uuid/A4DB-A261 /mnt/boot
arch-chroot /mnt
revert-plymouth
```

Enter the encryption password only at cryptsetup's interactive prompt. If the
root mapping is already open or partitions already mounted, do not repeat those
steps. The helper insists the correct EFI partition is mounted at /boot, selects
the original Tribar theme, and rebuilds only the Zen preset, leaving LTS alone. Do not reboot if
the rebuild fails. After success:

```sh
exit
umount -R /mnt
reboot
```

If the helper was never installed, the built-in equivalent INSIDE the chroot,
with the correct /boot mounted, is:

```sh
plymouth-set-default-theme tribar && mkinitcpio -p linux-zen
```

This recovers a broken Miku theme; it does not fix disk corruption, a broken
bootloader, or forgotten encryption passwords. It does not remove Plymouth,
change encryption hooks, or disable encryption. The rebuild uses CPU and RAM;
no rebuild was performed while preparing this helper.

Read-only preflight on the running installed system:

```sh
bash /home/user/Projects/miku-plymouth/revert-plymouth --check
```
