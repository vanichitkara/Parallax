"""
Parallax — Browser Tool
Playwright-based browser interaction tool that provides screenshot, click, type,
scroll, and navigate capabilities for persona agents.
These are exposed as ADK-compatible tool functions.
"""

import asyncio
import base64
import os
import time
import secrets
from typing import Optional

from playwright.async_api import async_playwright, Page, Browser, Playwright


class BrowserTool:
    """
    Manages a headless browser instance for a single persona agent.
    Each persona gets their own browser context for isolated sessions.
    """
    
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._screenshots: list[dict] = []
        self._is_setup = False
    
    async def setup(self, viewport_width: int = 1280, viewport_height: int = 800):
        """Initialize browser with specified viewport."""
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--allow-running-insecure-content",
            ]
        )
        self.context = await self.browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }
        )
        
        # Add stealth script to bypass most automation detectors
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)
        
        self.page = await self.context.new_page()
        self._is_setup = True
    
    async def navigate(self, url: str) -> dict:
        """
        Navigate to a URL and return a screenshot.
        
        Args:
            url: The URL to navigate to.
            
        Returns:
            dict with status and screenshot_base64
        """
        if not self._is_setup:
            await self.setup()
        
        try:
            # Random jitter before navigation
            await asyncio.sleep(0.5 + (secrets.randbelow(100) / 100.0))
            await self.page.goto(url, wait_until="networkidle", timeout=45000)
            # Wait extra time for dynamic transition
            await self.page.wait_for_timeout(3000)
            screenshot_b64 = await self._take_screenshot("navigate")
            
            return {
                "status": "success",
                "action": "navigate",
                "url": url,
                "page_title": await self.page.title(),
                "screenshot_base64": screenshot_b64,
            }
        except Exception as e:
            return {
                "status": "error",
                "action": "navigate",
                "error": str(e),
            }
    
    async def screenshot(self) -> dict:
        """
        Take a screenshot of the current page.
        
        Returns:
            dict with screenshot_base64
        """
        if not self._is_setup:
            return {"status": "error", "error": "Browser not initialized"}
        
        try:
            screenshot_b64 = await self._take_screenshot("screenshot")
            return {
                "status": "success",
                "action": "screenshot",
                "page_title": await self.page.title(),
                "current_url": self.page.url,
                "screenshot_base64": screenshot_b64,
            }
        except Exception as e:
            return {"status": "error", "action": "screenshot", "error": str(e)}
    
    async def click(self, x: int, y: int) -> dict:
        """
        Click at specific coordinates on the page.
        
        Args:
            x: X coordinate to click
            y: Y coordinate to click
            
        Returns:
            dict with status and new screenshot
        """
        if not self._is_setup:
            return {"status": "error", "error": "Browser not initialized"}
        
        try:
            # Clamp coordinates to viewport bounds
            clamped_x = max(0, min(x, self.viewport_width - 1))
            clamped_y = max(0, min(y, self.viewport_height - 1))
            if clamped_x != x or clamped_y != y:
                print(f"  ⚠️ Coordinates ({x},{y}) clamped to ({clamped_x},{clamped_y}) — was outside viewport")
            old_url = self.page.url
            await self.page.mouse.click(clamped_x, clamped_y)
            
            # Wait for potential navigation or network activity
            try:
                # Give the SPA a moment to react
                await self.page.wait_for_timeout(1500)
                if self.page.url == old_url:
                    # If still on same page, maybe it's a slow transition or SPA update
                    await self.page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass
            await self.page.wait_for_timeout(1000)
            
            screenshot_b64 = await self._take_screenshot(f"click_{x}_{y}")
            
            return {
                "status": "success",
                "action": "click",
                "coordinates": {"x": x, "y": y},
                "page_title": await self.page.title(),
                "current_url": self.page.url,
                "screenshot_base64": screenshot_b64,
            }
        except Exception as e:
            return {"status": "error", "action": "click", "error": str(e)}
    async def click_element(self, text: str, element_type: str = "any", near_text: str = "") -> dict:
        """
        Click an element by its visible text content. More reliable than coordinates.
        
        Args:
            text: Visible text of the element to click (e.g., "ENGLISH", "Submit", "Search")
            element_type: Type hint — "button", "link", or "any" (default)
            near_text: Optional — click the instance of this element nearest to another text
                       (e.g., near_text="Health" to click "Know More" near the Health section)
        
        Returns:
            dict with status and new screenshot
        """
        if not self._is_setup:
            return {"status": "error", "error": "Browser not initialized"}
        
        try:
            element = None
            
            # If near_text is provided, disambiguate among multiple matching elements
            if near_text:
                try:
                    # Find all elements matching the text
                    all_matches = self.page.get_by_text(text, exact=False)
                    count = await all_matches.count()
                    near_lower = near_text.lower()
                    
                    if count > 1:
                        # Strategy 1: Check href attributes for near_text keyword
                        for i in range(count):
                            el = all_matches.nth(i)
                            try:
                                href = await el.get_attribute("href") or ""
                                if near_lower in href.lower():
                                    element = el
                                    break
                            except Exception:
                                pass
                        
                        # Strategy 2: Check parent/ancestor text content
                        if element is None:
                            for i in range(count):
                                el = all_matches.nth(i)
                                try:
                                    # Check a few levels of parent containers
                                    for level in range(1, 6):
                                        parent = el.locator(f"xpath=ancestor::*[{level}]").first
                                        parent_text = await parent.inner_text()
                                        if near_lower in parent_text.lower() and len(parent_text) < 500:
                                            element = el
                                            break
                                    if element:
                                        break
                                except Exception:
                                    pass
                except Exception:
                    pass
            
            # Try specific locators
            if element is None and (element_type == "button" or element_type == "any"):
                try:
                    locator = self.page.get_by_role("button", name=text)
                    if await locator.count() > 0:
                        element = locator.first
                except Exception:
                    pass
            
            if element is None and (element_type == "link" or element_type == "any"):
                try:
                    locator = self.page.get_by_role("link", name=text)
                    if await locator.count() > 0:
                        element = locator.first
                except Exception:
                    pass
            
            if element is None:
                try:
                    locator = self.page.get_by_text(text, exact=True)
                    if await locator.count() > 0:
                        element = locator.first
                except Exception:
                    pass
            
            if element is None:
                try:
                    locator = self.page.get_by_text(text, exact=False)
                    if await locator.count() > 0:
                        element = locator.first
                except Exception:
                    pass
            
            if element is None:
                return {
                    "status": "error",
                    "action": "click_element",
                    "error": f"Could not find element with text '{text}'",
                }
            
            # Hover first to trigger hover-dependent menus/dropdowns
            try:
                await element.hover(timeout=3000)
                await self.page.wait_for_timeout(500)
            except Exception:
                pass
            
            # Click the found element
            old_url = self.page.url
            await element.click(timeout=8000)
            
            # Wait for any navigation or dynamic content
            try:
                # Wait for SPA or traditional navigation
                await self.page.wait_for_load_state("networkidle", timeout=5000)
                if self.page.url == old_url:
                    # Give it a bit more time if URL hasn't changed but it might be an async transition
                    await self.page.wait_for_timeout(2000)
            except Exception:
                pass
            await self.page.wait_for_timeout(1000)
            
            screenshot_b64 = await self._take_screenshot(f"click_element_{text[:20]}")
            
            return {
                "status": "success",
                "action": "click_element",
                "element_text": text,
                "page_title": await self.page.title(),
                "current_url": self.page.url,
                "screenshot_base64": screenshot_b64,
            }
        except Exception as e:
            return {"status": "error", "action": "click_element", "error": str(e)}
    
    async def hover(self, text: str) -> dict:
        """
        Hover over an element to trigger dropdown menus or tooltips.
        Use this for navigation menus that show submenus on hover.
        
        Args:
            text: Visible text of the element to hover over (e.g., "CLAIM", "Products")
            
        Returns:
            dict with status and screenshot showing the hover result (e.g. dropdown menu)
        """
        if not self._is_setup:
            return {"status": "error", "error": "Browser not initialized"}
        
        try:
            element = None
            for role in ["button", "link", "menuitem"]:
                try:
                    locator = self.page.get_by_role(role, name=text)
                    if await locator.count() > 0:
                        element = locator.first
                        break
                except Exception:
                    pass
            
            if element is None:
                try:
                    locator = self.page.get_by_text(text, exact=True)
                    if await locator.count() > 0:
                        element = locator.first
                except Exception:
                    pass
            
            if element is None:
                return {"status": "error", "action": "hover", "error": f"Could not find '{text}'"}
            
            await element.hover(timeout=5000)
            await self.page.wait_for_timeout(800)
            
            screenshot_b64 = await self._take_screenshot(f"hover_{text[:20]}")
            return {
                "status": "success",
                "action": "hover",
                "element_text": text,
                "page_title": await self.page.title(),
                "current_url": self.page.url,
                "screenshot_base64": screenshot_b64,
            }
        except Exception as e:
            return {"status": "error", "action": "hover", "error": str(e)}
    
    async def type_and_submit(self, text: str, field_text: str = "Search") -> dict:
        """
        Find a text input by placeholder/label, type text, and press Enter to submit.
        More reliable than coordinate-based typing for search forms.
        
        Args:
            text: Text to type into the field
            field_text: Placeholder or label text of the field (default: "Search")
            
        Returns:
            dict with status and screenshot
        """
        if not self._is_setup:
            return {"status": "error", "error": "Browser not initialized"}
        
        try:
            field = None
            # Try by placeholder
            try:
                locator = self.page.get_by_placeholder(field_text)
                if await locator.count() > 0:
                    field = locator.first
            except Exception:
                pass
            
            # Try by label
            if field is None:
                try:
                    locator = self.page.get_by_label(field_text)
                    if await locator.count() > 0:
                        field = locator.first
                except Exception:
                    pass
            
            # Try by role
            if field is None:
                try:
                    locator = self.page.get_by_role("searchbox")
                    if await locator.count() > 0:
                        field = locator.first
                except Exception:
                    pass
                    
            if field is None:
                try:
                    locator = self.page.get_by_role("textbox", name=field_text)
                    if await locator.count() > 0:
                        field = locator.first
                except Exception:
                    pass
            
            if field is None:
                return {"status": "error", "action": "type_and_submit", "error": f"Could not find field '{field_text}'"}
            
            await field.click(timeout=3000)
            await self.page.wait_for_timeout(200)
            
            # Clear and type
            await field.fill("")
            await field.fill(text)
            await self.page.wait_for_timeout(300)
            
            # Submit with Enter
            await self.page.keyboard.press("Enter")
            
            # Wait for results
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            await self.page.wait_for_timeout(1500)
            
            screenshot_b64 = await self._take_screenshot(f"search_{text[:20]}")
            return {
                "status": "success",
                "action": "type_and_submit",
                "text_typed": text,
                "field": field_text,
                "page_title": await self.page.title(),
                "current_url": self.page.url,
                "screenshot_base64": screenshot_b64,
            }
        except Exception as e:
            return {"status": "error", "action": "type_and_submit", "error": str(e)}
    
    async def type_text(self, x: int, y: int, text: str) -> dict:
        """
        Click on a field at (x, y) and type text into it.
        
        Args:
            x: X coordinate of the text field
            y: Y coordinate of the text field
            text: Text to type
            
        Returns:
            dict with status and new screenshot
        """
        if not self._is_setup:
            return {"status": "error", "error": "Browser not initialized"}
        
        try:
            # Click the field first
            await self.page.mouse.click(x, y)
            await self.page.wait_for_timeout(300)
            
            # Clear any existing text
            await self.page.keyboard.press("Control+A")
            await self.page.keyboard.press("Backspace")
            
            # Type the text with realistic delay
            await self.page.keyboard.type(text, delay=50)
            await self.page.wait_for_timeout(500)
            
            screenshot_b64 = await self._take_screenshot(f"type_{x}_{y}")
            
            return {
                "status": "success",
                "action": "type_text",
                "coordinates": {"x": x, "y": y},
                "text_typed": text,
                "screenshot_base64": screenshot_b64,
            }
        except Exception as e:
            return {"status": "error", "action": "type_text", "error": str(e)}
    
    async def scroll(self, direction: str = "down", amount: int = 300) -> dict:
        """
        Scroll the page.
        
        Args:
            direction: "up" or "down"
            amount: Number of pixels to scroll
            
        Returns:
            dict with status and new screenshot
        """
        if not self._is_setup:
            return {"status": "error", "error": "Browser not initialized"}
        
        try:
            delta = amount if direction == "down" else -amount
            await self.page.mouse.wheel(0, delta)
            await self.page.wait_for_timeout(800)
            
            screenshot_b64 = await self._take_screenshot(f"scroll_{direction}")
            
            return {
                "status": "success",
                "action": "scroll",
                "direction": direction,
                "amount": amount,
                "screenshot_base64": screenshot_b64,
            }
        except Exception as e:
            return {"status": "error", "action": "scroll", "error": str(e)}
    
    async def press_key(self, key: str) -> dict:
        """
        Press a keyboard key (for Tab, Enter, Escape, etc.).
        
        Args:
            key: Key to press (e.g., "Tab", "Enter", "Escape", "ArrowDown")
            
        Returns:
            dict with status and new screenshot
        """
        if not self._is_setup:
            return {"status": "error", "error": "Browser not initialized"}
        
        try:
            await self.page.keyboard.press(key)
            await self.page.wait_for_timeout(500)
            
            screenshot_b64 = await self._take_screenshot(f"key_{key}")
            
            return {
                "status": "success",
                "action": "press_key",
                "key": key,
                "screenshot_base64": screenshot_b64,
            }
        except Exception as e:
            return {"status": "error", "action": "press_key", "error": str(e)}
    
    async def get_page_info(self) -> dict:
        """Get information about the current page for accessibility analysis."""
        if not self._is_setup:
            return {"status": "error", "error": "Browser not initialized"}
        
        try:
            # Get heading structure
            headings = await self.page.evaluate("""
                () => {
                    const headings = [];
                    document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
                        headings.push({
                            level: h.tagName,
                            text: h.textContent.trim().substring(0, 100),
                        });
                    });
                    return headings;
                }
            """)
            
            # Get images without alt text
            images_without_alt = await self.page.evaluate("""
                () => {
                    const imgs = [];
                    document.querySelectorAll('img').forEach(img => {
                        if (!img.alt || img.alt.trim() === '') {
                            imgs.push({
                                src: img.src.substring(0, 100),
                                width: img.width,
                                height: img.height,
                            });
                        }
                    });
                    return imgs;
                }
            """)
            
            # Get interactive elements (for tab order analysis)
            interactive = await self.page.evaluate("""
                () => {
                    const elements = [];
                    document.querySelectorAll('a, button, input, select, textarea, [tabindex]').forEach(el => {
                        elements.push({
                            tag: el.tagName.toLowerCase(),
                            text: (el.textContent || el.value || el.placeholder || '').trim().substring(0, 50),
                            tabindex: el.tabIndex,
                            ariaLabel: el.getAttribute('aria-label') || '',
                        });
                    });
                    return elements.slice(0, 30);
                }
            """)
            
            return {
                "status": "success",
                "page_title": await self.page.title(),
                "current_url": self.page.url,
                "headings": headings,
                "images_without_alt": len(images_without_alt),
                "interactive_elements_count": len(interactive),
                "interactive_elements_sample": interactive[:10],
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _take_screenshot(self, action_name: str) -> str:
        """Take a screenshot and return as base64 string."""
        screenshot_bytes = await self.page.screenshot(type="png", full_page=False)
        b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        
        self._screenshots.append({
            "action": action_name,
            "timestamp": time.time(),
            "url": self.page.url,
        })
        
        return b64
    
    async def cleanup(self):
        """Close browser and cleanup resources."""
        if self.page:
            await self.page.close()
        if hasattr(self, 'context') and self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self._is_setup = False
    
    def get_screenshot_count(self) -> int:
        """Get the number of screenshots taken."""
        return len(self._screenshots)
