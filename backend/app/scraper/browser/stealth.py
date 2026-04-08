"""Stealth browser configuration inspired by Fairtrail.
Anti-detection measures for scraping Google Flights/Hotels."""

import random
import logging
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1440, "height": 900},
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
]

STEALTH_JS = """
// Hide webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Mock chrome.runtime
window.chrome = { runtime: {} };

// Mock plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Mock languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['fr-FR', 'fr', 'en-US', 'en'],
});

// Disable automation flags
Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
"""


async def create_browser() -> tuple[Browser, object]:
    """Launch a stealth Chromium browser. Returns (browser, playwright_instance)."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--window-size=1440,900",
        ],
    )
    return browser, pw


async def create_stealth_context(browser: Browser) -> BrowserContext:
    """Create a browser context with anti-detection measures."""
    viewport = random.choice(VIEWPORTS)
    ua = random.choice(USER_AGENTS)

    context = await browser.new_context(
        viewport=viewport,
        user_agent=ua,
        locale="fr-FR",
        timezone_id="Europe/Paris",
        geolocation={"latitude": 48.8566, "longitude": 2.3522},
        permissions=["geolocation"],
    )

    await context.add_init_script(STEALTH_JS)
    return context


async def navigate_and_extract(page: Page, url: str, wait_selector: str, timeout: int = 20000) -> str | None:
    """Navigate to a URL, wait for content, and extract visible text."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

        # Dismiss cookie consent
        try:
            consent = page.locator("button:has-text('Accept'), button:has-text('Accepter'), button:has-text('Tout accepter')")
            if await consent.count() > 0:
                await consent.first.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        # Wait for results
        try:
            await page.wait_for_selector(wait_selector, timeout=timeout)
        except Exception:
            logger.warning(f"Selector {wait_selector} not found, extracting anyway")

        # Simulate human behavior
        await page.wait_for_timeout(random.randint(1000, 3000))
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        await page.evaluate("window.scrollBy(0, 300)")
        await page.wait_for_timeout(random.randint(500, 1500))

        # Extract visible text (not HTML — much smaller, better for LLM)
        text = await page.evaluate("document.body.innerText")
        return text

    except Exception as e:
        logger.error(f"Navigation failed for {url}: {e}")
        return None
