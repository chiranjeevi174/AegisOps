"""
AegisOps — Automated UI Screenshot Capture Script
Uses Playwright with real Chrome to capture all 9 required genuine UI screenshots.
"""

import asyncio
import logging
import os
from pathlib import Path

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = Path("docs/images")
GRAFANA_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")


async def capture_screenshots():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1.25,  # Crisp high-DPI rendering
        )
        page = await context.new_page()

        print("\n[Step 1] Authenticating with AegisOps...")
        await page.goto("http://localhost:5173")
        await page.wait_for_load_state("networkidle")

        # Log in as sre-admin-bob (has all roles: operator, approver, requester, verifier, admin)
        await page.evaluate("""async () => {
            const res = await fetch('/api/v1/auth/session', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({identity: 'sre-admin-bob'}),
                credentials: 'include'
            });
            return res.status;
        }""")

        # 1. Dashboard
        print("[Step 2] Capturing 1/9: Dashboard (dashboard.png)...")
        await page.goto("http://localhost:5173/")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(OUTPUT_DIR / "dashboard.png"))
        print(" -> Saved docs/images/dashboard.png")

        # 2. Incident Management
        print(
            "[Step 3] Capturing 2/9: Incident Management (incident-management.png)..."
        )
        await page.goto("http://localhost:5173/incidents")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(OUTPUT_DIR / "incident-management.png"))
        print(" -> Saved docs/images/incident-management.png")

        # Fetch latest incident ID from API to view incident details
        inc_id = await page.evaluate("""async () => {
            const res = await fetch('/api/v1/incidents?limit=1');
            const data = await res.json();
            return data[0]?.id;
        }""")

        # 3. Incident Details
        print(
            f"[Step 4] Capturing 3/9: Incident Details (incident-details.png) for ID: {inc_id}..."
        )
        if inc_id:
            await page.goto(f"http://localhost:5173/incidents/{inc_id}")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(OUTPUT_DIR / "incident-details.png"))
            print(" -> Saved docs/images/incident-details.png")

        # 4. AI Investigation / RCA
        print(
            "[Step 5] Capturing 4/9: AI Investigation & RCA (ai-investigation.png)..."
        )
        await page.goto("http://localhost:5173/investigations")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)
        # Check if Execute AI Investigation is visible, if so click and wait
        exec_btn = await page.query_selector(
            "button:has-text('Execute AI Investigation')"
        )
        if exec_btn:
            await exec_btn.click()
            try:
                await page.wait_for_selector(
                    "button:has-text('Re-Run AI Investigation')", timeout=90000
                )
                await page.wait_for_selector(
                    "text=Observed Platform Evidence", timeout=30000
                )
                await page.wait_for_timeout(2000)
            except TimeoutError:
                logger.warning(
                    "Timed out waiting for investigation to finish rendering"
                )
        await page.screenshot(path=str(OUTPUT_DIR / "ai-investigation.png"))
        print(" -> Saved docs/images/ai-investigation.png")

        # 5. Remediation Planning
        print("[Step 6] Capturing 5/9: Remediation Plans (remediation-plan.png)...")
        await page.goto("http://localhost:5173/remediation")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(OUTPUT_DIR / "remediation-plan.png"))
        print(" -> Saved docs/images/remediation-plan.png")

        # 6. Human Approval Workflow
        print(
            "[Step 7] Capturing 6/9: Human Approval Workflow (approval-workflow.png)..."
        )
        await page.goto("http://localhost:5173/approvals")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(OUTPUT_DIR / "approval-workflow.png"))
        print(" -> Saved docs/images/approval-workflow.png")

        # 7. Execution Workflow & Registry
        print(
            "[Step 8] Capturing 7/9: Execution Engine & Registry (execution-details.png)..."
        )
        await page.goto("http://localhost:5173/executions")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)
        # Try inspecting the first execution modal for rich inspection view
        inspect_btn = await page.query_selector("button:has-text('Inspect')")
        if inspect_btn:
            await inspect_btn.click()
            await page.wait_for_timeout(1000)
        await page.screenshot(path=str(OUTPUT_DIR / "execution-details.png"))
        print(" -> Saved docs/images/execution-details.png")

        # 8. Post-Execution Verification & Rollback
        print(
            "[Step 9] Capturing 8/9: Verification & Rollback (verification-results.png)..."
        )
        await page.goto("http://localhost:5173/verifications")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)
        # Try inspecting first verification for statistical comparison
        verif_inspect = await page.query_selector("button:has-text('Inspect')")
        if verif_inspect:
            await verif_inspect.click()
            await page.wait_for_timeout(1000)
        await page.screenshot(path=str(OUTPUT_DIR / "verification-results.png"))
        print(" -> Saved docs/images/verification-results.png")

        # 9. Grafana Dashboard
        print(
            "[Step 10] Capturing 9/9: Grafana SRE Dashboard (grafana-dashboard.png)..."
        )
        grafana_page = await context.new_page()
        # Login to Grafana
        await grafana_page.goto("http://localhost:3000/login")
        await grafana_page.wait_for_load_state("networkidle")
        await grafana_page.fill("input[name='user']", GRAFANA_USER)
        await grafana_page.fill("input[name='password']", GRAFANA_PASSWORD)
        await grafana_page.click("button[type='submit']")
        await grafana_page.wait_for_load_state("networkidle")
        await grafana_page.wait_for_timeout(2000)

        # Open the AegisOps Platform Overview dashboard
        await grafana_page.goto(
            "http://localhost:3000/d/aegisops-overview/aegisops-platform-overview?kiosk"
        )
        await grafana_page.wait_for_load_state("networkidle")
        await grafana_page.wait_for_timeout(3500)
        await grafana_page.screenshot(path=str(OUTPUT_DIR / "grafana-dashboard.png"))
        print(" -> Saved docs/images/grafana-dashboard.png")

        await browser.close()
        print("\nAll 9 genuine UI screenshots captured successfully!")


if __name__ == "__main__":
    asyncio.run(capture_screenshots())
