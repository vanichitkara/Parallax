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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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


@app.on_event("startup")
async def _preload_historical_runs():
    """Scan output/ and load all historical pipeline reports into memory on startup."""
    if not OUTPUT_DIR.exists():
        return
    reports = sorted(OUTPUT_DIR.glob("pipeline_report_*.json"), key=lambda p: p.stat().st_mtime)
    for report_path in reports:
        try:
            report = json.loads(report_path.read_text())
            # Derive a stable run_id from the filename timestamp
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
        except Exception:
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
        str(Path(__file__).parent.parent / "run_pipeline.py"),
        "--personas", personas_str,
        "--url", url,
        "--task", task,
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
        report = _load_latest_report()
        journeys = _load_journeys_for_run(personas)

        _runs[run_id]["status"] = "complete" if exit_code == 0 else "error"
        _runs[run_id]["completed_at"] = datetime.now().isoformat()
        _runs[run_id]["report"] = report
        _runs[run_id]["journeys"] = journeys

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


def _load_latest_report() -> Optional[dict]:
    """Load the most recently created pipeline report JSON."""
    reports = sorted(OUTPUT_DIR.glob("pipeline_report_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if reports:
        try:
            return json.loads(reports[0].read_text())
        except Exception:
            pass
    return None


def _load_journeys_for_run(personas: list[str]) -> dict:
    """Load the most recent journey.json for each persona."""
    journeys = {}
    for persona in personas:
        dirs = sorted(
            OUTPUT_DIR.glob(f"{persona}_*/journey.json"),
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
# Routes
# ---------------------------------------------------------------------------

@app.post("/test", response_model=TestResponse)
async def start_test(req: TestRequest):
    """Start a new UX test run. Returns a run_id to track progress."""
    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = {
        "run_id": run_id,
        "url": req.url,
        "task": req.task,
        "personas": req.personas,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "logs": [],
    }
    # Fire and forget
    asyncio.create_task(_run_pipeline(run_id, req.url, req.task, req.personas))
    return TestResponse(run_id=run_id, status="queued", message=f"Test started. Connect to /ws/{run_id} for live updates.")


@app.get("/results/{run_id}")
async def get_results(run_id: str):
    """Get the full result for a completed run."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return _runs[run_id]


@app.get("/runs")
async def list_runs():
    """List all runs (most recent first)."""
    runs = sorted(_runs.values(), key=lambda r: r.get("created_at", ""), reverse=True)
    return {"runs": runs}


@app.get("/output/{persona}/screenshots")
async def list_screenshots(persona: str):
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
    """WebSocket endpoint for live pipeline progress streaming."""
    await websocket.accept()

    # Register client
    _websocket_clients.setdefault(run_id, []).append(websocket)

    # Send current state immediately
    if run_id in _runs:
        await websocket.send_json({"type": "state", "run": _runs[run_id]})
    else:
        await websocket.send_json({"type": "error", "error": "Run not found"})

    try:
        # Keep alive until client disconnects
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
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
