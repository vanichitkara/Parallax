"""
Parallax — FastAPI Backend
Serves the pipeline API and streams live progress via WebSocket.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import secrets
import jwt
import bcrypt
from api.gcp_services import gcp_client

from google import genai

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Parallax UX Testing API",
    description="Multi-persona UX testing powered by Gemini Vision + ADK",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active runs and results
_runs: dict[str, dict] = {}
_websocket_clients: dict[str, list[WebSocket]] = {}

OUTPUT_DIR = Path(__file__).parent.parent / "output"

security = HTTPBasic()
JWT_SECRET = os.getenv("JWT_SECRET", "parallax_secret_key_123")

_gemini_client: Optional[genai.Client] = None


def _get_gemini_client() -> Optional[genai.Client]:
    """Lazily create a shared Gemini client, or return None if not configured."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


async def _summarize_task_to_title(task: str) -> Optional[str]:
    """Use Gemini to turn a freeform task into a short dashboard friendly title."""
    client = _get_gemini_client()
    if not client or not task:
        return None

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = (
        "Rewrite the following UX test task as a very short, 4–8 word title "
        "suitable for a dashboard list item. Make it specific and scannable. "
        "Output only the title, no quotes, no extra text.\n\n"
        f"Task: {task}"
    )

    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception:
        # If summarization fails, just fall back to raw task on the client
        return None

def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    # bcrypt expects bytes
    password_bytes = plain_password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_bytes = hashed_password.encode('utf-8')
    else:
        hashed_bytes = hashed_password
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def get_password_hash(password):
    # bcrypt expects bytes and returns bytes
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

async def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    user = await gcp_client.get_user_by_email(credentials.username)
    if not user:
        # Fallback to local admin for bootstrap/local dev
        if credentials.username == os.getenv("API_USERNAME", "admin") and \
           credentials.password == os.getenv("API_PASSWORD", "parallax"):
            return credentials.username
            
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if not verify_password(credentials.password, user.get("hashed_password")):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.on_event("startup")
async def _preload_historical_runs():
    """Scan output/ and load all historical pipeline reports into memory on startup.
    Also fetches recent runs from Firestore."""
    
    # 1. First fetch from Firestore
    fs_runs = await gcp_client.list_runs(limit=20)
    for r in fs_runs:
        run_id = r.get("run_id")
        if run_id:
            r["historical"] = True
            _runs[run_id] = r
            
    # 2. Backfill from local disk if not in Firestore
    if not OUTPUT_DIR.exists():
        return
    reports = sorted(OUTPUT_DIR.glob("pipeline_report_*.json"), key=lambda p: p.stat().st_mtime)
    for report_path in reports:
        try:
            report = json.loads(report_path.read_text())
            run_id = report_path.stem.replace("pipeline_report_", "")[:8]
            if run_id in _runs:
                continue
            personas = [r["persona"].lower() for r in report.get("persona_results", [])]
            journeys = _load_journeys_for_personas_near(report_path.stat().st_mtime, personas)
            _runs[run_id] = {
                "run_id": run_id,
                "url": report.get("url", ""),
                "task": report.get("task", ""),
                "personas": personas,
                "status": "complete",
                "created_at": report.get("timestamp", ""),
                "completed_at": report.get("timestamp", ""),
                "report": report,
                "journeys": journeys,
                "logs": [],
                "historical": True,
            }
        except Exception:
            pass


def _load_journeys_for_personas_near(report_mtime: float, personas: list[str]) -> dict:
    """Load journey.json files whose mtime is close to the report's mtime."""
    journeys = {}
    for persona in personas:
        # Find all journey files for this persona, pick the one closest to report_mtime
        candidates = list(OUTPUT_DIR.glob(f"{persona}_*/journey.json"))
        if not candidates:
            continue
        best = min(candidates, key=lambda p: abs(p.stat().st_mtime - report_mtime))
        try:
            data = json.loads(best.read_text())
            step_dir = best.parent
            screenshots = sorted(step_dir.glob("step_*.png"))
            data["output_dir"] = step_dir.name
            data["screenshot_files"] = [s.name for s in screenshots]
            journeys[persona] = data
        except Exception:
            pass
    return journeys

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class TestRequest(BaseModel):
    url: str
    task: str
    personas: list[str] = ["martha", "raj"]

class TestResponse(BaseModel):
    run_id: str
    status: str
    message: str

class SignUpRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# ---------------------------------------------------------------------------
# Helper: stream stdout lines as WebSocket messages
# ---------------------------------------------------------------------------

