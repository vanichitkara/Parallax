"""
Parallax — Navigator Agent Factory
Creates ADK agents configured for specific personas. Each navigator agent
browses a website as its assigned persona, taking screenshots and interacting
with the page while logging its journey.
"""

import os
import sys
import json
import uuid
import asyncio
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from google.genai import types

from tools.browser import BrowserTool
from personas.definitions import Persona, PERSONAS, get_persona_by_name
from personas.cognitive import CognitiveModel
from models.journey import Journey, JourneyStep, ActionType


# ============================================================
# Per-navigator state management
# ============================================================
_nav_browsers: dict[str, BrowserTool] = {}
_nav_journeys: dict[str, Journey] = {}
_nav_cognitive: dict[str, CognitiveModel] = {}


async def _get_browser(persona_name: str) -> BrowserTool:
    if persona_name not in _nav_browsers:
        browser = BrowserTool()
        await browser.setup()
        _nav_browsers[persona_name] = browser
    return _nav_browsers[persona_name]


def _get_cognitive(persona_name: str) -> CognitiveModel:
    if persona_name not in _nav_cognitive:
        try:
            persona = get_persona_by_name(persona_name)
            threshold = persona.cognitive_traits.frustration_threshold
        except ValueError:
            threshold = 5
        _nav_cognitive[persona_name] = CognitiveModel(
            persona_name=persona_name,
            frustration_threshold=threshold,
        )
    return _nav_cognitive[persona_name]


def _get_journey(persona_name: str, url: str, task: str) -> Journey:
    if persona_name not in _nav_journeys:
        try:
            persona = get_persona_by_name(persona_name)
            age = persona.age
            bg = persona.background
        except ValueError:
            age = 0
            bg = ""
        _nav_journeys[persona_name] = Journey(
            journey_id=str(uuid.uuid4()),
            persona_name=persona_name,
            persona_age=age,
            persona_background=bg,
            target_url=url,
            task=task,
        )
    return _nav_journeys[persona_name]


def _record_step(persona_name: str, action_type: ActionType, details: dict, outcome: str):
    """Record a journey step."""
    if persona_name not in _nav_journeys:
        return
    journey = _nav_journeys[persona_name]
    cognitive = _get_cognitive(persona_name)
    cognitive.step()
    step = JourneyStep(
        step_number=len(journey.steps) + 1,
        observation="(recorded by tool)",
        thinking="(recorded by tool)",
        action_type=action_type,
        action_details=details,
        outcome=outcome,
        frustration_level=cognitive.current_frustration,
    )
    journey.add_step(step)


# ============================================================
# ADK Tool Functions for Navigator
# ============================================================

async def nav_goto(url: str, persona_name: str) -> dict:
    """Navigate the browser to a URL. Returns page info after navigation."""
    browser = await _get_browser(persona_name)
    result = await browser.navigate(url)
    _get_journey(persona_name, url, "")  # Initialize journey
    if result["status"] == "success":
        _record_step(persona_name, ActionType.NAVIGATE, {"url": url},
                     f"Navigated to {url}. Title: {result.get('page_title', '')}")
        return {
            "status": "success",
            "page_title": result.get("page_title", ""),
            "current_url": url,
            "message": f"Navigated to {url}. Describe what you see.",
        }
    return {"status": "error", "error": result.get("error", "Unknown")}


async def nav_click(x: int, y: int, persona_name: str, description: str = "") -> dict:
    """Click at pixel coordinates. Returns what happened."""
    browser = await _get_browser(persona_name)
    result = await browser.click(x, y)
    if result["status"] == "success":
        _record_step(persona_name, ActionType.CLICK,
                     {"x": x, "y": y, "description": description},
                     f"Clicked ({x},{y}): {description}")
        return {
            "status": "success",
            "page_title": result.get("page_title", ""),
            "current_url": result.get("current_url", ""),
            "message": f"Clicked at ({x},{y}). Check if content changed.",
        }
    return {"status": "error", "error": result.get("error", "Unknown")}


async def nav_type(x: int, y: int, text: str, persona_name: str, field_desc: str = "") -> dict:
    """Click a field and type text."""
    browser = await _get_browser(persona_name)
    result = await browser.type_text(x, y, text)
    if result["status"] == "success":
        _record_step(persona_name, ActionType.TYPE,
                     {"x": x, "y": y, "text": text},
                     f"Typed '{text}' at ({x},{y})")
        return {"status": "success", "message": f"Typed '{text}'."}
    return {"status": "error", "error": result.get("error", "Unknown")}


