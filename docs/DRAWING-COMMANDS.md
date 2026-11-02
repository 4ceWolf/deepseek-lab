# Drawing commands

DeepSeek can describe visuals with a small declarative language. The app interprets these commands into a native SVG artifact. This is separate from OS/shell command execution.

Use a `deepseek-draw` fenced block. A whole reply containing only a valid drawing program is accepted too; ordinary mixed prose is not treated as commands. Unknown commands or invalid geometry leave the text visible with a rendering error. No scripts, URLs, file access or shell commands are supported.

```deepseek-draw
canvas 800 320
title "A simple workflow"
source "Illustrative diagram"
rect 40 100 240 100 surface p0 12
text 70 155 22 p0 "Input"
arrow 290 150 500 150 p1 3
rect 520 100 240 100 surface p1 12
text 550 155 22 p1 "Output"
```

One command per line. Quote text with double quotes. Numbers use canvas coordinates in pixels. The title and source sit outside the drawing area.

| Command | Arguments |
| --- | --- |
| `canvas` | width height |
| `title` | "title" |
| `source` | "provenance or illustrative label" |
| `rect` | x y width height fill stroke radius |
| `circle` | center-x center-y radius fill stroke |
| `line` | x1 y1 x2 y2 color stroke-width |
| `arrow` | x1 y1 x2 y2 color stroke-width |
| `text` | x y font-size color "text" |

Colors: `#RRGGBB`, `none`, `background`, `surface`, `text`, `title`, `muted`, `grid`, `p0` through `p5`. Palette/role tokens respond to Appearance controls. Fixed hex colors remain editable in the specification.

Limits: 30 KB of drawing commands, 1–80 primitives, width 200–2400, height 100–2400, font sizes 8–72, stroke widths 1–20. Shapes must fit the canvas; text clips at its boundary. Supported primitives become a validated `drawing` specification with editable command arrays. Text is escaped, numbers are finite and bounds-checked, and export uses a fixed template.

In API Code mode the model can call `draw_visual` with a `commands` string. In website Chat, the app parses the assistant's completed reply; this does not require API tools. The Artifacts tab offers Visual, Data, Specification, Appearance, and HTML/SVG/PNG/CSV/JSON export. Import visual accepts either drawing commands or a supported artifact JSON spec.

A live website test on 2026-10-22 generated an Input → Check → Result diagram. The model returned valid bare commands rather than a fence; that integration gap was fixed, and the saved reply was reprocessed without a second model request. Its native SVG was validated and exported to `build/previews/desktop-live-drawing.png`. This is an illustrative capability test, not a capability/performance benchmark.
