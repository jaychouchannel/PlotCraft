<div align="right">

[English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md)

</div>

# PlotCraft

**AI-powered vector graphics generator for scientific papers · Sandboxed rendering · Publication-ready**

> Describe your figure in natural language. PlotCraft calls an LLM to generate matplotlib code, executes it in an isolated sandbox on the backend, and produces SVG vector graphics at Nature / Cell / Science quality — all API keys encrypted locally, all code running locally, all data staying on your machine.

---

## What is this?

Scientific plotting has long been the most tedious part of paper writing:

- GraphPad / Origin are maze-like, requiring dozens of clicks for one figure;
- Hand-writing matplotlib means juggling color schemes, fonts, statistical annotations, and vector export — endlessly looking up docs;
- AI tools (GPT-4 / Gemini) can write plotting code but can't actually run it — the loop stays inside the chat.

PlotCraft closes the entire pipeline in one go: **natural language → code → render → vector output**.

1. You describe your figure in **one sentence** ("5 curves, x=0~10, y=sin(x), label Time (s) / Amplitude");
2. The backend calls your configured LLM to generate matplotlib Python code;
3. The code runs in an **isolated subprocess sandbox** — forced `Agg` backend, no network, 60s timeout, import blacklist (`os`, `sys`, `socket`, `subprocess`, `requests`, `pathlib`, etc.);
4. The rendered `output.svg` streams back to the frontend for inline preview — downloadable, editable, re-renderable;
5. Every session (prompt + code + SVG) is persisted to local SQLite history — replayable, searchable, cleanable.

**This is not another ChatGPT wrapper.** It's a local-first tool that closes the gap between LLM-generated code and actually *running it to produce a figure*.

---

## Key Features

### 🎯 Vector-first, publication-ready
- Renders SVG directly (`plt.savefig(format="svg", dpi=300, bbox_inches="tight")`), lossless at any zoom, ready for LaTeX / Word / InDesign;
- System prompt enforces **Nature-style color palette** (`#E64B35 #4DBBD5 #00A087 #3C5488 #F39B7F #8491B4`) and typography conventions: axis labels in 12pt, tick labels 10pt, legends 10pt, titles 14pt; semantic significance markers (`*p<0.05`, `**p<0.01`, `***p<0.001`);
- 8 built-in templates: line (with error bars), grouped bar (significance), scatter + regression, box + violin, heatmap, radar, dual-axis line, Kaplan-Meier survival — covering life sciences, materials science, and clinical medicine.

### 🔒 Local encryption · Keys never leave your machine
- API keys are **Fernet-encrypted** (`cryptography` lib) before storage in local SQLite, key held by `ONE_ENCRYPT_KEY` env var;
- Frontend only receives masked `api_key_masked` — plaintext never leaves the server;
- No third-party cloud dependency; data stays fully on your machine in self-hosted deployment.

### 🏝 Sandboxed execution · LLM code stays constrained
- Each render gets a fresh temporary directory (`tempfile.mkdtemp`), cleaned up on exit;
- Environment-level safeguards: `NO_PROXY=*`, forced `MPLBACKEND=Agg` (no GUI popups);
- System prompt prohibits `os / sys / socket / requests / httpx / subprocess / shutil / pathlib / importlib` imports and any file I/O beyond `output.svg`;
- Subprocess killed after 60s timeout to prevent infinite loops;
- On failure, last 500 characters of stderr are returned to the frontend for rapid iteration.

### 🔌 Model-agnostic · Multi-provider unified interface
- Two built-in providers:
  - `openai_compat`: any OpenAI Chat Completions-compatible API (DeepSeek, Qwen, Moonshot, Zhipu, Together, OpenRouter, local vLLM, etc.);
  - `gemini`: Google Gemini (`google-genai` SDK);
- `replicate` interface reserved for future photorealistic bitmap model integration;
- Models can be added, updated, and deleted from the UI at any time — no code changes needed.

### 📝 Template system · Inheritable presets, custom overrides
- 8 built-in templates with `system_prompt` + `user_template` placeholders (e.g., `{xlabel}`, `{series}`), auto-seeded into SQLite at startup;
- Built-in templates are read-only (to prevent accidental edits); clone them for customization;
- Templates are categorized, filterable by category in the frontend dropdown;
- The prompt editor pre-fills from the template but remains freely editable — templates are a starting point, not a ceiling.