async def _broadcast(run_id: str, event: dict):
    """Broadcast an event to all WebSocket clients watching this run."""
    clients = _websocket_clients.get(run_id, [])
    dead = []
    for ws in clients:
        try:
            await ws.send_json(event)
        except (WebSocketDisconnect, RuntimeError):
            dead.append(ws)
    for ws in dead:
        clients.remove(ws)

async def _run_pipeline(run_id: str, url: str, task: str, personas: list[str]):
    """Run the pipeline subprocess and stream output to WebSocket clients."""
    import subprocess
    import sys

    _runs[run_id]["status"] = "running"
    _runs[run_id]["started_at"] = datetime.now().isoformat()

    await _broadcast(run_id, {"type": "status", "status": "running", "run_id": run_id})

    personas_str = ",".join(personas)
    cmd = [
        sys.executable,
        "-u",
        str(Path(__file__).parent.parent / "run_pipeline.py"),
        "--personas", personas_str,
        "--url", url,
        "--task", task,
        "--run-id", run_id,
        "--delay", "10",
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(Path(__file__).parent.parent),
        )

        async for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if line:
                _runs[run_id].setdefault("logs", []).append(line)
                await _broadcast(run_id, {"type": "log", "line": line, "run_id": run_id})

        await process.wait()
        exit_code = process.returncode

        # After pipeline completes, load the latest report
        report = _load_latest_report(run_id=run_id)
        journeys = _load_journeys_for_run(personas, run_id=run_id)

        # Determine final status:
        # - Non-zero exit code is always an error
        status = "complete" if exit_code == 0 else "error"

        _runs[run_id]["status"] = status
        _runs[run_id]["completed_at"] = datetime.now().isoformat()
        _runs[run_id]["report"] = report
        _runs[run_id]["journeys"] = journeys

        # Save to Firestore
        await gcp_client.save_run(run_id, _runs[run_id])

        await _broadcast(run_id, {
            "type": "complete",
            "status": _runs[run_id]["status"],
            "run_id": run_id,
            "report": report,
            "journeys": journeys,
        })

    except Exception as e:
        _runs[run_id]["status"] = "error"
        _runs[run_id]["error"] = str(e)
        await _broadcast(run_id, {"type": "error", "error": str(e), "run_id": run_id})


