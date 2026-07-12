"""browse_autonomously — autonomous web browsing via Playwright.

Spins up a real headless Chromium browser, navigates pages, extracts content.
Uses the LLM to drive multi-step browsing: click links, fill forms, research topics.

Handles Cloudflare challenges by waiting and retrying. Extracts page text for
the agent to reason about.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import time
from typing import Optional

from plugins.ares.tools.base import json_result, tool_error

logger = logging.getLogger(__name__)

TOOLSET = "ares_browsing"

_browser_lock = threading.Lock()


def _llm_call(prompt: str, system: str = "", model: str = "tencent/hy3:free") -> str:
    """Call LLM via OpenRouter for browser reasoning."""
    import requests as _req

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        from cyberfox_cli.env_loader import load_cyberfox_dotenv
        load_cyberfox_dotenv()
        api_key = os.environ.get("OPENROUTER_API_KEY", "")

    if not api_key:
        return ""

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = _req.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 2000},
            timeout=30,
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.debug("LLM call failed: %s", e)
        return ""


def _extract_text(html: str) -> str:
    """Extract readable text from HTML, stripping tags and scripts."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:8000]


def _get_links(html: str, base_url: str) -> list[dict]:
    """Extract links from HTML."""
    from urllib.parse import urljoin
    links = []
    seen = set()
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = m.group(1)
        full = urljoin(base_url, href)
        if full not in seen and full.startswith("http"):
            seen.add(full)
            label = re.search(r'>([^<]+)<', html[m.start():m.end()+50])
            links.append({"url": full, "label": label.group(1).strip() if label else ""})
            if len(links) >= 20:
                break
    return links