### 🖥 Modern frontend · Editable code, re-render at zero LLM cost
- React 19 + TypeScript 7 + Vite 8 + Tailwind 4;
- **CodeMirror** editor (VSCode Dark theme + Python syntax highlighting) for online code editing;
- "Re-render" button POSTs modified code to `/api/generate/render` — no LLM quota consumed;
- SVG preview via `dangerouslySetInnerHTML` (sandbox already air-gaps networks; SVG is local-only), right-click to save;
- One-click downloads: `.svg` vector and `.py` source code.

### 🗂 Full history · Never lose an experiment
- Every generation (success, failure, or code-only) lands in the `generations` table with `model_id`, `template_id`, `user_input`, `generated_code`, `output_svg`, `status`, `error`, and `created_at`;
- History page shows last 50 records, supports single delete and full clear;
- Failed runs are preserved for side-by-side debugging.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI · Pydantic · aiosqlite · aiofiles · cryptography · openai · google-genai |
| Rendering | matplotlib (Agg backend) · numpy · pandas · scipy (as needed) |
| Frontend | React 19 · TypeScript 7 · Vite 8 · Tailwind 4 · @uiw/react-codemirror · react-router-dom 7 |
| Storage | SQLite (model configs / templates / history) |
| Sandbox | tempfile + subprocess + Agg + no-network + timeout kill |

---

## Project Structure

```
PlotCraft/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI entry, CORS + lifespan + template seeding
│   │   ├── config.py            Environment variable loader
│   │   ├── crypto.py            Fernet encryption/decryption
│   │   ├── db.py                aiosqlite connection + table init
│   │   ├── executor.py          Sandbox execution (core security boundary)
│   │   ├── prompts.py           Scientific plotting system prompt template
│   │   ├── models.py            Pydantic data models
│   │   ├── providers/
│   │   │   ├── base.py          Provider abstract base class
│   │   │   ├── factory.py       Provider factory
│   │   │   ├── openai_compat.py OpenAI-compatible protocol
│   │   │   └── gemini.py        Google Gemini
│   │   └── routes/
│   │       ├── generate.py       /api/generate + /api/generate/render
│   │       ├── history.py        History CRUD
│   │       ├── models.py         Model config CRUD
│   │       └── templates.py      Template CRUD + startup seeding
│   ├── templates_seed/           8 built-in figure JSON templates
│   │   ├── 01_line_with_errorbar.json
│   │   ├── 02_grouped_bar_significance.json
│   │   ├── 03_scatter_regression.json
│   │   ├── 04_box_violin.json
│   │   ├── 05_heatmap.json
│   │   ├── 06_radar.json
│   │   ├── 07_dual_axis_line.json
│   │   └── 08_kaplan_meier.json
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx              Routes + navigation
│   │   ├── main.tsx             Entry point
│   │   ├── index.css            Tailwind
│   │   ├── lib/api.ts           Frontend API client
│   │   ├── components/
│   │   │   └── SetupBanner.tsx  Setup prompt when no key is configured
│   │   └── pages/
│   │       ├── Generate.tsx     Main generation page
│   │       ├── History.tsx      History page
│   │       ├── ModelConfig.tsx  Model configuration page
│   │       └── Templates.tsx    Template management page
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
└── .gitignore
```

---

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# Generate a Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Write the key to .env
cp .env.example .env
# Edit .env, paste the key into ONE_ENCRYPT_KEY=
# You can also change HOST / PORT / DB_PATH

# Start the server
uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` to see the OpenAPI docs.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (default `http://localhost:5173`).

### 3. Configure a Model

Go to the "Models" page and add a model:

- **OpenAI-compatible** (DeepSeek example)
  - `provider`: `openai_compat`
  - `base_url`: `https://api.deepseek.com/v1`
  - `model_name`: `deepseek-chat`
  - `api_key`: your DeepSeek key
- **Gemini**
  - `provider`: `gemini`
  - `model_name`: `gemini-2.5-flash`
  - `api_key`: Google AI Studio key
- **Local vLLM / Ollama (OpenAI-compatible)**
  - `base_url`: `http://localhost:8000/v1` (vLLM) or `http://localhost:11434/v1` (Ollama)
  - `api_key`: any non-empty string for local services