def _load_latest_report(run_id: str = None) -> Optional[dict]:
    """Load the pipeline report JSON for this run."""
    # If run_id is provided, search for report starting with pipeline_report_{run_id}_
    # Otherwise fall back to most recent: pipeline_report_*
    glob_pattern = f"pipeline_report_{run_id}_*.json" if run_id else "pipeline_report_*.json"
    
    reports = sorted(OUTPUT_DIR.glob(glob_pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if reports:
        try:
            return json.loads(reports[0].read_text())
        except Exception:
            pass
    return None


def _load_journeys_for_run(personas: list[str], run_id: str = None) -> dict:
    """Load the journey.json for each persona in this run."""
    journeys = {}
    for persona in personas:
        # If run_id is provided, search for dir containing it: {persona}_{run_id}_*
        # Otherwise fall back to most recent: {persona}_*
        glob_pattern = f"{persona}_{run_id}_*/journey.json" if run_id else f"{persona}_*/journey.json"
        
        dirs = sorted(
            OUTPUT_DIR.glob(glob_pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if dirs:
            try:
                data = json.loads(dirs[0].read_text())
                # Attach output dir name + screenshot filenames so frontend can build URLs
                step_dir = dirs[0].parent
                screenshots = sorted(step_dir.glob("step_*.png"))
                data["output_dir"] = step_dir.name          # e.g. "martha_20260303_162907"
                data["screenshot_files"] = [s.name for s in screenshots]
                journeys[persona] = data
            except Exception:
                pass
    return journeys

# ---------------------------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------------------------

@app.post("/signup")
async def signup(req: SignUpRequest):
    existing = await gcp_client.get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    hashed = get_password_hash(req.password)
    user_data = {
        "name": req.name,
        "email": req.email.lower(),
        "hashed_password": hashed,
        "created_at": datetime.now().isoformat()
    }
    
    success = await gcp_client.create_user(req.email, user_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create user in Firestore (Check GCP config)")
    
    return {"message": "User created successfully"}

@app.post("/login")
async def login(req: LoginRequest):
    user = await gcp_client.get_user_by_email(req.email)
    if not user or not verify_password(req.password, user.get("hashed_password")):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Return basic auth token for simplicity in our current frontend setup
    import base64
    combined = f"{req.email.lower()}:{req.password}"
    token = base64.b64encode(combined.encode()).decode()
    
    return {
        "token": token,
        "user": {
            "name": user.get("name"),
            "email": user.get("email")
        }
    }

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/test", response_model=TestResponse)
async def start_test(req: TestRequest, username: str = Depends(verify_auth)):
    """Start a new UX test run. Returns a run_id to track progress."""
    run_id = str(uuid.uuid4())[:8]
    short_title = await _summarize_task_to_title(req.task)
    _runs[run_id] = {
        "run_id": run_id,
        "username": username,
        "url": req.url,
        "task": req.task,
        "short_title": short_title,
        "personas": req.personas,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "logs": [],
    }
    # Fire and forget
    asyncio.create_task(_run_pipeline(run_id, req.url, req.task, req.personas))
    return TestResponse(run_id=run_id, status="queued", message=f"Test started. Connect to /ws/{run_id} for live updates.")


@app.get("/results/{run_id}")
async def get_results(run_id: str, username: str = Depends(verify_auth)):
    """Get the full result for a completed run."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return _runs[run_id]


@app.get("/runs")
async def list_runs(username: str = Depends(verify_auth)):
    """List all runs (most recent first) for the current user."""
    # 1. Fetch from Firestore (Historical)
    firestore_runs = await gcp_client.list_runs(limit=50)
    
    # Filter by username and create a set of IDs to avoid duplicates
    runs_map = {r["run_id"]: r for r in firestore_runs if r.get("username") == username}
    
    # 2. Add local in-memory runs (Active/Recent)
    for run_id, run_data in _runs.items():
        if run_data.get("username") == username:
            # Overwrite or add local state (it might be newer/streaming)
            runs_map[run_id] = run_data
            
    # 3. Sort by created_at DESC (latest first)
    sorted_runs = sorted(
        runs_map.values(),
        key=lambda r: r.get("created_at", "0000-00-00"),
        reverse=True,
    )

    return {"runs": sorted_runs}


@app.delete("/runs/{run_id}")
async def delete_run(run_id: str, username: str = Depends(verify_auth)):
    """Delete a run from Firestore and disk."""
    # 1. Check permissions
    run = _runs.get(run_id)
    if not run:
        run = await gcp_client.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    if run.get("username") != username:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 2. Delete from Firestore
    await gcp_client.delete_run(run_id)

    # 3. Remove from memory
    if run_id in _runs:
        del _runs[run_id]

    # 4. Clean up local files
    import shutil
    try:
        # Remove pipeline report
        reports = list(OUTPUT_DIR.glob(f"pipeline_report_{run_id}_*.json"))
        for r in reports:
            r.unlink()
        
        # Remove ux report markdown
        md_reports = list(OUTPUT_DIR.glob(f"ux_report_{run_id}_*.md"))
        for m in md_reports:
            m.unlink()

        # Remove persona journey directories
        # These are usually named {persona}_{run_id}_*
        persona_dirs = list(OUTPUT_DIR.glob(f"*_{run_id}_*"))
        for d in persona_dirs:
            if d.is_dir():
                shutil.rmtree(d)
                
    except Exception as e:
        print(f"⚠️ Error cleaning up local files for {run_id}: {e}")

    return {"message": f"Run {run_id} deleted successfully"}


@app.get("/output/{persona}/screenshots")
async def list_screenshots(persona: str, username: str = Depends(verify_auth)):
    """List screenshot files for the most recent run of a persona."""
    dirs = sorted(
        OUTPUT_DIR.glob(f"{persona}_*/"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not dirs:
        raise HTTPException(status_code=404, detail="No runs found for this persona")
    screenshots = sorted(dirs[0].glob("step_*.png"))
    return {"persona": persona, "dir": dirs[0].name, "screenshots": [s.name for s in screenshots]}


@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for live pipeline progress streaming.
    (WebSocket auth is tricky in browsers, so we rely on run_id being unguessable uuid)."""
    await websocket.accept()

    # Register client
    _websocket_clients.setdefault(run_id, []).append(websocket)

    try:
        # Send current state immediately
        if run_id in _runs:
            await websocket.send_json({"type": "state", "run": _runs[run_id]})
        else:
            await websocket.send_json({"type": "error", "error": "Run not found"})

        # Keep alive until client disconnects
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        # Client potentially closed connection before we finished sending, or just left
        pass
    finally:
        if run_id in _websocket_clients:
            try:
                _websocket_clients[run_id].remove(websocket)
            except ValueError:
                pass


@app.get("/health")
async def health():
    return {"status": "ok", "service": "parallax-api"}


# ---------------------------------------------------------------------------
# Serve output screenshots statically
# ---------------------------------------------------------------------------
if OUTPUT_DIR.exists():
    app.mount("/screenshots", StaticFiles(directory=str(OUTPUT_DIR)), name="screenshots")
