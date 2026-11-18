// Record showcase/video/demo.html (1280x720, ~49 s) to showcase/demo.mp4 and a poster frame.
// Usage: node scripts/record_demo.cjs   (needs Playwright with Chromium, and ffmpeg)
const path = require("path");
const fs = require("fs");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright");

(async () => {
  const root = path.resolve(__dirname, "..");
  const tmp = fs.mkdtempSync(path.join(require("os").tmpdir(), "demo-"));
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: tmp, size: { width: 1280, height: 720 } } });
  const page = await context.newPage();
  const t0 = Date.now();
  await page.goto("file://" + path.join(root, "showcase/video/demo.html"));
  await page.waitForFunction(() => window.__ready === true);
  const lead = (Date.now() - t0) / 1000;
  await page.waitForTimeout(49500);
  const video = await page.video().path();
  await context.close();
  // poster: the four verdicts, from a fresh page so no timer of the recording is still running
  const still = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await still.goto("file://" + path.join(root, "showcase/video/demo.html#manual"));
  await still.waitForFunction(() => window.__ready === true);
  await still.evaluate(() => { show("s-four"); ["c1","c2","c3","c4"].forEach(c => { $(c).classList.add("on","stamped"); }); });
  await still.waitForTimeout(900);
  await still.screenshot({ path: path.join(root, "showcase/poster.jpg"), type: "jpeg", quality: 88 });
  await browser.close();
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-ss", String(Math.max(0, lead)), "-i", video, "-t", "49",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-preset", "slow", "-r", "30", "-movflags", "+faststart", "-an",
    path.join(root, "showcase/demo.mp4")]);
  console.log("wrote showcase/demo.mp4 and showcase/poster.jpg (lead trimmed:", lead.toFixed(2), "s)");
})();
