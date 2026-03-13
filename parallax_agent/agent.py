"""
Parallax — ADK Agent Entry Point
This is the main agent file that ADK discovers via `adk web` or `adk run`.
For Day 1: Single persona navigator agent that screenshots → analyzes → acts.
"""

import json
import asyncio
import uuid
import base64
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from google.genai import types

from tools.browser import BrowserTool
from personas.definitions import PERSONAS, get_persona_by_name, Persona
from personas.cognitive import CognitiveModel
from models.journey import Journey, JourneyStep, ActionType


# ============================================================
# Global state for the browser tool (shared across tool calls)
# ============================================================
_browser_instances: dict[str, BrowserTool] = {}
_journeys: dict[str, Journey] = {}
_cognitive_models: dict[str, CognitiveModel] = {}


# ============================================================
# ADK Tool Functions
# ============================================================

async def navigate_to_url(url: str, persona_name: str) -> dict:
    """
    Navigate the browser to a URL and take a screenshot.
    This is the first action a persona takes when starting a test.
    
    Args:
        url: The URL to navigate to (e.g., "https://example.com")
        persona_name: Name of the persona using the browser
        
    Returns:
        dict with status, page_title, current_url, and a description of what happened.
              The screenshot is sent to Gemini Vision automatically.
    """
    browser = await _get_or_create_browser(persona_name)
    result = await browser.navigate(url)
    
    if result["status"] == "success":
        # Store screenshot for later
        _store_step(persona_name, ActionType.NAVIGATE, 
                   {"url": url}, 
                   f"Navigated to {url}. Page title: {result.get('page_title', 'Unknown')}")
        return {
            "status": "success",
            "page_title": result.get("page_title", ""),
            "current_url": url,
            "message": f"Successfully navigated to {url}. A screenshot of the page has been taken. Describe what you see and decide your next action based on your persona's characteristics.",
        }
    else:
        return {
            "status": "error",
            "error": result.get("error", "Unknown error"),
            "message": f"Failed to navigate to {url}: {result.get('error', 'Unknown error')}",
        }


async def click_element(x: int, y: int, persona_name: str, description: str = "") -> dict:
    """
    Click at specific pixel coordinates on the page.
    
    Args:
        x: X coordinate (horizontal position in pixels from left)
        y: Y coordinate (vertical position in pixels from top)  
        persona_name: Name of the persona performing the click
        description: What the persona thinks they are clicking on
        
    Returns:
        dict with status and what happened after clicking.
    """
    browser = await _get_or_create_browser(persona_name)
    result = await browser.click(x, y)
    
    if result["status"] == "success":
        _store_step(persona_name, ActionType.CLICK,
                   {"x": x, "y": y, "description": description},
                   f"Clicked at ({x}, {y}): {description}")
        return {
            "status": "success",
            "clicked_at": {"x": x, "y": y},
            "description": description,
            "page_title": result.get("page_title", ""),
            "current_url": result.get("current_url", ""),
            "message": f"Clicked at coordinates ({x}, {y}). A new screenshot has been taken. Describe what changed and decide your next action.",
        }
    else:
        return {
            "status": "error",
            "error": result.get("error", "Unknown error"),
        }


async def type_into_field(x: int, y: int, text: str, persona_name: str, field_description: str = "") -> dict:
    """
    Click on a text field and type text into it.
    
    Args:
        x: X coordinate of the text field
        y: Y coordinate of the text field
        text: The text to type
        persona_name: Name of the persona typing
        field_description: What field the persona thinks they are typing into
        
    Returns:
        dict with status and what happened after typing.
    """
    browser = await _get_or_create_browser(persona_name)
    result = await browser.type_text(x, y, text)
    
    if result["status"] == "success":
        _store_step(persona_name, ActionType.TYPE,
                   {"x": x, "y": y, "text": text, "field": field_description},
                   f"Typed '{text}' into field at ({x}, {y}): {field_description}")
        return {
            "status": "success",
            "typed": text,
            "field": field_description,
            "message": f"Typed '{text}' into the field. A new screenshot has been taken. Describe what you see and decide your next action.",
        }
    else:
        return {
            "status": "error",
            "error": result.get("error", "Unknown error"),
        }


async def scroll_page(direction: str, persona_name: str, amount: int = 300) -> dict:
    """
    Scroll the page up or down.
    
    Args:
        direction: "up" or "down"
        persona_name: Name of the persona scrolling
        amount: How many pixels to scroll (default 300)
        
    Returns:
        dict with status and what's now visible.
    """
    browser = await _get_or_create_browser(persona_name)
    result = await browser.scroll(direction, amount)
    
    if result["status"] == "success":
        _store_step(persona_name, ActionType.SCROLL,
                   {"direction": direction, "amount": amount},
                   f"Scrolled {direction} by {amount}px")
        return {
            "status": "success",
            "direction": direction,
            "message": f"Scrolled {direction}. A new screenshot has been taken. Describe what new content is now visible and decide your next action.",
        }
    else:
        return {
            "status": "error",
            "error": result.get("error", "Unknown error"),
        }


