# skills/visual_regression.py
from pathlib import Path
from PIL import Image, ImageChops
from playwright.async_api import async_playwright
from skills.base import NedsterSkill

SCREENSHOT_DIR = Path(".nedster/screenshots")

class VisualRegressionCheck(NedsterSkill):
    name = "visual_regression_check"
    description = "Screenshot the live deployed site and diff it against the previous deploy's screenshot."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "deploy_id": {"type": "string"},
            "diff_threshold_pct": {"type": "number", "default": 1.5},
        },
        "required": ["url", "deploy_id"],
    }

    async def run(self, url: str, deploy_id: str, diff_threshold_pct: float = 1.5) -> dict:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        current_path = SCREENSHOT_DIR / f"{deploy_id}.png"

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1280, "height": 800})
            await page.goto(url, wait_until="networkidle")
            await page.screenshot(path=str(current_path), full_page=True)
            await browser.close()

        previous_screenshots = sorted(
            [f for f in SCREENSHOT_DIR.glob("*.png") if f != current_path],
            key=lambda f: f.stat().st_mtime,
        )
        if not previous_screenshots:
            return {"status": "baseline_set", "screenshot": str(current_path)}

        prev_img = Image.open(previous_screenshots[-1]).convert("RGB")
        curr_img = Image.open(current_path).convert("RGB")
        if prev_img.size != curr_img.size:
            curr_img = curr_img.resize(prev_img.size)

        diff = ImageChops.difference(prev_img, curr_img)
        diff_pixels = sum(1 for px in diff.getdata() if any(c > 15 for c in px))
        total_pixels = prev_img.size[0] * prev_img.size[1]
        diff_pct = round((diff_pixels / total_pixels) * 100, 2)

        return {
            "status": "regression" if diff_pct > diff_threshold_pct else "ok",
            "diff_pct": diff_pct, "threshold_pct": diff_threshold_pct,
            "current_screenshot": str(current_path),
            "previous_screenshot": str(previous_screenshots[-1]),
        }
