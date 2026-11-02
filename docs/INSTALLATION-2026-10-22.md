# DeepSeek Lab installation — 2026-10-22

The user explicitly authorized dependency installation and installation of the native application. This supersedes the earlier build-only instruction.

## Installed application

- App menu name: **DeepSeek Lab**.
- Executable wrapper: `/home/user/.local/bin/deepseek-lab`.
- Desktop entry: `/home/user/.local/share/applications/deepseek-lab.desktop`.
- Native source: `/home/user/Projects/deepseek-lab`.
- Persistent state/logs: `/home/user/Projects/deepseek-lab/data/desktop/`.
- Documentation: `/home/user/Projects/deepseek-lab/docs/`.
- Icon: `/home/user/Projects/deepseek-lab/desktop/deepseek-lab.svg`.

This is an editable user-local installation. The app-menu and executable launchers run the source directly, so it remains modifiable without a separate copied app tree. Existing Dev staging and idle service restart controls remain applicable. The native Qt window identifies itself as `deepseek-lab` for its Wayland icon/app-menu association. There is no login/autostart entry.

`python3 install_desktop.py` registers the launcher and desktop entry. It validates source presence, avoids replacing unmanaged launcher files, and can be repeated. It does not install system packages, start the service or launch a window by itself. The generated wrapper fixes source/state paths and invokes the installed host Python runtime.

## Dependency installation

Host already had Python 3.14.8, PySide6 6.12.0, Node 26.12.0 and secret-tool. Only Chromium was added: Arch package `chromium 154.0.8037.97-1`.

The initial normal repository install failed because the configured mirror returned 404 for that version's detached signature. No package changed in that failed transaction. The same package was then successfully installed through pacman from the official Arch Linux archive URL:

https://archive.archlinux.org/packages/c/chromium/chromium-154.0.8037.97-1-x86_64.pkg.tar.zst

Administrator authentication used the system graphical prompt. No password was requested or recorded in chat. Signature verification was not disabled; normal pacman keyring/integrity/conflict checks ran. System mirror configuration was not changed. No full system upgrade was performed. Existing automatic pacman/Snapper hooks ran as part of the transaction.

## Observed verification

- Installer exercised in a temporary home: executable mode, generated paths, repeated registration, and protection against unmanaged file replacement.
- Desktop entry passed `desktop-file-validate`; icon passed Qt SVG validation.
- App launched successfully through `gtk-launch deepseek-lab`.
- Niri reported the native window titled **DeepSeek Lab**, with app ID `deepseek-lab`.
- The local Unix-socket service responded. Default project/docs point inside Projects, no task was running, and command mode was `approve` (every command requires approval).
- Installed Chromium reports its version successfully.
- Bundled Playwright library launched installed Chromium headlessly with the Chromium sandbox enabled, rendered a local fixture and closed it.
- Bundled private website bridge detected the browser and reported no account session. This verification did not log in, access a personal browser profile or make a model request.

The app was left open. Choose **Normal chat → Sign in / Reconnect** for website-account chat. The API workspace currently has no connected key. Actual website login, Google sign-in eligibility, private endpoint compatibility and live search results remain unverified until the user signs in.

For removal, close the native app/service before removing its two user-local launcher files. Source and saved state are deliberately separate and are not deleted by removing launchers. Chromium is a separately managed system package.