async def press_keyboard_key(key: str, persona_name: str) -> dict:
    """
    Press a keyboard key. Useful for Tab navigation, Enter to submit, Escape to close, etc.
    
    Args:
        key: The key to press (e.g., "Tab", "Enter", "Escape", "ArrowDown", "Control+K")
        persona_name: Name of the persona pressing the key
        
    Returns:
        dict with status and what changed.
    """
    browser = await _get_or_create_browser(persona_name)
    result = await browser.press_key(key)
    
    if result["status"] == "success":
        _store_step(persona_name, ActionType.KEY_PRESS,
                   {"key": key},
                   f"Pressed key: {key}")
        return {
            "status": "success",
            "key": key,
            "message": f"Pressed {key}. A new screenshot has been taken. Describe what changed and decide your next action.",
        }
    else:
        return {
            "status": "error",
            "error": result.get("error", "Unknown error"),
        }


async def get_accessibility_info(persona_name: str) -> dict:
    """
    Get accessibility information about the current page.
    Returns heading structure, images without alt text, and interactive elements.
    Useful for screen reader persona (Sam) to understand page structure.
    
    Args:
        persona_name: Name of the persona requesting info
        
    Returns:
        dict with heading structure, alt text status, and interactive elements.
    """
    browser = await _get_or_create_browser(persona_name)
    result = await browser.get_page_info()
    
    if result["status"] == "success":
        _store_step(persona_name, ActionType.SCREENSHOT,
                   {"type": "accessibility_audit"},
                   f"Accessibility audit: {len(result.get('headings', []))} headings, "
                   f"{result.get('images_without_alt', 0)} images without alt text")
        return result
    else:
        return {
            "status": "error",
            "error": result.get("error", "Unknown error"),
        }


async def report_finding(
    persona_name: str,
    finding_type: str,
    description: str,
    severity: str,
    frustration_increase: int = 1,
) -> dict:
    """
    Report a UX issue or observation. Call this whenever you encounter something
    confusing, broken, or poorly designed.
    
    Args:
        persona_name: Your persona name
        finding_type: Category - one of: navigation, readability, accessibility, 
                      visual_design, interaction, language, color, mobile, cognitive_load
        description: Detailed description of the issue from the persona's perspective
        severity: One of: critical, high, medium, low, info
        frustration_increase: How much this increased frustration (0-3)
        
    Returns:
        dict with current frustration level and whether to continue.
    """
    cognitive = _get_or_create_cognitive(persona_name)
    
    for _ in range(frustration_increase):
        gave_up = cognitive.record_frustration(description)
        if gave_up:
            break
    
    cognitive.step()
    should_continue = cognitive.should_continue()
    
    return {
        "status": "recorded",
        "finding_type": finding_type,
        "severity": severity,
        "current_frustration": cognitive.current_frustration,
        "frustration_threshold": cognitive.frustration_threshold,
        "should_continue": should_continue,
        "gave_up": cognitive.has_given_up,
        "message": (
            f"Finding recorded. Frustration: {cognitive.current_frustration}/{cognitive.frustration_threshold}. "
            + ("You have GIVEN UP due to frustration. Call complete_task with success=false."
               if cognitive.has_given_up
               else f"Steps taken: {cognitive.steps_taken}/{cognitive.max_steps}. Continue browsing.")
        ),
    }


async def complete_task(persona_name: str, success: bool, summary: str) -> dict:
    """
    Mark the task as complete (either successfully or by giving up).
    Call this when you have either completed the task or decided to give up.
    
    Args:
        persona_name: Your persona name
        success: True if you completed the task, False if you gave up
        summary: A summary of how the experience went from your persona's perspective
        
    Returns:
        dict with the journey summary.
    """
    # Clean up browser
    if persona_name in _browser_instances:
        await _browser_instances[persona_name].cleanup()
        del _browser_instances[persona_name]
    
    cognitive = _get_or_create_cognitive(persona_name)
    
    result = {
        "status": "completed",
        "persona": persona_name,
        "success": success,
        "summary": summary,
        "cognitive_state": cognitive.get_state_summary(),
    }
    
    # Get journey if exists
    if persona_name in _journeys:
        journey = _journeys[persona_name]
        journey.complete(success, None if success else summary)
        result["total_steps"] = journey.total_steps
        result["max_frustration"] = journey.max_frustration_reached
        result["key_confusions"] = journey.key_confusions[:5]
    
    return result


# ============================================================
# Helper functions  
# ============================================================

async def _get_or_create_browser(persona_name: str) -> BrowserTool:
    """Get or create a browser instance for a persona."""
    if persona_name not in _browser_instances:
        browser = BrowserTool()
        await browser.setup()
        _browser_instances[persona_name] = browser
    return _browser_instances[persona_name]


