# Miku Plymouth: unlock-ready staging

Recovery: see `RECOVERY.md`. Install the standalone `revert-plymouth` helper
before activating this theme; it works from arch-chroot without mounting /home.

Animation source: all 38 clips (912 PNG frames) from Thang1191/MikuPlymouth,
pinned revision 2ffca526cc3c0fffb95dd2b8c0fd2bc11377a5db.
Original artwork/animations credited upstream to @x_cast_x.
Upstream README and installer are retained for reference; do not run the
upstream installer, which lacks password rendering and selects ten clips.
No upstream license was established; this is a local personal-use staging copy,
not a grant to redistribute the animation assets.

Run `python3 download-all.py` to download and verify all frames against pinned
Git blob hashes. The full pool is about 152 MiB compressed. At 1920x1080 RGBA,
preloading 912 frames would require about 7.05 GiB just for decoded pixels.
Instead, this script starts at a random clip and cycles through all 38, loading
one frame on demand every three refresh calls (nominally 20 fps at 60 Hz).
No array retains previous frames. Actual process memory and frame-decoding
latency still require runtime measurement; this is not a measured memory cap.
Animation pauses during questions/password entry to prioritize input.

Password source comparison: the installed `/usr/share/plymouth/themes/script/script.script`
registers the same `(prompt, bullets)` callback and restores normal display
through `SetDisplayNormalFunction`. Its text messages use the same `Image.Text`
and display/hide-message callbacks. This theme reconstructs the entire masked
string on each password update, so deletion does not leave stale characters.
The installed `/usr/lib/initcpio/hooks/encrypt` invokes Plymouth's password
request and passes its input to cryptsetup; the theme does not change that path.
Noto Sans is available through the host Plymouth font resolver. These comparisons
establish API alignment, not proof that the script renders or unlocks at boot.

The new script displays the supplied disk-unlock prompt, masks password input,
updates correctly on backspace, caps the visible mask at 40 characters without
limiting actual input, handles question/message callbacks, and dims/pauses Miku
while entering a password. Plymouth handles input; the theme receives only the
password character count, never the passphrase itself.

Status: staged only. No installed theme, initramfs, boot arguments, or services
have been changed. Runtime rendering and real disk unlock remain unverified.
Before activation, test empty input, typing, backspace, long input, failure/retry,
and return to normal display through Plymouth with a dummy password. Never use
the real disk password in a desktop preview.

The host has no Xvfb available; do not run a real-console Plymouth preview over
the active desktop without coordinating with the user. Activation requires root
and an initramfs rebuild. Keep the previous Tribar theme and a bootable recovery
entry available. Do not enable the upstream daily rebuild timer.
