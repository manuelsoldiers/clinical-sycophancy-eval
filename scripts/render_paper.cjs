// Render paper/paper.html to paper/clinical-sycophancy-eval.pdf with headless Chromium.
// Usage: node scripts/render_paper.cjs
const path = require("path");
const { chromium } = require("playwright");
(async () => {
  const root = path.resolve(__dirname, "..");
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + path.join(root, "paper/paper.html"), { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: path.join(root, "paper/clinical-sycophancy-eval.pdf"),
    format: "A4", printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: "<span></span>",
    footerTemplate: '<div style="width:100%;font-size:7.5px;color:#55635f;padding:0 19mm;display:flex;justify-content:space-between;font-family:sans-serif">'
      + '<span>Soldatini · When the patient pushes back · v1.0</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
  });
  await browser.close();
  console.log("wrote paper/clinical-sycophancy-eval.pdf");
})();
