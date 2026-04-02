## Project layout

| Path | Purpose |
|------|---------|
| `frontend/public/` | Static site served locally and deployed to Azure Static Web Apps |
| `frontend/src/` | Front-end source (framework code, bundles) as you grow beyond plain HTML/CSS/JS |
| `backend/app/` | Backend application package (API, services) |
| `backend/tests/` | Backend tests |
| `api/` | Optional Azure Static Web Apps Functions (set `api_location` in the workflow when used) |

The prototype script `echofy_model_prototype.py` lives in `backend/` at the repo root of that folder.

## Local development (localhost)

| Service | Port | How to run |
|---------|------|------------|
| Both at once | **3000** + **5000** | `start.bat` (Windows) or `./start.sh` (macOS / Linux) opens two terminal windows |
| Frontend only | **3000** | `start.bat frontend` or `./start.sh frontend` (optional: `PORT=8080 ./start.sh frontend`) |
| Backend only | **5000** | `start.bat backend` or `./start.sh backend` (optional: `PORT=5001 ./start.sh backend`) |

Activate `.venv` and run `pip install -r requirements.txt` first. On Linux, `./start.sh` needs a supported terminal (GNOME Terminal, Konsole, XFCE Terminal, or xterm). Check the API with [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health).

<hr>

## Python virtual environment (`.venv`)

Create a virtual environment in the project root so dependencies stay isolated (says in the project not on your whole system). The `.venv` folder is gitignored.

### Windows (PowerShell or Command Prompt)

From the repo root:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `python` is not found, try `py -3` instead of `python`.

To leave the environment: `deactivate`

### macOS / Linux (Terminal)

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

To leave the environment: `deactivate`
