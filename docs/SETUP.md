# Setup

The full install for each OS, how to run each part, the settings, and how to keep the data current. The README's Quick start is the short version of this.

## Requirements

- Windows, macOS or Linux
- Python 3.12 or newer
- [bun](https://bun.sh) for the frontend
- Internet access to arknights.wiki.gg
- [Ollama](https://ollama.com), for screenshots and relationship labels, with about 6 GB of disk for the two models

## Install

macOS or Linux:

```bash
git clone https://github.com/AtlasMint/arknights-lore-compendium.git
cd arknights-lore-compendium
python3 -m venv .venv
source .venv/bin/activate
WITH_EXTENSION=0 pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
git clone https://github.com/AtlasMint/arknights-lore-compendium.git
cd arknights-lore-compendium
py -m venv .venv
.venv\Scripts\Activate.ps1
$env:WITH_EXTENSION = "0"; pip install -r requirements.txt
```

`WITH_EXTENSION=0` lets pip install `mwparserfromhell` without a C compiler where it has no prebuilt wheel (Python 3.14, Windows on ARM). It then uses its pure-Python parser, which is about 1.5× slower and still under a second per graph. Where a wheel exists, the setting does nothing.

## Ollama and the models

Two open models run on your machine: `qwen3.5:2b` (2.7 GB) reads screenshots, and `qwen3.5:4b` (3.4 GB) labels the map's links. On macOS:

```bash
brew install ollama && brew services start ollama
ollama pull qwen3.5:2b
ollama pull qwen3.5:4b
```

On Windows, `winget install Ollama.Ollama`; on Linux, `curl -fsSL https://ollama.com/install.sh | sh`. Then the same two `ollama pull` commands. Ollama keeps running in the background, and each model loads when first needed.

Without Ollama the map still builds from typed keywords; screenshots can't be read and links stay unlabelled.

## Run

With the venv active:

```bash
# Term index: every title and redirect, about 1-2 minutes. The first graph build runs this if you skip it.
python -m backend.index.build_index

# Command line
python -m backend.cli --seeds "Amiya,Reunion" --depth 1
python -m backend.cli --lookup "Reunion Movement"

# Web UI: the API in one terminal...
python -m flask --app backend.app run --port 5001
# ...and the frontend in another, then open http://localhost:5173
cd frontend
bun install
bun run dev
```

## Settings

All in `backend/config.py`:

| Setting | What it is |
|---|---|
| `WIKI_API`, `WIKI_FILES` | The wiki's API and file URLs |
| `USER_AGENT` | Sent with every wiki request; add a contact before sharing the tool |
| `REQUEST_DELAY` | Seconds between wiki requests |
| `CACHE_TTL` | Seconds before a cached page is fetched again (7 days) |
| `DB_PATH` | The SQLite file for pages, the term index, readings, labels and icons |
| `DEPTH`, `MAX_NODES` | Link hops out from the seeds, and the graph's size after pruning |
| `RECIPROCAL_BONUS`, `SECTION_BONUS` | Edge weights for pages that link each other or share a section |
| `SPEAKER_WEIGHT` | How much more a screenshot's speaker counts in the ranking |
| `MAX_SEEDS` | Most keywords one graph takes |
| `GLOBAL_LAUNCH` | Global's first day, the release date of Prologue to Episode 04 |
| `READER_URL`, `READER_MODEL` | Ollama, and the model that reads screenshots |
| `LABEL_MODEL` | The model that labels links |
| `MAX_UPLOAD_MB` | Largest screenshot the API takes |

## Keeping data current

- Rerun `python -m backend.index.build_index` now and then to pick up new wiki pages.
- Restart the API to pick up newly released stories; the stories data is kept for as long as it runs.
- The In-game tab's years are a checked-in table, `backend/story_years.json`, corrected by hand. When a new story comes out, see what the wiki says and merge it in by hand:

  ```bash
  python -m backend.stories    # years seeded from the Timeline page and the synopses
  ```

## Troubleshooting

- **Windows:** if PowerShell won't run `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
- **Debian and Ubuntu:** if creating the venv fails, run `sudo apt install python3-venv`.
- **macOS with the python.org installer:** if wiki requests fail with `CERTIFICATE_VERIFY_FAILED`, run `Install Certificates.command` from the Python folder in Applications.
- **Port 5001** is used because macOS AirPlay holds 5000. To use another port, change it in the `flask` command and in `frontend/vite.config.js`.
- **"Model not pulled"** in the status line or the map legend: run the `ollama pull` it names.
