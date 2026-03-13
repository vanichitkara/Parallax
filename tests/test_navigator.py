"""
Tests for the browser tool (Playwright wrapper).
Tests that the browser can be created, navigate, and take screenshots.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.browser import BrowserTool


async def test_browser_setup():
    """Test that browser can be initialized."""
    browser = BrowserTool()
    await browser.setup()
    assert browser._is_setup == True
    assert browser.page is not None
    await browser.cleanup()
    assert browser._is_setup == False
    print("✅ Browser setup/cleanup works")


async def test_browser_navigate():
    """Test navigation to a URL."""
    browser = BrowserTool()
    await browser.setup()
    
    result = await browser.navigate("https://example.com")
    assert result["status"] == "success"
    assert "screenshot_base64" in result
    assert len(result["screenshot_base64"]) > 100  # Screenshot has content
    assert result["page_title"] != ""
    
    await browser.cleanup()
    print("✅ Browser navigation works")


async def test_browser_screenshot():
    """Test screenshot capture."""
    browser = BrowserTool()
    await browser.setup()
    await browser.navigate("https://example.com")
    
    result = await browser.screenshot()
    assert result["status"] == "success"
    assert "screenshot_base64" in result
    assert result["current_url"] == "https://example.com/"
    
    await browser.cleanup()
    print("✅ Screenshot capture works")


async def test_browser_scroll():
    """Test page scrolling."""
    browser = BrowserTool()
    await browser.setup()
    await browser.navigate("https://en.wikipedia.org/wiki/Main_Page")
    
    result = await browser.scroll("down", 300)
    assert result["status"] == "success"
    assert result["direction"] == "down"
    
    result = await browser.scroll("up", 150)
    assert result["status"] == "success"
    assert result["direction"] == "up"
    
    await browser.cleanup()
    print("✅ Scrolling works")


async def test_browser_click():
    """Test clicking."""
    browser = BrowserTool()
    await browser.setup()
    await browser.navigate("https://example.com")
    
    result = await browser.click(640, 360)
    assert result["status"] == "success"
    assert "screenshot_base64" in result
    
    await browser.cleanup()
    print("✅ Clicking works")


async def test_page_info():
    """Test accessibility info extraction."""
    browser = BrowserTool()
    await browser.setup()
    await browser.navigate("https://example.com")
    
    result = await browser.get_page_info()
    assert result["status"] == "success"
    assert "headings" in result
    assert isinstance(result["headings"], list)
    assert "interactive_elements_count" in result
    
    await browser.cleanup()
    print("✅ Page info extraction works")


async def test_screenshot_count():
    """Test screenshot counter."""
    browser = BrowserTool()
    await browser.setup()
    
    assert browser.get_screenshot_count() == 0
    await browser.navigate("https://example.com")
    assert browser.get_screenshot_count() == 1
    await browser.screenshot()
    assert browser.get_screenshot_count() == 2
    await browser.scroll("down")
    assert browser.get_screenshot_count() == 3
    
    await browser.cleanup()
    print("✅ Screenshot counter works")


async def run_all_browser_tests():
    """Run all browser tests."""
    await test_browser_setup()
    await test_browser_navigate()
    await test_browser_screenshot()
    await test_browser_scroll()
    await test_browser_click()
    await test_page_info()
    await test_screenshot_count()
    
    print(f"\n{'='*40}")
    print("✅ ALL BROWSER TESTS PASSED!")
    print(f"{'='*40}")


if __name__ == "__main__":
    asyncio.run(run_all_browser_tests())
