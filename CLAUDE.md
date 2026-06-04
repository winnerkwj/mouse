# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

An **archive of independent, single-file Python desktop utilities** for Windows — not one application. Each `.py` is its own entry point, run directly. There is no package, no shared module, no test suite, and no CI. UI text and comments are in Korean throughout.

Most scripts cluster around **mouse/input analytics**; the rest are one-off Windows desktop helpers.

## Commands

```powershell
# IMPORTANT: `python` on PATH is the Windows Store stub (no-op, exits non-zero).
# Use the `py` launcher -> resolves to Python 3.13.

py <file>.py                                   # run any tool (each file is standalone)
py -m pip install -r requirements.txt          # install dependencies
py -m py_compile <file>.py                      # quick syntax check (no deps needed)
pyinstaller mouse_click_move2.spec              # build dist/mouse_click_move2.exe (windowed, UPX)
```

There are no lint, format, or test commands configured. `py -m py_compile` is the fastest available correctness gate after an edit.

## Files at a glance

| File | Purpose |
| --- | --- |
| `mouse_analytics.py` | **Unified** recorder: click heatmap + movement distance + click/scroll counts, auto-saved to Excel (`openpyxl`, 3 sheets). Beginner UI, global hotkeys, excludes its own-window clicks |
| `mouse_click_move2.py` | Mouse-click **heatmap** tool — the PyInstaller build target |
| `mouse_distance1.0.6.py` | Tkinter canvas: click two points, compute pixel→mm distance via DPI |
| `click_update_v1.0.9.py` | Click counter + travel/scroll distance tracker; `s` toggles; saves a `.txt` to Desktop |
| `fps_1.0.8.py` | Loop-rate "FPS" monitor for the foreground process (win32 + psutil) |
| `get.py` | Print all open window titles (pygetwindow) |
| `ctdata_list.py` | List files in a hardcoded `D:\` path |
| `mouse_click_move2.spec` | PyInstaller spec for `mouse_click_move2.py` |
| `requirements.txt` | Dependency list (full `pip freeze`) |

Numbers in filenames (`v1.0.9`, `1.0.8`, `1.0.6`, the `2` in `mouse_click_move2`) are historical version tags. There is now a **single copy of each tool** — the superseded `mouse_click_move.py` (v1) was deleted in favor of `mouse_click_move2.py`. `build/` and `dist/` are regenerable PyInstaller artifacts and are git-ignored (rebuild with the spec).

## Recurring architecture (the heatmap / input tools)

These patterns repeat across `mouse_click_move2.py`, `click_update_v1.0.9.py`, and `mouse_analytics.py` and are the main thing to understand:

- **Threading model:** Tkinter owns the main thread for the GUI. `pynput` `mouse.Listener` / `keyboard.GlobalHotKeys` run on their own background threads. Shared position lists are guarded by a `threading.Lock`. **Tkinter is not thread-safe** — listener-thread callbacks must marshal UI updates back to the main thread with `self.root.after(0, ...)`.
- **Heatmap pipeline** (`mouse_click_move2.py`): accumulate click/move hits into a `numpy` array → `scipy.ndimage.gaussian_filter(sigma=30)` → normalize → apply a `matplotlib` colormap → convert to a `PIL` RGBA image → `Image.alpha_composite` over a `pyautogui.screenshot`. Caps stored points (`pop(0)` past 5000) to bound memory.
- **DPI-safe sizing:** `mouse_click_move2.py` captures the screenshot *first* and sizes the heatmap to its actual pixel dimensions, avoiding DPI-scaling mismatch when compositing. It also writes a temp-dir log file, keeps Undo/Redo stacks, and wraps every listener/IO call in try/except.
- **Multi-monitor:** `screeninfo.get_monitors()` enumerates monitors; global mouse coordinates are converted to monitor-relative before recording.
- **DPI → physical distance:** `mouse_distance1.0.6.py` and `click_update_v1.0.9.py` derive `pixels_per_mm` from `hypot(w, h) / diagonal_inches` to convert pixel measurements into mm/cm.

`mouse_analytics.py` adds three patterns on top of the above:
- **Per-step ("software stage") model:** a recording is divided into *steps* — `Ctrl+Shift+F10` (`advance_step`) finalizes the current step (builds its heatmap, stores its stats, resets the click/distance/scroll accumulators) and re-captures the background for the next step; stop finalizes the last step. Each step's clicks/heatmap are independent, so you get one heatmap per software screen (Alignment → Orientation → …) in a single continuous recording.
- **Excel auto-save** (`openpyxl`, MIT — added to `requirements.txt`): one workbook per session with a `summary` sheet (session info + a per-step table + totals), one `step{N}` sheet per step holding that step's embedded heatmap PNG (`openpyxl.drawing.image.Image`), and an `events` sheet (all events with a leading `step` column). Writes to a temp file then `os.replace`; if the target `.xlsx` is locked (open in Excel) it falls back to a `_backup_<ts>.xlsx`. Autosave fires from a single self-rescheduling `after(1000, tick)` (no extra timer thread).
- **Own-window click exclusion:** global listeners would otherwise record clicks on this app's own buttons. `_own_rect` (cached on the main thread, `None` when minimized) + a `_suppress` flag (set around modal dialogs) make listener callbacks drop self-events. The rect comes from Win32 `GetWindowRect` on the `GA_ROOT` ancestor (`_window_frame_rect`), NOT `winfo_rootx/rooty` — the latter is the client area only, so dragging the window by its title bar would otherwise count as a click; the full frame (title bar + borders) must be excluded. Global hotkeys (`Ctrl+Shift+F9/F10`) + a "minimize on start" option let users avoid clicking the UI mid-recording entirely.
- **Monitor selection defaults to the *primary* monitor** (`_default_monitor_index`, via `is_primary` or the `(0,0)` origin), not list index 0 — otherwise clicks on the primary fall outside a selected secondary monitor's bounds and nothing gets recorded. On a fully-empty session, stop warns "기록 없음" so the user re-checks the monitor.
- **Screenshot heatmap background is captured once at recording start** (`_session_shot`), after briefly `withdraw()`-ing so the app's own window isn't in the shot. The chosen background mode (`_bg_mode`, blank vs screenshot) persists, so **stop rebuilds the heatmap in that mode with the full-session clicks** rather than silently overwriting it with a blank one.
- **Move-event coalescing:** distance accumulates on every raw `on_move`, but a row is logged to `events` only every ~100 ms / ~50 px, bounding file size while keeping the distance total exact.
- **No scipy/matplotlib (unlike `mouse_click_move2.py`):** the heatmap blurs with a hand-rolled numpy separable Gaussian (`_gaussian_blur`, float) and colors with a hand-rolled numpy `turbo` colormap (`_turbo_rgb`) using a density-proportional alpha (transparent where no clicks) plus an adjustable light-blue base wash (`BLUE_BASE_*`, "파란 배경 세기" slider). NOTE: the blur MUST stay in float — an earlier Pillow `ImageFilter.GaussianBlur` on a uint8 `L` image silently rounded the sparse, widely-spread blurred values below 1 down to 0, producing a totally empty heatmap. This keeps the PyInstaller onefile small (~30 MB) and dodges the scipy `_cyutility` hook breakage. Build with `mouse_analytics.spec` (onefile, windowed; excludes scipy/matplotlib/torch/pandas/…).

## Gotchas

- **Windows-only.** Scripts depend on win32 APIs, `pyautogui`/`ImageGrab` screen capture, and Windows paths.
- **Global listeners** may require running as administrator or adding antivirus exceptions — `mouse_click_move2.py` surfaces this to the user on startup.
- **Hardcoded absolute path:** `ctdata_list.py` reads a fixed `D:\` directory (now guarded with an existence check).
- **`fps_1.0.8.py` is a misnomer:** it counts its own polling-loop iterations (~10/s minus explorer time), not real rendered frames. Behavior is intentionally preserved; don't mistake it for a true frame counter.

---

## Development guidelines — Andrej Karpathy's principles

These are the working principles for this repo. They are drawn from Karpathy's public writing/talks and were fact-checked against primary sources (every quote below is verbatim from the cited link). Apply them when changing code here.

### A. AI-assisted coding (how to use the model — including Claude — on this repo)
- **Keep the AI on a tight leash; you are still the bottleneck.** Treat the model as *"an over-eager junior intern savant ... who also bullshits you all the time, has an over-abundance of courage and shows little to no taste for good code."* Review its output; don't grant broad autonomy on code you care about. ([X, Apr 2025](https://x.com/karpathy/status/1915581920022585597))
- **Be slow, defensive, careful, paranoid; never blindly delegate.** *"always taking the inline learning opportunity, not delegating."* ([same](https://x.com/karpathy/status/1915581920022585597))
- **Stuff all relevant context in, then ask for a plan before code.** Load everything relevant, request a few high-level approaches with pros/cons, pick one, *then* ask for the diff. ([same](https://x.com/karpathy/status/1915581920022585597))
- **Work in small, incremental, verifiable chunks.** *"I always go ... in small incremental chunks ... spin this loop very, very fast."* Avoid big unreviewable diffs. ([YC "Software Is Changing (Again)", Jun 2025](https://www.youtube.com/watch?v=LCEmiRjPEtQ))
- **Optimize the generation–verification loop.** The human is the verifier; make verification fast and keep generation leashed so you never rubber-stamp bugs. ([same talk](https://www.youtube.com/watch?v=LCEmiRjPEtQ))
- **Reserve full "vibe coding" for throwaway, low-stakes projects** — not code where correctness, security, or maintenance matter. ([X, Feb 2025](https://x.com/karpathy/status/1886192184808149383))
- **"The hottest new programming language is English"** — specify intent clearly; the prompt/spec is part of the source. ([X, Jan 2023](https://x.com/karpathy/status/1617979122625712128))

### B. Code minimalism & readability
- **Keep the core small enough to read top-to-bottom** — treat line count as a design constraint. ([minGPT](https://github.com/karpathy/minGPT))
- **Reject complexity even when it buys performance:** *"a PR that ... improves performance by 2% but ... 'costs' 500 lines of complex C code ... I may reject ... because the complexity is not worth it."* ([llm.c](https://github.com/karpathy/llm.c))
- **Minimize dependencies; prefer pure, self-contained code.** ([llm.c](https://github.com/karpathy/llm.c))
- **Optimize for hackability and transparency over generality** — write the straightforward version a reader can fork, not an abstract one. ([nanoGPT](https://github.com/karpathy/nanoGPT))
- **Avoid heavyweight libraries "with a billion switches and knobs"** — resist premature abstraction/speculative config. ([makemore](https://github.com/karpathy/makemore))
- **Strip to the algorithmic essence; simplify until you can't.** ([microgpt](http://karpathy.github.io/2026/02/12/microgpt/))
- **Plain, readable code is the primary deliverable** — value code a newcomer can read straight through over clever/compact code. ([nanoGPT](https://github.com/karpathy/nanoGPT))

### C. Engineering discipline (from "A Recipe for Training Neural Networks", 2019)
Phrased as general engineering, not just ML. ([source](https://karpathy.github.io/2019/04/25/recipe/))
- **Assume silent failures; be paranoid and verify everything** — *"thorough, defensive, paranoid, and obsessed with visualizations of basically every possible thing."* "No crash" ≠ "correct."
- **Understand your data/inputs before writing code** — *"begin by thoroughly inspecting your data."*
- **Build an end-to-end skeleton with a dumb baseline first**, then add sophistication.
- **Sanity-check expected values** — derive what a correct system should output and assert it.
- **Prove capacity on a tiny case** (the ML form is "overfit one batch") before scaling up.
- **Fix the random seed** for a reproducible baseline; remove variance as a confound.
- **Add complexity one piece at a time, verifying each step** — "don't throw the kitchen sink at it."

### D. Software 2.0 / 3.0 (conceptual)
- **Treat the dataset as source code; program by data, not logic.** ([Software 2.0](https://karpathy.medium.com/software-2-0-a64152b37c35))
- **Fix learned-system failures by adding labeled examples, not patching code.** ([same](https://karpathy.medium.com/software-2-0-a64152b37c35))
- **Expect silent, unintuitive failures (incl. inherited bias); build monitoring.** ([same](https://karpathy.medium.com/software-2-0-a64152b37c35))
- **Treat LLMs as a new computer you program in English; build partial-autonomy tools with an "autonomy slider" you raise as trust grows; make docs/infra legible to LLMs.** ([YC talk](https://www.youtube.com/watch?v=LCEmiRjPEtQ))

### How these were applied to this repo (2026-06-02 cleanup + refactor)
Concrete, behavior-preserving changes — generated carefully by hand and verified, *not* mass-delegated (per A):
- **Assume silent failures (C):** removed a real silent bug in `click_update_v1.0.9.py` — the `m`/`p`/`r` hotkeys called deleted methods and the `AttributeError` was swallowed by a bare `except`; the dangling handlers were removed (only `s` was ever functional). Made cross-thread Tkinter calls safe via `root.after` in `click_update` and `fps`. Added missing exception handling on failure paths (`psutil` process lookups, file writes, bad DPI input). One **intentional** behavior change: `fps_1.0.8.py` now exits cleanly on window close — the original left a non-daemon worker thread running so the process never exited cleanly while monitoring.
- **Strip to the essence / plain readable code (B):** deleted dead code — the never-called result-window machinery and no-op click stubs in `mouse_distance1.0.6.py`, commented-out "new measurement" feature in `click_update`, and unused imports (`sys`, `time`) and dead Tk variables in `mouse_click_move2.py`.
- **Minimize dependencies / no broken state (B):** `requirements.txt` (renamed from the non-standard `re.text`) now includes the previously-missing `pywin32` and `psutil` that `fps_1.0.8.py` needs.
- **Reject complexity / preserve behavior (A/B):** no features added or rewritten; the packaged `mouse_click_move2.py` got only minimal, invisible cleanup. Known latent quirks that would change behavior to "fix" (e.g. `mouse_distance` redo not re-tracking new objects, `fps` not measuring true frames) were intentionally left and documented rather than silently altered.