async def nav_scroll(direction: str, persona_name: str, amount: int = 500) -> dict:
    """Scroll the page up or down."""
    browser = await _get_browser(persona_name)
    result = await browser.scroll(direction, amount)
    if result["status"] == "success":
        _record_step(persona_name, ActionType.SCROLL,
                     {"direction": direction}, f"Scrolled {direction}")
        return {"status": "success", "message": f"Scrolled {direction}."}
    return {"status": "error", "error": result.get("error", "Unknown")}


async def nav_key(key: str, persona_name: str) -> dict:
    """Press a keyboard key."""
    browser = await _get_browser(persona_name)
    result = await browser.press_key(key)
    if result["status"] == "success":
        _record_step(persona_name, ActionType.KEY_PRESS,
                     {"key": key}, f"Pressed {key}")
        return {"status": "success", "message": f"Pressed {key}."}
    return {"status": "error", "error": result.get("error", "Unknown")}


async def nav_a11y(persona_name: str) -> dict:
    """Get accessibility info (headings, alt text, interactive elements)."""
    browser = await _get_browser(persona_name)
    return await browser.get_page_info()


async def nav_report_issue(
    persona_name: str, issue_type: str, description: str,
    severity: str, frustration_increase: int = 1
) -> dict:
    """Report a UX issue. Tracks frustration."""
    cognitive = _get_cognitive(persona_name)
    for _ in range(frustration_increase):
        gave_up = cognitive.record_frustration(description)
        if gave_up:
            break
    return {
        "status": "recorded",
        "current_frustration": cognitive.current_frustration,
        "threshold": cognitive.frustration_threshold,
        "should_continue": cognitive.should_continue(),
        "gave_up": cognitive.has_given_up,
    }


async def nav_complete(persona_name: str, success: bool, summary: str) -> dict:
    """Mark task as complete. Saves journey data to shared state."""
    # Clean up browser
    if persona_name in _nav_browsers:
        await _nav_browsers[persona_name].cleanup()
        del _nav_browsers[persona_name]

    cognitive = _get_cognitive(persona_name)
    journey_data = {
        "persona": persona_name,
        "success": success,
        "summary": summary,
        "frustration": cognitive.current_frustration,
        "steps_taken": cognitive.steps_taken,
    }

    if persona_name in _nav_journeys:
        journey = _nav_journeys[persona_name]
        journey.complete(success, None if success else summary)
        journey_data["total_steps"] = journey.total_steps
        journey_data["key_confusions"] = journey.key_confusions[:5]
        journey_data["ux_issues"] = [
            {"step": s.step_number, "observation": s.observation}
            for s in journey.steps if s.ux_issues
        ]

    return journey_data


# ============================================================
# Navigator Agent Factory
# ============================================================

def create_navigator_agent(persona: Persona, target_url: str, task: str) -> Agent:
    """
    Create an ADK Agent configured as a specific persona navigator.
    
    Args:
        persona: The Persona to embody
        target_url: URL to test
        task: Task to perform
    
    Returns:
        Configured ADK Agent
    """
    persona_context = persona.to_prompt_context()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    instruction = f"""WEB NAVIGATION FACTS:
1. Table of Contents / anchor links SCROLL you to a section on the SAME page. 
   This is normal — check if the visible CONTENT changed to verify it worked.
2. After clicking any link: if the content is different, the click worked.
3. Search autocomplete: click a suggestion to navigate.
4. Long pages requiring scrolling are normal.

IMPORTANT: As the AGENT, understand anchor links work correctly. As the PERSONA, 
you can feel confused or surprised — that's valuable UX data. But NEVER give up 
solely because a TOC link scrolled instead of opening a new page.

---

{persona_context}

YOUR TASK:
Test the website at: {target_url}
Goal: {task}

TASK COMPLETION:
- Complete when you've FOUND relevant information AND navigated to at least 
  one related section or page. TOC scrolling COUNTS as navigation.
- Call nav_complete(success=True) when done, or nav_complete(success=False) 
  if you truly cannot proceed.

RULES:
- Maximum 15 steps. Always pass persona_name="{persona.name}" in tool calls.
- Report genuine UX issues via nav_report_issue().
- Stay in character as {persona.name}.
- Start by calling nav_goto("{target_url}", "{persona.name}")."""

    return Agent(
        name=f"navigator_{persona.name.lower()}",
        model=model,
        description=f"Navigator agent for persona: {persona.name}, age {persona.age}. {persona.background}",
        instruction=instruction,
        output_key=f"journey_{persona.name.lower()}",
        tools=[
            nav_goto,
            nav_click,
            nav_type,
            nav_scroll,
            nav_key,
            nav_a11y,
            nav_report_issue,
            nav_complete,
        ],
    )