### 4. Generate Your First Figure

1. Go to the "Generate" page, select a model + a template (e.g., "Scatter + Linear Regression");
2. The template prompt auto-fills into the editor; adapt it to your data:
   ```
   Draw a scatter plot with linear regression:
   - x: cell diameter (μm), y: protein expression (RFU)
   - 30 samples, scatter with noise
   - fit line + 95% confidence interval shading
   - show R² and p-value on the chart
   - Nature-style color palette
   ```
3. Click "Generate" — the SVG preview appears on the right in seconds;
4. Happy → download `.svg` / `.py`; not happy → edit the code in CodeMirror → click "Re-render" (zero LLM cost).

---

## Demo

The figures below were generated entirely by PlotCraft — natural language in, matplotlib code generated by an LLM, rendered in the backend sandbox, exported as SVG (re-rasterized here for GitHub preview).

<p align="center">
  <img src="png/808aa00d130c44832a83f8700828c46e.png" width="32%" alt="demo figure 2" />
  <img src="png/5564f828049e55775e89289333cddf9b.png" width="32%" alt="demo figure 3" />
</p>
<p align="center"><em>Left: multi-series line with error bars · Middle: grouped bar with significance markers · Right: scatter with linear regression + 95% CI</em></p>

---

## Built-in Template List

| # | Category | Template Name | Typical Use Case |
|---|---|---|---|
| 01 | Line | Multi-series line with error bars | Time course, dose-response curves |
| 02 | Bar | Grouped bar with significance | Multi-group comparisons + ANOVA markers |
| 03 | Scatter | Scatter + linear regression | Correlation analysis, R² / p-value |
| 04 | Distribution | Box + violin | Inter-group distribution comparison |
| 05 | Heatmap | Heatmap | Gene expression, confusion matrix |
| 06 | Radar | Radar chart | Multi-dimensional score comparison |
| 07 | Dual-axis | Dual-axis line | Different units on one chart (temp vs yield) |
| 08 | Survival | Kaplan-Meier | Survival analysis + log-rank test |

---

## Security Model

| Risk | Mitigation |
|---|---|
| LLM-generated malicious code reads local files | System prompt bans `os / sys / pathlib / subprocess / open()` imports; subprocess runs in an isolated temp directory |
| LLM sends data to public networks | System prompt bans `socket / requests / httpx`; env sets `NO_PROXY=*`; downstream network namespaces can be added |
| Infinite loop / deadlock exhausts CPU | Subprocess killed after 60s timeout |
| API key leakage | Fernet symmetric encryption to database; frontend only sees masked strings |
| SVG XSS | SVG rendered inline in frontend DOM; sandbox has no network; no external resource loading |

> ⚠️ **Production note**: CORS defaults to `allow_origins=["*"]`, suitable for local single-user use. For multi-user or public deployments, change to a whitelist and add authentication.

---

## When to Use

**Good for**
- Individual researchers / graduate students / postdocs producing paper figures quickly
- Lab-internal shared plotting tool (self-hosted on a group server)
- Teaching: showing students how an LLM maps natural language to executable matplotlib code

**Not suitable for**
- Enterprise multi-user scenarios requiring compliance audit trails (no authentication / audit log)
- Replacing professional publishing tools (Adobe Illustrator can still polish SVGs)
- Interactive 3D or large-scale WebGL rendering (sandbox only runs matplotlib)

---

## Roadmap

- [ ] PDF / EPS export (currently SVG only)
- [ ] Batch generation (multi-panel figures from one prompt)
- [ ] Figure parameter cloning ("same style, different data")
- [ ] Replicate / FAL photorealistic provider
- [ ] Client-side sandpack-js pre-rendering to reduce Python subprocess overhead

---

## License

This repository does not currently declare an open-source license. Until a LICENSE file is added, all rights are reserved by the author by default. You may refer to the code for reference, but please contact the author for permission before redistribution, derivative work, or commercial use.

---

## Acknowledgements

- Color inspiration: [ggsci — Nature journal palettes](https://github.com/nanxstats/ggsci)
- Template design: matplotlib gallery + common paper figure conventions
- Sandbox inspiration: Jupyter `%%script` / `nbconvert` isolate mode
