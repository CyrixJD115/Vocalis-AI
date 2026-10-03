// Screenshot harness: boots the mock server, drives the UI in headless chromium
// and captures the main states. Usage: node scripts/screenshot.mjs [outdir]
import { chromium } from "playwright-core";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = process.argv[2] || "/tmp/vc-ui-shots";
fs.mkdirSync(outDir, { recursive: true });

const PORT = 8899;
const BASE = `http://127.0.0.1:${PORT}`;

const mock = spawn("node", [path.join(__dirname, "mock-server.mjs"), String(PORT)], { stdio: "pipe" });
await new Promise((r) => setTimeout(r, 800));

const browser = await chromium.launch({
    executablePath: "/usr/sbin/chromium",
    headless: true,
    args: ["--no-sandbox", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.on("console", (msg) => {
    if (msg.type() === "error") console.log("[console.error]", msg.text());
});
page.on("pageerror", (err) => console.log("[pageerror]", err.message));

const shot = async (name) => {
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, `${name}.png`) });
    console.log("saved", name);
};

try {
    await page.goto(BASE, { waitUntil: "networkidle" });
    await shot("01-welcome-dialog");

    // close welcome
    await page.getByRole("button", { name: "Start", exact: true }).click();
    await shot("02-main");

    // model slot manager
    await page.getByRole("button", { name: "edit", exact: true }).click();
    await shot("03-slot-manager");
    await page.getByText("close", { exact: true }).click();

    // advanced setting
    await page.getByRole("button", { name: "Advanced Setting" }).click();
    await shot("04-advanced-setting");
    await page.locator("div.absolute.inset-0").click({ position: { x: 10, y: 10 } });
    await page.waitForTimeout(300);

    // merge lab
    await page.getByRole("button", { name: "Merge Lab" }).click();
    await shot("06-merge-lab");
    await page.locator("div.absolute.inset-0").click({ position: { x: 10, y: 10 } });
    await page.waitForTimeout(300);

    // server mode
    await page.getByRole("radio", { name: "server" }).check();
    await shot("07-server-mode");
    await page.getByRole("radio", { name: "client" }).check();

    // start button guard (no device selected -> toast)
    await page.getByRole("button", { name: "start", exact: true }).first().click();
    await shot("09-start-guard-toast");

    // narrow viewport
    await page.setViewportSize({ width: 900, height: 1200 });
    await shot("08-narrow");
} catch (e) {
    console.error("screenshot run failed:", e);
    await shot("99-failure").catch(() => {});
} finally {
    await browser.close();
    mock.kill();
}
