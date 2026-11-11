# Run and render

Resolve SKILL_DIR to this installed skill's absolute directory. Use a separate WORK directory for each user task. All scripts accept absolute paths. Install missing Python dependencies with the active interpreter: `python3 -m pip install pillow imageio-ffmpeg certifi` (prefer a task-local virtual environment).

## Model generation

Fetch current metadata (no key needed):

```sh
python3 "$SKILL_DIR/scripts/run_models.py" --catalog "$WORK/models.json"
```

Inspect IDs, pricing, context length, `top_provider.max_completion_tokens`, and supported parameters. If the maximum is absent, consult current provider documentation instead of assuming unlimited output. Respect user model choices and budgets. Do not use batch routes for measured interactive latency.

Write request.json with the original prompt text (not the prompt file path):

```json
{
  "prompt": "The exact user prompt",
  "max_tokens": 64000,
  "models": [{"id": "provider/verified-model-id", "max_tokens": 64000}]
}
```

Run `python3 "$SKILL_DIR/scripts/run_models.py" --config "$WORK/request.json" --output "$WORK/runs"`. Use an existing authorized environment variable or hidden TTY prompt for the key. Do not shell-echo secrets. Requests run concurrently (default 3, max 4). Each request creates an immutable attempt directory with request, raw response, extracted scene, and metrics. The helper does not silently retry. Exit 2 means at least one incomplete/request-failed result; inspect records before deciding whether to retry. HTML completion is preliminary; browser validation is mandatory. Missing API cost is unknown, never zero; obtain generation billing data or clearly mark pending before final rendering.

To retry, make a config containing only the affected model, with an increased supported limit. Preserve the original attempt and record why. Default maximum: 2 generation attempts per model for one user request. A user-requested rerun is a new authorization, not an excuse for endless automatic retries.

## Browser and capture

Read the installed ego-browser skill before using it. Serve the WORK directory with Python HTTP server bound to localhost. Create one TaskSpace, print its ID, reuse its page for each model. Use the same viewport/aspect and canvas recording duration across models. The original workflow used a roughly 1274×783 viewport, preserved using contain in square panels. Observe actual viewport dimensions; do not assume CDP emulation persists across navigation.

Inspect screenshot and runtime errors before capture. Save unmodified source files. `scripts/record.js` is a working template for a single animated canvas; replace cfg in a per-run copy and run `ego-browser nodejs < /absolute/record-copy.js`. This CLI takes source text/stdin, not a script filename as a source argument. Do not pass guessed Playwright methods. Screenshots alone are not motion verification.

Canvas capture omits DOM UI. If DOM is only unrelated model-added controls, note the omission. For tasks where DOM is part of the actual output (websites, dashboards, multiple canvases), capture the complete viewport with browser CDP screencast or a supported screen recorder instead; preserve its real timing. Never replace a failed canvas with your own illustration.

Remux/encode recorded WebM to MP4 first with FFmpeg, because browser WebM may lack duration metadata:

```sh
FFMPEG=$(python3 -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')
"$FFMPEG" -y -i scene.webm -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p scene.mp4
```

Inspect first/middle/last frames, legs and scenery changes, blank frames, static lead-in and usable duration. Choose trims and a common duration without freeze-frame padding. Close the task space when capture is complete.

## Render configuration

Copy assets into WORK/assets, or use absolute paths to the skill assets. All relative config paths resolve against the config file directory. Font and Offloop mark come from the skill assets. Example schema below is illustrative only: populate real models, measured metrics and source paths. Do not reuse example totals.

```json
{
  "panel_size": 1080,
  "fps": 30,
  "duration_seconds": 6,
  "speed": 1.5,
  "animation_seconds": 5,
  "time_scale_seconds": 250,
  "cost_scale_usd": 0.5,
  "music": "assets/music.wav",
  "output": "output/comparison.mp4",
  "models": [
    {"name":"Actual model name", "logo":"assets/gemini.png", "video":"scene.mp4", "time_seconds":239.8, "cost_usd":0.491, "cost_decimals":4, "trim_start_seconds":1, "fit":"contain"}
  ]
}
```

Supply 2–4 distinct model entries. 2/3 are one row, 4 are 2×2; order is row-major. Each panel is square. `trim_end_seconds` optionally limits usable source; `background` optionally overrides sampled background; `ffmpeg` optionally points to a compatible executable. Music null gives silence. Shared time/cost maxima must contain all measured totals; recompute after every rerun. Keep title spelling and logos faithful. Prefer the supplied marks for Google, OpenAI, Anthropic, DeepSeek, Tencent; other providers require an authentic asset or text-only adaptation of the renderer.

Run with --check, then draft at panel_size=360, then full size:

```sh
python3 "$SKILL_DIR/scripts/render.py" --config "$WORK/config.json" --check
python3 "$SKILL_DIR/scripts/render.py" --config "$WORK/config.json"
```

Verify metadata with `imageio_ffmpeg.read_frames` (first yielded item), inspect contact sheet at start/middle/end and final counters. It reports video dimensions, fps, duration, codec and audio codec without ffprobe. Read frames only as needed and close the generator. Source durations must cover selected playback span, or explicitly inspect looping for jumps.

## Report and delivery

Record model IDs, request timestamps/attempts, original prompt/system instruction, output/reasoning budgets, finish reasons, usage/cost, measured API wall time, model/code changes, viewport, trims, speed, and capture method. TIME excludes browser loading and video rendering. COST is response usage.cost or verified generation billing, not a token-price estimate presented as actual charge. Report each successful attempt and cumulative spend separately. Do not claim a provider's reasoning defaults are controlled if they differ.

If user requests replacing an existing video, back it up, render a new candidate, verify, then replace the original path. Return a playable absolute-path MP4 embed and download link. Never include an API key in artifacts.
