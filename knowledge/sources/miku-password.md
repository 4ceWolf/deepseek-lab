# Password prompt and background appearance

When Plymouth requests the disk-unlock password, the theme:

- Pauses the animation on its current frame, including on-demand frame loading.
- Reduces the animation sprite to 15% opacity over a black background. This
  darkens the artwork so the white password prompt is easier to read.
- Draws the prompt and entry above the artwork: animation Z=-10, text Z=100.
- Centers the prompt at 68% of the screen height and the entry at 76%.
  Status/error messages appear at 88%. Overwide text is scaled to fit.
- Shows typing instructions for empty input, then asterisks as characters are
  entered. Backspace updates the mask. Beyond 40 characters it displays a plus
  sign; this limits only the visual mask, not the password length.

When Plymouth returns to normal display, the animation resumes at full opacity
and the prompt, entry, and message sprites are hidden. Ordinary question prompts
also pause and dim the animation, but display their supplied non-password entry.

## About the gradient / blur-like look

The user reported a pleasing gradient and blurred-looking background during the
successful boot. Preserve that visual result, but distinguish it from the code:
the script does NOT apply a blur filter or generate a colored gradient. Both
background colors are black. Its explicit effect is dimming the current artwork
to 15% opacity; any soft or gradient-looking detail may come from that artwork.
The exact perceived effect has not been independently inspected in a screenshot.

Plymouth handles password input and passes it through the existing encryption
hook. The theme's password callback receives only the prompt and character
count, not the password itself; it does not store or log the password.

Reference: theme/miku-safe.script, especially password(), question(), refresh(),
normal(), and label(). This note documents the working version without changing
the theme or the installed boot image.
