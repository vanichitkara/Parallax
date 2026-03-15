"""
Parallax — Standalone Navigator Runner
Run a single persona agent against a website from the command line.
This is the Day 1 test script.

Usage:
    python run_navigator.py --persona martha --url "https://en.wikipedia.org" --task "Find info about climate change"
    python run_navigator.py --persona raj --url "https://en.wikipedia.org" --task "Find info about climate change"
"""

import asyncio
import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

# Import our modules
from tools.browser import BrowserTool
from personas.definitions import PERSONAS, get_persona_by_name, Persona
from personas.cognitive import CognitiveModel
from models.journey import Journey, JourneyStep, ActionType


class NavigatorRunner:
    """
    Runs a single persona agent through a website using Gemini Vision.
    This is the core Day 1 loop: screenshot → analyze → act → repeat.
    """
    
    def __init__(self, persona: Persona, target_url: str, task: str, run_id: str | None = None):
        self.persona = persona
        self.target_url = target_url
        self.task = task
        self.run_id = run_id
        self.browser = BrowserTool()
        self.cognitive = CognitiveModel(
            persona_name=persona.name,
            frustration_threshold=persona.cognitive_traits.frustration_threshold,
        )
        self.journey = Journey(
            journey_id=str(uuid.uuid4()),
            persona_name=persona.name,
            persona_age=persona.age,
            persona_background=persona.background,
            target_url=target_url,
            task=task,
        )
        
        # Initialize Gemini client
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required. Set it in .env file.")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.conversation_history = []
        
        # Output directory for screenshots
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dir_name = f"{persona.name.lower()}_{timestamp}"
        if run_id:
            dir_name = f"{persona.name.lower()}_{run_id}_{timestamp}"
            
        self.output_dir = Path(f"output/{dir_name}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the persona."""
        persona_context = self.persona.to_prompt_context()
        
        return f"""VIEWPORT: The screen you are seeing is exactly 1280 pixels wide and 800 pixels tall.
All click coordinates MUST be within (0,0) to (1279,799). Be precise with coordinates.

CLICKING ELEMENTS:
- PREFERRED: Use "click_element" with the exact visible text of a button/link (e.g., "ENGLISH", "Search", "Submit").
  This is more reliable than coordinates. Example: {{"type": "click_element", "text": "ENGLISH", "reason": "..."}} 
- FALLBACK: Use "click" with x,y coordinates ONLY for elements without clear text labels (icons, images, etc.).
  Example: {{"type": "click", "x": 640, "y": 400, "reason": "..."}}

WEB NAVIGATION FACTS (use these to understand what happened, NOT to override your persona's reactions):

1. TABLE OF CONTENTS / ANCHOR LINKS: On websites like Wikipedia, clicking a Table of 
   Contents link SCROLLS you to that section on the SAME page (URL adds #fragment like 
   page.html#Impacts). This is standard web behavior. After clicking a TOC link, if the 
   visible content changed, the link WORKED — it took you to that section.

2. HOW TO VERIFY A CLICK WORKED: After clicking any link:
   - Is the visible CONTENT different from before? → The click worked.
   - Is a new HEADING visible near the top? → Navigation succeeded.
   - ONLY consider a click failed if absolutely NOTHING changed on screen.

3. SEARCH AUTOCOMPLETE: When you type in a search box and see a dropdown, click a 
   suggestion to navigate to that page.

4. LONG PAGES: Many articles require scrolling. This is normal.

IMPORTANT DISTINCTION — "Understanding" vs "Experiencing":
- As the AGENT, you should UNDERSTAND that anchor links work correctly (don't treat them 
  as broken, don't give up because of them, keep progressing toward your task).
- As the PERSONA, you can still FEEL confused, surprised, or annoyed if the behavior 
  wasn't what you expected. Your persona's reaction is valuable UX data!
- Example: Martha might think "Oh, I thought that would open a new page, but it just 
  scrolled down. That's a bit confusing for me." — This is a VALID observation. But she 
  should still recognize the content changed and CONTINUE with her task.
- You should NEVER give up solely because a TOC link scrolled instead of opening a new page.

---

{persona_context}

YOUR TASK:
You are testing the website at: {self.target_url}
Your goal: {self.task}

TASK COMPLETION CRITERIA:
- Your task is complete when you have FOUND relevant information about the topic AND 
  successfully navigated to at least ONE related sub-topic, section, or linked page.
- "Finding information" = you can see relevant headings and paragraphs about the topic.
- "Navigating to a related topic" = clicking ANY link (TOC anchor or article link) to 
  view different content about a related subject. A TOC anchor scrolling you to a section 
  COUNTS as successful navigation.
- Once you've read some content and visited at least one related section/page, 
  set action.type to "task_complete".

You will be shown screenshots of the website. After each screenshot, respond with ONLY this JSON:
{{
    "observation": "What I see on the screen right now (from {self.persona.name}'s perspective)",
    "thinking": "My internal thought process as {self.persona.name}",
    "emotion": "How I feel (confused/frustrated/excited/neutral/anxious)",
    "frustration_delta": 0,
    "confusion_points": ["things that genuinely confused me from my persona's perspective"],
    "ux_issues": [
        {{
            "title": "Short issue title",
            "description": "Detailed description from my persona's perspective",
            "severity": "critical/high/medium/low/info",
            "category": "navigation/readability/accessibility/visual_design/interaction/language/color/mobile/cognitive_load"
        }}
    ],
    "action": {{
        "type": "click_element/click/hover/search/type/scroll/key_press/give_up/task_complete",
        "text": "for click_element: exact visible text of button/link (PREFERRED for buttons/links)",
        "near_text": "optional: disambiguate when multiple elements share same text (e.g. near_text='Health' to click 'Know More' near Health section)",
        "x": 640,
        "y": 360,
        "key": "Tab (for key_press action)",
        "direction": "down (for scroll action)",
        "query": "for search: what to search for",
        "reason": "why I'm taking this action"
    }}
}}

ACTION TYPES:
- click_element: Click a button/link by its visible text. PREFERRED for anything with text.
  Include "near_text" to click the right one when there are multiple (e.g. multiple 'Know More' buttons).
- click: Click at x,y coordinates. Use ONLY for icons, images, or elements without text
  (e.g. a dropdown arrow ▼ next to a menu item, a close X icon, an image).
- hover: Hover over an element to see if it reveals a dropdown/submenu. Use for navigation menus.
- search: Type a query into a search field and submit. Text goes in "query" field.
- type: Type text at x,y coordinates. Less precise — prefer search for search boxes.
- scroll: Scroll up/down.
- key_press: Press a key (Tab, Enter, Escape, etc).

RULES:
- frustration_delta: How much frustration changed (-1, 0, 1, 2, or 3). 
  Increase for things your persona would genuinely struggle with (tiny text, confusing 
  layout, jargon, inaccessible features). A small increase (1) for surprises like 
  unexpected scrolling is fine, but not enough to give up over.
- When you give up, set action.type to "give_up" — but ONLY for truly blocking problems 
  (e.g. you literally cannot figure out how to proceed after multiple attempts)
- When you complete the task, set action.type to "task_complete" with a summary
- ALWAYS stay in character as {self.persona.name}
- ONLY respond with valid JSON, no other text"""\
    
    def _parse_retry_delay(self, error_msg: str) -> float:
        """Extract retry delay from API error message, or return default."""
        match = re.search(r'retry(?:Delay)?["\s:]*["\s]*(\d+(?:\.\d+)?)s', str(error_msg))
        if match:
            return float(match.group(1))
        return 30.0  # Default 30s if we can't parse
    
    async def _call_gemini_with_retry(self, contents, max_retries: int = 3) -> str:
        """Call Gemini API with automatic retry on rate limit errors."""
        for attempt in range(max_retries):
            try:
                # Small delay between ALL calls to stay under per-minute limits
                if attempt == 0:
                    await asyncio.sleep(2)
                
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=self._build_system_prompt(),
                        temperature=0.7,
                        max_output_tokens=1500,
                        response_mime_type="application/json",
                    ),
                )
                return response.text.strip()
                
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                
                if is_rate_limit and attempt < max_retries - 1:
                    delay = self._parse_retry_delay(error_str)
                    # Add a small buffer
                    delay = min(delay + 5, 120)
                    print(f"  ⏳ Rate limited. Waiting {delay:.0f}s before retry ({attempt + 1}/{max_retries})...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
    
    async def _analyze_screenshot(self, screenshot_b64: str, action_context: str = "") -> dict:
        """Send a screenshot to Gemini Vision and get the persona's response."""
        import base64
        
        # Get current URL for context
        current_url = ""
        if self.browser.page:
            current_url = self.browser.page.url
        
        # Build the message with URL context and verification reminder
        click_reminder = ""
        if "click" in action_context.lower():
            click_reminder = (
                "NOTE: You just clicked a link. Check if the visible content changed — "
                "if new headings or text appeared, the click worked (anchor/TOC links "
                "scroll within the same page, which is normal). React as your persona "
                "would, but keep progressing with your task.\n"
            )
        
        prompt = (
            f"You just performed: {action_context}\n"
            f"Current URL: {current_url}\n"
            f"{click_reminder}\n"
            f"Here is the current screenshot of the page. "
            f"Examine the CONTENT visible on screen carefully. "
            f"What do you see and what will you do next? Respond with JSON only."
        )
        
        # Create image part
        image_part = types.Part.from_bytes(
            data=base64.b64decode(screenshot_b64),
            mime_type="image/png",
        )
        
        # Add to conversation history
        self.conversation_history.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    image_part,
                ],
            )
        )
        
        try:
            response_text = await self._call_gemini_with_retry(self.conversation_history)
            
            # Add assistant response to history
            self.conversation_history.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=response_text)],
                )
            )
            
            # Parse JSON (handle markdown code blocks)
            if response_text.startswith("```"):
                # Remove markdown code block markers
                lines = response_text.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                response_text = "\n".join(lines)
            
            return json.loads(response_text)
            
        except json.JSONDecodeError as e:
            print(f"  ⚠️ Failed to parse JSON response: {e}")
            print(f"  Raw response: {response_text[:200]}")
            return {
                "observation": "Could not parse response",
                "thinking": "Error in response parsing",
                "emotion": "neutral",
                "frustration_delta": 0,
                "confusion_points": [],
                "ux_issues": [],
                "action": {"type": "scroll", "direction": "down", "reason": "Fallback action"},
            }
        except Exception as e:
            print(f"  ❌ Error calling Gemini: {e}")
            return {
                "observation": f"Error: {str(e)}",
                "thinking": "API error occurred",
                "emotion": "neutral",
                "frustration_delta": 0,
                "confusion_points": [],
                "ux_issues": [],
                "action": {"type": "give_up", "reason": f"API error: {str(e)}"},
            }
    
    async def _save_screenshot(self, screenshot_b64: str, step_num: int, action: str):
        """Save a screenshot to disk, and upload to GCS if configured."""
        import base64
        filename = f"step_{step_num:02d}_{action}.png"
        filepath = self.output_dir / filename
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(screenshot_b64))
            
        # Optional Cloud Storage upload
        try:
            from api.gcp_services import gcp_client
            if gcp_client.enabled:
                gcp_client.upload_screenshot_str(self.output_dir.name, filename, str(filepath))
        except ImportError:
            pass
            
        return str(filepath)
    
    async def _execute_action(self, action: dict) -> tuple[str, str]:
        """
        Execute an action from the agent's response.
        Returns (screenshot_b64, action_description).
        """
        action_type = action.get("type", "scroll")
        
        if action_type == "click_element":
            text = action.get("text", "")
            element_type = action.get("element_type", "any")
            near_text = action.get("near_text", "")
            result = await self.browser.click_element(text, element_type, near_text)
            if result["status"] == "success":
                return result.get("screenshot_base64", ""), f"Clicked element '{text}'"
            else:
                # Fallback: try coordinate click if element not found
                print(f"  ⚠️ Element '{text}' not found by text, trying coordinate click...")
                x = action.get("x", 640)
                y = action.get("y", 360)
                result = await self.browser.click(x, y)
                return result.get("screenshot_base64", ""), f"Clicked at ({x}, {y}) [fallback]: {action.get('reason', '')}"
        
        elif action_type == "click":
            x = action.get("x", 640)
            y = action.get("y", 360)
            result = await self.browser.click(x, y)
            return result.get("screenshot_base64", ""), f"Clicked at ({x}, {y}): {action.get('reason', '')}"
        
        elif action_type == "hover":
            text = action.get("text", "")
            result = await self.browser.hover(text)
            return result.get("screenshot_base64", ""), f"Hovered over '{text}'"
        
        elif action_type == "search":
            query = action.get("query", action.get("text", ""))
            field = action.get("field", "Search")
            result = await self.browser.type_and_submit(query, field)
            return result.get("screenshot_base64", ""), f"Searched for '{query}'"
        
        elif action_type == "type":
            x = action.get("x", 640)
            y = action.get("y", 360)
            text = action.get("text", "")
            result = await self.browser.type_text(x, y, text)
            return result.get("screenshot_base64", ""), f"Typed '{text}' at ({x}, {y})"
        
        elif action_type == "scroll":
            direction = action.get("direction", "down")
            amount = action.get("amount", 500)  # Larger scroll for better coverage
            result = await self.browser.scroll(direction, amount)
            return result.get("screenshot_base64", ""), f"Scrolled {direction}"
        
        elif action_type == "key_press":
            key = action.get("key", "Tab")
            result = await self.browser.press_key(key)
            return result.get("screenshot_base64", ""), f"Pressed {key}"
        
        elif action_type in ("give_up", "task_complete"):
            return "", action_type
        
        else:
            # Default: take a screenshot
            result = await self.browser.screenshot()
            return result.get("screenshot_base64", ""), "Took screenshot"
    
    async def run(self) -> Journey:
        """
        Run the full navigation loop for this persona.
        Returns the completed Journey.
        """
        print(f"\n{'='*60}")
        print(f"🧑 {self.persona.name} (age {self.persona.age}) — {self.persona.background}")
        print(f"🎯 Task: {self.task}")
        print(f"🌐 URL: {self.target_url}")
        print(f"{'='*60}\n")
        
        try:
            # Setup browser
            await self.browser.setup()
            
            # Step 1: Navigate to URL
            print(f"  📍 Step 1: Navigating to {self.target_url}...")
            nav_result = await self.browser.navigate(self.target_url)
            
            if nav_result["status"] != "success":
                print(f"  ❌ Failed to navigate: {nav_result.get('error')}")
                self.journey.complete(False, f"Failed to navigate: {nav_result.get('error')}")
                return self.journey
            
            screenshot_b64 = nav_result["screenshot_base64"]
            await self._save_screenshot(screenshot_b64, 1, "navigate")
            
            # Analyze the first screenshot
            print(f"  🤖 Analyzing screenshot with Gemini Vision...")
            response = await self._analyze_screenshot(
                screenshot_b64, 
                f"Navigated to {self.target_url}"
            )
            
            step = JourneyStep(
                step_number=1,
                observation=response.get("observation", ""),
                thinking=response.get("thinking", ""),
                action_type=ActionType.NAVIGATE,
                action_details={"url": self.target_url},
                outcome=f"Page loaded: {nav_result.get('page_title', '')}",
                frustration_level=max(0, min(10, response.get("frustration_delta", 0))),
                confusion_points=response.get("confusion_points", []),
                page_url=self.target_url,
                page_title=nav_result.get("page_title", ""),
            )
            self.journey.add_step(step)
            self.cognitive.step()
            
            # Print what the persona saw
            print(f"  👁️ {self.persona.name} sees: {response.get('observation', '')}")
            print(f"  💭 Thinking: {response.get('thinking', '')}")
            print(f"  😤 Emotion: {response.get('emotion', 'neutral')}")
            
            # Log any UX issues found
            for issue in response.get("ux_issues", []):
                print(f"  🔍 Issue: [{issue.get('severity', '?')}] {issue.get('title', 'Unknown')}")
            
            # Main loop: analyze → act → repeat
            step_num = 2
            while self.cognitive.should_continue() and step_num <= 15:
                action = response.get("action", {})
                action_type = action.get("type", "scroll")
                
                if action_type in ("give_up", "task_complete"):
                    success = action_type == "task_complete"
                    reason = action.get("reason", "")
                    print(f"\n  {'✅' if success else '❌'} {self.persona.name} {'completed the task' if success else 'gave up'}: {reason}")
                    self.journey.complete(success, None if success else reason)
                    break
                
                # Execute the action
                print(f"\n  📍 Step {step_num}: {action_type} — {action.get('reason', '')}...")
                screenshot_b64, action_desc = await self._execute_action(action)
                
                if not screenshot_b64:
                    # Action returned no screenshot (give_up or task_complete handled above)
                    break
                
                await self._save_screenshot(screenshot_b64, step_num, action_type)
                
                # Update frustration
                frustration_delta = response.get("frustration_delta", 0)
                if frustration_delta > 0:
                    for _ in range(frustration_delta):
                        gave_up = self.cognitive.record_frustration(
                            response.get("confusion_points", ["Unknown"])[0] if response.get("confusion_points") else "Unknown"
                        )
                        if gave_up:
                            print(f"  😡 {self.persona.name} has reached frustration limit and is giving up!")
                            self.journey.complete(False, "Frustration threshold exceeded")
                            break
                    if self.cognitive.has_given_up:
                        break
                elif frustration_delta < 0:
                    self.cognitive.record_success(action_desc)
                
                # Analyze the new screenshot
                print(f"  🤖 Analyzing screenshot...")
                response = await self._analyze_screenshot(screenshot_b64, action_desc)
                
                # Record the step
                step = JourneyStep(
                    step_number=step_num,
                    observation=response.get("observation", ""),
                    thinking=response.get("thinking", ""),
                    action_type=ActionType(action_type) if action_type in ActionType.__members__.values() else ActionType.CLICK,
                    action_details=action,
                    outcome=action_desc,
                    frustration_level=self.cognitive.current_frustration,
                    confusion_points=response.get("confusion_points", []),
                    page_url=self.browser.page.url if self.browser.page else "",
                )
                self.journey.add_step(step)
                self.cognitive.step()
                
                # Print status
                emotion = response.get("emotion", "neutral")
                emoji = {"confused": "😕", "frustrated": "😤", "excited": "🤩", "anxious": "😰", "neutral": "😐"}.get(emotion, "😐")
                print(f"  👁️ Sees: {response.get('observation', '')}")
                print(f"  {emoji} Feeling: {emotion} | Frustration: {self.cognitive.current_frustration}/{self.cognitive.frustration_threshold}")
                
                for issue in response.get("ux_issues", []):
                    print(f"  🔍 Issue: [{issue.get('severity', '?')}] {issue.get('title', 'Unknown')}")
                
                step_num += 1
            
            # If we hit max steps
            if step_num > 15 and not self.journey.completed_at:
                print(f"\n  ⏰ {self.persona.name} hit the maximum step limit (15 steps)")
                self.journey.complete(False, "Maximum steps reached")
            
        except Exception as e:
            print(f"\n  ❌ Error during navigation: {e}")
            import traceback
            traceback.print_exc()
            self.journey.complete(False, f"Error: {str(e)}")
        
        finally:
            await self.browser.cleanup()
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 JOURNEY SUMMARY — {self.persona.name}")
        print(f"{'='*60}")
        print(f"  Steps: {self.journey.total_steps}")
        print(f"  Task completed: {'✅ Yes' if self.journey.task_completed else '❌ No'}")
        if self.journey.gave_up:
            print(f"  Gave up: {self.journey.gave_up_reason}")
        print(f"  Max frustration: {self.journey.max_frustration_reached}")
        print(f"  Confusions: {len(self.journey.key_confusions)}")
        if self.journey.key_confusions:
            for c in self.journey.key_confusions[:5]:
                print(f"    - {c}")
        print(f"  Screenshots saved to: {self.output_dir}")
        print(f"{'='*60}\n")
        
        # Save journey JSON
        journey_path = self.output_dir / "journey.json"
        with open(journey_path, "w") as f:
            json.dump(self.journey.model_dump(exclude={"steps": {"__all__": {"screenshot_base64"}}}), f, indent=2, default=str)
        print(f"  💾 Journey saved to: {journey_path}")
        
        return self.journey


async def main():
    parser = argparse.ArgumentParser(description="Parallax — Run a persona navigator agent")
    parser.add_argument("--persona", "-p", type=str, default="martha",
                       help=f"Persona name. Available: {', '.join(p.name.lower() for p in PERSONAS)}")
    parser.add_argument("--url", "-u", type=str, default="https://en.wikipedia.org",
                       help="Target URL to test")
    parser.add_argument("--task", "-t", type=str, default="Find information about climate change and navigate to a related topic",
                       help="Task for the persona to complete")
    parser.add_argument("--run-id", type=str, default=None,
                       help="Specific run ID to associate with this test")
    
    args = parser.parse_args()
    
    # Get persona
    try:
        persona = get_persona_by_name(args.persona)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    print(f"\n🚀 Parallax Navigator — Starting UX Test")
    print(f"   Persona: {persona.name} (age {persona.age})")
    print(f"   URL: {args.url}")
    print(f"   Task: {args.task}")
    
    # Run the navigator
    runner = NavigatorRunner(persona, args.url, args.task, run_id=args.run_id)
    journey = await runner.run()
    
    return journey


if __name__ == "__main__":
    asyncio.run(main())
