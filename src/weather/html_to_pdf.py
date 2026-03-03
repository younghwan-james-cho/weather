"""HTML to PDF converter with dark mode preservation.

Uses Playwright to render HTML exactly as displayed in a browser,
preserving all CSS styling including dark mode themes.
"""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

PROJECT_DIR = Path(__file__).parent.parent.parent  # weather/
REPORTS_DIR = PROJECT_DIR / "reports"


async def html_to_pdf(
    html_path: Path,
    pdf_path: Path | None = None,
    *,
    width: str = "1200px",
    scale: float = 1.0,
) -> Path:
    """Convert HTML file to PDF with dark mode preserved.

    Args:
        html_path: Path to the HTML file
        pdf_path: Output PDF path (default: same name as HTML with .pdf extension)
        width: Viewport width for rendering
        scale: Scale factor for the PDF (default 1.0)

    Returns:
        Path to the generated PDF file

    """
    html_path = Path(html_path).resolve()
    if pdf_path is None:
        pdf_path = html_path.with_suffix(".pdf")
    else:
        pdf_path = Path(pdf_path).resolve()

    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)

        # Create page with dark color scheme preference
        context = await browser.new_context(
            color_scheme="dark",
            viewport={"width": 1200, "height": 800},
        )
        page = await context.new_page()

        # Navigate to the HTML file
        await page.goto(f"file://{html_path}")

        # Wait for fonts and content to load
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(0.5)  # Extra wait for font rendering

        # Generate PDF with dark mode colors preserved
        await page.pdf(
            path=str(pdf_path),
            format="A4",
            scale=scale,
            print_background=True,  # Critical: preserves background colors
            prefer_css_page_size=False,
            margin={
                "top": "10mm",
                "bottom": "10mm",
                "left": "10mm",
                "right": "10mm",
            },
        )

        await browser.close()

    return pdf_path


def main() -> None:
    """Convert robustness_complete.html to PDF."""
    html_file = REPORTS_DIR / "robustness_complete.html"
    pdf_file = REPORTS_DIR / "robustness_complete.pdf"

    if not html_file.exists():
        print(f"[ERR] HTML file not found: {html_file}")
        return

    print(f"[INFO] Converting: {html_file}")
    print(f"[INFO] Output: {pdf_file}")

    pdf_path = asyncio.run(html_to_pdf(html_file, pdf_file))

    print(f"[OK] PDF generated: {pdf_path}")
    print(f"[OK] Size: {pdf_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
