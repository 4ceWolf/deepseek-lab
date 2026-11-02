# Interactive visuals directly in chat — 2026-10-22

## User-facing behavior

Live visual cards now occupy their position in the chat document, between the surrounding explanation, in both website Chat and API Code. They are native Qt widgets anchored to real sized inline text objects, not a separate browser tab or workspace pane. The Artifacts output tab is hidden; Code's Review tab remains available for receipts. Charts, tables and drawings also render inline when their supported specs appear in a response. API tool-produced artifacts attach to the originating assistant/tool exchange after their saved specs arrive.

Interactive cards support sliders with numeric inputs, toggles, numeric-valued selections, draggable points with keyboard-editable coordinates, live calculated readouts, a time scrubber, Play/Pause and Reset. Animation starts paused, respects Reduce motion, and avoids updating the simulation when the card is outside the visible area. Changing a control evaluates locally and does not call DeepSeek. User control values are debounced into the private local store per conversation and normalized spec hash, survive window reloads, and remain stable during streamed response updates. Identical specs repeated in one conversation share their exploration state. Revised specs get a new identity. Exploration values are not automatically inserted into future model prompts.

Interactive exports include standalone offline HTML with the same controls, animation and point dragging, a PNG snapshot, and JSON containing the specification and current state. Static inline visuals retain HTML/SVG/PNG/CSV/JSON exports. HTML uses a fixed, hashed script and embedded validated data; it does not fetch libraries or execute model-generated JavaScript. The desktop app remains native.

## Format for DeepSeek

Use a fenced `deepseek-visual` JSON block. JSON fences or a complete JSON-only reply are also recognized when the object explicitly has `kind: "interactive"`. Ordinary JSON examples remain plain code. Website replies are parsed and persisted; API Code also has `create_interactive_visual`. Instructions describe the available interpreter so the model knows that plain text can create an interactive result.

```json
{
  "kind": "interactive",
  "title": "Explore a wave",
  "description": "Adjust amplitude and phase, then play or scrub time.",
  "source": "Illustrative sine-wave model, not measured data",
  "controls": [
    {"id":"a","label":"Amplitude","type":"slider","min":0,"max":3,"step":0.1,"value":1},
    {"id":"phase","label":"Phase","type":"slider","min":0,"max":6.28,"step":0.01,"value":0},
    {"id":"probe","label":"Probe","type":"point","x":1,"y":0}
  ],
  "scene": {
    "x":[-8,8], "y":[-4,4], "axes":true,
    "layers":[{"type":"curve","x":"u","y":"a*sin(u+phase-t)","u":[-8,8],"samples":200,"color":"p0","label":"Wave"}]
  },
  "readouts":[{"label":"At probe","expr":"a*sin(probe_x+phase-t)","unit":"m"}],
  "animation":{"duration":12,"speed":1}
}
```

Scene layers can be curves, circles, rectangles, lines, arrows or text. Geometry and visibility accept bounded arithmetic expressions. Variables are control IDs, point coordinates as `id_x`/`id_y`, `u` for curve sampling, `t` for time, and `pi`, `tau`, `e`. Supported functions: sin, cos, tan, sqrt, abs, exp, log, log10, min, max, floor, ceil, atan2. Arithmetic, comparisons, boolean operations and conditional expressions are supported. Power uses `**`. A readout-only spec can act as a calculator without an empty plot.

The expression interpreter walks a validated syntax tree; it never uses Python eval or generated executable code. Exported HTML receives equivalent precompiled expression trees, interpreted by the fixed runtime. Invalid operations remain undefined or produce a visible rendering error rather than becoming tool calls.

Limits: 60 KB per spec, 8 controls, 12 layers, 8 readouts, 1,600 total curve samples, expressions under 240 characters/80 syntax nodes, finite bounded values, and limited animation duration/speed. This is a general declarative scene/calculator renderer, not an arbitrary HTML/JS app runtime or a guarantee of the model's mathematics. Sources, units and assumptions still need review. Native screen-reader certification and full model capability parity are not claimed.

## Implementation

- `interactive.py`: normalized specs, state and bounded expression evaluator.
- `interactive_view.py`: native scene, controls, dragging, local calculation and animation.
- `inline_visuals.py`: Qt text-object sizing and widget anchoring, scrolling, card reuse and persisted state.
- `interactive_html.py`: offline export and static compatibility preview.
- `web_artifacts.py`, `webchat.py`, `core.py`: capture, model instructions, tool and durable state.
- `artifact_export.py`: shared explicit exports for static visuals and the existing inspector.

## Verification

- Full offline suite: **169 checks passed**, covering native UI, website/API controllers, artifacts, inline placement, expressions, memory, recovery, commands and existing features.
- Browser export checks passed: slider/readout updates, Play/Pause, Reset, reduced motion and 480 px layout. **Zero network requests and zero page errors.**
- Native checks verify inline object slots, direct controls/dragging, reuse across response changes, restoration after chat switches, context isolation, repeated visuals, animation and reduced-motion scrubbing. A focused rerun covers the final point-control layout adjustment.
- One live website request (thinking off, search off) generated a valid interactive sine-wave explanation with 3 controls, readouts and animation. Its native card rendered in the conversation, and changing a slider updated it locally. No paid API call was made for the live check.
- Preview files are under `build/previews/`. `desktop-live-interactive-inline.png` is an actual reply from the live test; the wave-interference example is an explicitly illustrative fixture. The exported example is `desktop-interactive-example.html`.

The GUI/service source bundle is rebuilt after verification. The installed editable app loads the project source; no new dependencies or competitor runtimes were installed.

Live account screenshots remain local and are excluded from the distributable source bundle; fixture previews and the offline example export are included.
