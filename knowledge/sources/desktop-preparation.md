# KDE → prepared iNiR migration

## Update after confirmed removal

Both DMS packages are now absent, verified with pacman. iNiR source revision is `9574fa424c0d1008e927454e933a7fbe292f9fb2`. Its launcher and runtime are linked into the user's home; its private settings disable the wallpaper pipeline's external-app enable flags and select the installed Alacritty terminal. Nothing has launched or enabled iNiR yet.

The old DMS startup drop-in was moved into the existing backup as `removed-dms.conf`; the user service manager no longer requests DMS from Niri. The replacement Niri config at `inir-staging/config.kdl` passed `niri validate`. It is NOT the active Niri config. No KDE theme, login-manager, power-profile, or snapshot settings changed.

Thirteen missing official-repository prerequisites were identified and a package-manager preview succeeded:

```sh
sudo pacman -S --needed brightnessctl cliphist fish grim playerctl polkit-gnome slurp swayidle swaylock wlsunset ttf-material-symbols-variable wl-clipboard xwayland-satellite
```

Roboto Flex was also listed upstream but is unavailable in the configured official repositories; do not install an unreviewed AUR recipe automatically. Font fallback can be checked during testing. Python helper environment setup and graphical smoke testing are still pending. Do not switch sessions yet.

The earlier preparation record follows; its pending-removal and unchanged-drop-in statements are superseded by this update.

Inspected 2026-09-28. Current session is KDE Wayland; plasmashell is running, DMS and Niri are not. No KDE settings, power profile, login manager, or snapshots changed.

Backup: `/home/user/Projects/machine-care/desktop-backup-UNYJHsyd/` contains Niri settings, DankMaterialShell settings (if present), the Niri service drop-in, and installed package versions. Preserve this directory privately.

Installed DMS packages: dms-shell 1.6.2-1 and dms-shell-niri 1.6.2-1. A removal preview selects exactly those two. Run in a host terminal:

```sh
sudo pacman -R dms-shell-niri dms-shell
```

Do not use recursive dependency removal: Niri, Quickshell, and shared KDE libraries must remain. Package removal is pending user authentication; it has not been executed by the assistant.

Missing documented iNiR prerequisites: wl-clipboard, cliphist, grim, slurp. Already present: niri, quickshell, syntax-highlighting, kirigami, kdialog, pipewire, wireplumber, plasma-browser-integration, plasma-integration. This is a preliminary check, not a complete dependency audit.

Upstream source is being prepared at `/home/user/Projects/inir`. Do not run an unattended installer or copy all upstream dotfiles onto KDE. Review optional app theming, login-manager modifications, and power-related setup first.

The existing Niri config includes DMS-generated bindings and appearance files. Its service drop-in requests dms.service even though that service is disabled. These remain unchanged until replacement config is ready. After package removal, stay in KDE: Niri's DMS launcher, locking, and media shortcuts will not function until migrated. KDE's own lock screen is unaffected.

Recovery: reinstall both DMS packages with the package manager, then restore only the backed-up files if subsequent migration changed them. Do not overwrite newer settings blindly.