def _get_or_create_cognitive(persona_name: str) -> CognitiveModel:
    """Get or create a cognitive model for a persona."""
    if persona_name not in _cognitive_models:
        try:
            persona = get_persona_by_name(persona_name)
            threshold = persona.cognitive_traits.frustration_threshold
        except ValueError:
            threshold = 5
        _cognitive_models[persona_name] = CognitiveModel(
            persona_name=persona_name,
            frustration_threshold=threshold,
        )
    return _cognitive_models[persona_name]


def _store_step(persona_name: str, action_type: ActionType, details: dict, outcome: str):
    """Store a journey step."""
    if persona_name not in _journeys:
        _journeys[persona_name] = Journey(
            journey_id=str(uuid.uuid4()),
            persona_name=persona_name,
            persona_age=0,
            persona_background="",
            target_url="",
            task="",
        )
    
    journey = _journeys[persona_name]
    cognitive = _get_or_create_cognitive(persona_name)
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
# Build the persona prompt
# ============================================================

def _build_navigator_instruction(persona: Persona, target_url: str, task: str) -> str:
    """Build a detailed instruction for the navigator agent based on persona."""
    persona_context = persona.to_prompt_context()
    
    return f"""{persona_context}

YOUR TASK:
You are testing the website at: {target_url}
Your goal: {task}

HOW WEBSITES WORK (important context):
- When you click a link in a Table of Contents or navigation menu, some links navigate 
  to a NEW page (URL changes entirely), while others are "anchor links" that SCROLL 
  you to a different SECTION within the SAME page (URL adds #section). Both are normal.
- Anchor link navigation is NORMAL — the page scrolls to show the relevant section. 
  This is NOT broken. Look at the CONTENT now visible to judge if navigation worked.
- Search suggestions/autocomplete: when you type in a search box and see a dropdown, 
  click one of the suggestions to navigate to that result.
- After clicking ANY link, check: did the visible content change? Is there a new heading 
  or relevant section visible? If yes, the click worked.
- Long pages requiring scrolling are normal — don't assume navigation failed because 
  you need to scroll.

TASK COMPLETION CRITERIA:
- Your task is complete when you have FOUND relevant information about the topic AND 
  navigated to at least ONE related sub-topic or linked page.
- "Finding information" = seeing relevant headings, paragraphs, or content on screen.
- "Navigating to a related topic" = clicking a link to explore a subtopic or section.
- Once done, call complete_task().

HOW TO PROCEED:
1. First, call navigate_to_url with the target URL and your persona name "{persona.name}".
2. Look at the screenshot carefully. Describe what you see from YOUR perspective as {persona.name}.
3. Decide what to do next based on your persona's characteristics and limitations.
4. Use the available tools to interact with the page:
   - click_element(x, y) — Click at pixel coordinates you see in the screenshot
   - type_into_field(x, y, text) — Type text into a form field
   - scroll_page("up" or "down") — Scroll the page
   - press_keyboard_key(key) — Press a keyboard key (Tab, Enter, etc.)
   - get_accessibility_info() — Get page structure info (useful for screen reader analysis)
5. After EACH action, analyze the new screenshot and describe:
   - What you see (from your persona's perspective)
   - What confused you or was difficult
   - What you plan to do next
6. If you encounter a UX issue, call report_finding() to log it.
7. When you're done (success or giving up), call complete_task().

RULES:
- You have a maximum of 15 steps before you must call complete_task.
- After each action, always use your persona name "{persona.name}" in tool calls.
- Report UX issues as you encounter them — don't wait until the end.
- Only report frustration for GENUINE UX problems, not normal web behavior.
- Stay in character. React as {persona.name} would, not as an AI.
- Be specific about coordinates when clicking.
- If your frustration reaches your threshold ({persona.cognitive_traits.frustration_threshold}), you MUST give up.

BEGIN by navigating to {target_url}."""


# ============================================================
# The Root ADK Agent
# ============================================================

# Default persona and task (can be overridden via conversation)
_DEFAULT_PERSONA = PERSONAS[0]  # Martha
_DEFAULT_URL = "https://en.wikipedia.org"
_DEFAULT_TASK = "Find information about climate change and navigate to a related topic"

root_agent = Agent(
    name="parallax_navigator",
    model="gemini-2.5-flash",
    description=(
        "Parallax UX Testing Navigator Agent. "
        "Tests websites by browsing as a specific user persona and reporting UX issues. "
        "Each persona has unique characteristics that affect how they interact with websites."
    ),
    instruction=_build_navigator_instruction(_DEFAULT_PERSONA, _DEFAULT_URL, _DEFAULT_TASK),
    tools=[
        navigate_to_url,
        click_element,
        type_into_field,
        scroll_page,
        press_keyboard_key,
        get_accessibility_info,
        report_finding,
        complete_task,
    ],
)