def _run_browse(
    task: str,
    max_steps: int = 10,
    model: str = "tencent/hy3:free",
) -> dict:
    """Browse the web with Playwright, driven by LLM reasoning."""
    from playwright.sync_api import sync_playwright

    results = {
        "success": True,
        "task": task,
        "visited_urls": [],
        "pages_content": [],
        "final_result": None,
        "steps_taken": 0,
    }

    system_prompt = (
        "You are a web browsing assistant. Given a task and the current page content, "
        "decide the next action. Respond with JSON: "
        '{"action": "navigate", "url": "..."} or '
        '{"action": "extract", "content": "what you found"} or '
        '{"action": "done", "result": "final answer"}'
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
            color_scheme="light",
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Linux"',
            },
        )

        # Apply playwright-stealth patches
        try:
            from playwright_stealth import stealth_sync
            stealth_sync(context)
        except ImportError:
            pass

        page = context.new_page()

        # Extra anti-detection: override navigator.webdriver
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'platform', { get: () => 'Linux x86_64' });
            window.chrome = { runtime: {} };
        """)

        current_url = "about:blank"
        page_text = ""

        for step in range(max_steps):
            results["steps_taken"] = step + 1

            prompt = (
                f"Task: {task}\n\n"
                f"Current URL: {current_url}\n\n"
                f"Page content (truncated):\n{page_text[:3000]}\n\n"
                f"Decide next action. If you have enough information, return 'done'. "
                f"If you need to visit a URL, return 'navigate'. If you found what you need, return 'extract'."
            )

            response = _llm_call(prompt, system=system_prompt, model=model)
            if not response:
                results["final_result"] = "LLM call failed"
                break

            try:
                action_data = json.loads(response)
            except json.JSONDecodeError:
                action_match = re.search(r'\{.*\}', response, re.DOTALL)
                if action_match:
                    action_data = json.loads(action_match.group())
                else:
                    action_data = {"action": "done", "result": response}

            action = action_data.get("action", "done")

            if action == "done":
                results["final_result"] = action_data.get("result", response)
                break

            elif action == "navigate":
                url = action_data.get("url", "")
                if not url:
                    results["final_result"] = "No URL provided"
                    break
                try:
                    # Navigate and wait for network to settle (JS rendering)
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    current_url = page.url
                    results["visited_urls"].append(current_url)

                    # Wait for network idle — lets JS frameworks finish rendering
                    try:
                        page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass  # timeout is fine, we still continue

                    # Wait for Cloudflare challenge if present
                    for _ in range(12):
                        title = page.title().lower()
                        body = ""
                        try:
                            body = page.inner_text("body").lower()[:500]
                        except Exception:
                            pass
                        is_blocked = any(w in title or w in body for w in [
                            "just a moment", "checking your browser",
                            "cloudflare", "captcha", "verify you are human",
                            "attention required", "ddos protection",
                            "checking if the site connection is secure",
                            "enable javascript",
                        ])
                        if not is_blocked:
                            break

                        # Try clicking Turnstile checkbox if visible
                        try:
                            turnstile = page.query_selector("iframe[src*='turnstile']")
                            if turnstile:
                                frame = turnstile.content_frame()
                                if frame:
                                    checkbox = frame.query_selector("input[type='checkbox']")
                                    if checkbox:
                                        checkbox.click()
                                        time.sleep(3)
                                        continue
                        except Exception:
                            pass

                        # Try clicking any Cloudflare challenge checkbox
                        try:
                            cf_checkbox = page.query_selector("#challenge-stage input[type='checkbox']")
                            if cf_checkbox:
                                cf_checkbox.click()
                                time.sleep(3)
                                continue
                        except Exception:
                            pass

                        time.sleep(3)

                    # Extra wait for JS-heavy sites (data tables, etc.)
                    # Check for common loading indicators
                    for selector in [
                        "text=Processing...", "text=Loading...",
                        ".dataTables_processing", ".loading",
                        "[aria-busy=true]", ".spinner",
                    ]:
                        try:
                            el = page.query_selector(selector)
                            if el and el.is_visible():
                                page.wait_for_selector(
                                    selector, state="hidden", timeout=10000
                                )
                        except Exception:
                            pass

                    # Final short wait for any remaining rendering
                    time.sleep(1)

                    html = page.content()
                    page_text = _extract_text(html)
                    links = _get_links(html, current_url)

                    results["pages_content"].append({
                        "url": current_url,
                        "title": page.title(),
                        "text_preview": page_text[:800],
                        "links_count": len(links),
                    })

                except Exception as e:
                    page_text = f"Navigation failed: {e}"

            elif action == "extract":
                results["final_result"] = action_data.get("content", response)
                break

            else:
                results["final_result"] = f"Unknown action: {action}"
                break

        browser.close()

    if results["final_result"] is None:
        results["final_result"] = "Max steps reached"

    return results


def _handle_browse(args: dict, **kw) -> str:
    task = args.get("task", "").strip()
    if not task:
        return tool_error("task is required — describe what to do on the web")

    max_steps = min(int(args.get("max_steps", 10)), 30)
    model = args.get("model", "tencent/hy3:free")

    if not _browser_lock.acquire(blocking=False):
        return tool_error("Another browser task is running. Wait for it to finish.")

    try:
        result = _run_browse(task=task, max_steps=max_steps, model=model)
        return json_result(result.get("success", False), data=result, error=result.get("error"))
    except Exception as e:
        return tool_error(f"Browser task failed: {e}")
    finally:
        _browser_lock.release()


_BROWSE_SCHEMA = {
    "name": "browse_autonomously",
    "description": (
        "Autonomous web browsing with anti-bot-detection. Opens a real Chromium browser, "
        "navigates pages, extracts content, and uses AI reasoning to complete tasks. "
        "Handles Cloudflare challenges. Use for: researching CVEs, reading GitHub/exploit-db, "
        "learning skills from websites, extracting data from protected pages."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": (
                    "What to do on the web. Be specific. Examples: "
                    "'Go to https://github.com/search?q=CVE-2021-41773 and extract the top 3 exploit PoCs', "
                    "'Visit https://www.exploit-db.com and find exploits for Apache 2.4.49'"
                ),
            },
            "max_steps": {
                "type": "integer",
                "description": "Maximum browser actions (default 10, max 30). Higher = more complex tasks.",
                "default": 10,
            },
            "model": {
                "type": "string",
                "description": "LLM model for browser reasoning (default: tencent/hy3:free)",
                "default": "tencent/hy3:free",
            },
        },
        "required": ["task"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="browse_autonomously",
        toolset=TOOLSET,
        schema=_BROWSE_SCHEMA,
        handler=lambda args, **kw: _handle_browse(args, **kw),
        emoji="🌐",
    )
