"""
Visualize Weather Analysis Results (Strict 4-Page Layout)
- Reads weather_analysis_formatted.xlsx
- Generates a PDF with EXACTLY 4 pages:
  Page 1: Portfolio Sorts (MAX) - EW & VW
  Page 2: Portfolio Sorts (IVOL) - EW & VW
  Page 3: Fama-MacBeth (First 3 Variables)
  Page 4: Fama-MacBeth (Last 3 Variables)
"""

import pandas as pd
import asyncio
from pathlib import Path
from html_to_pdf import html_to_pdf

PROJECT_DIR = Path(__file__).parent.parent.parent
REPORTS_DIR = PROJECT_DIR / "reports"
EXCEL_PATH = REPORTS_DIR / "weather_analysis_formatted.xlsx"
HTML_PATH = REPORTS_DIR / "weather_analysis_visualized.html"

# CSS for Strict Pagination
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600&display=swap');

    @page {
        margin: 10mm;
        size: A4;
    }

    body {
        font_family: 'Inter', sans-serif;
        color: #000;
        line-height: 1.1;
        max_width: 100%;
        margin: 0;
        padding: 0;
        background-color: #fff;
        font-size: 7.5pt;
    }

    /* Page Containers */
    .page {
        height: 270mm; /* Approx A4 printable height */
        page-break-after: always;
        overflow: hidden;
        position: relative;
    }

    .page:last-child {
        page-break-after: avoid;
    }

    h2 {
        text-align: center;
        margin: 0 0 10px 0;
        font-size: 11pt;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-bottom: 2px solid #000;
        padding-bottom: 5px;
    }

    /* Two-Column Layout within Page */
    .grid-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8mm;
        align-items: start;
    }

    .table-section {
        margin-bottom: 10px;
    }
    
    h3 {
        margin: 0 0 5px 0;
        font-size: 8pt;
        text-transform: uppercase;
        background: #eee;
        padding: 4px;
        text-align: center;
        border: 1px solid #000;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        border: 1px solid #000;
    }

    th {
        background-color: #fff;
        font-weight: 600;
        font-size: 6.5pt;
        text-transform: uppercase;
        padding: 3px 2px;
        text-align: center;
        border-bottom: 1px solid #000;
    }

    th:first-child {
        text-align: left;
        width: 25%;
        padding-left: 4px;
    }

    td {
        padding: 2px;
        border-bottom: 1px solid #ddd;
        text-align: center;
        font-size: 7pt;
    }

    td:first-child {
        text-align: left;
        font-weight: 500;
        padding-left: 4px;
    }
    
    tr:last-child td {
        border-bottom: none;
    }

    /* Significance Styling */
    .sig {
        font-weight: 700;
        color: #000; /* Keep black for professional print, rely on bold */
        text-decoration: underline; /* Add underline for clarity if B&W */
    }
    
    .negative-sig {
        font-weight: 700;
        color: #000;
        font-style: italic;
    }
    
    /* Rows */
    .row-tvalue {
        color: #555;
        font-size: 6pt;
    }
</style>
"""

def generate_html():
    print(f"Reading {EXCEL_PATH}...")
    xls = pd.ExcelFile(EXCEL_PATH)
    
    # Helper to clean sheet names for display
    def clean_name(name):
        return name.replace("Portfolio_", "").replace("FM_", "").replace("_", " ")

    # Helper to render a single table from a sheet dataframe
    def render_table(sheet_name):
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None).fillna('')
        html = []
        html.append(f"<table>")
        
        for idx, row in df.iterrows():
            row_list = row.tolist()
            non_empty = [x for x in row_list if x != '']
            
            if len(non_empty) == 0: continue
            
            # Title Row (e.g. "Portfolio - Sunny")
            if len(non_empty) == 1:
                title = non_empty[0].split("-")[-1].strip() # Extract "Sunny"
                html.append(f"<tr><td colspan='{len(row_list)}' style='background:#f0f0f0; font-weight:bold; font-size:7pt; text-align:center;'>{title}</td></tr>")
            
            # Header Row
            elif 'Type' in row_list:
                html.append("<tr>")
                for col in row_list:
                    c = str(col).replace("Normal-High", "N-H").replace("Normal-Low", "N-L")
                    html.append(f"<th>{c}</th>")
                html.append("</tr>")
            
            # Data Row
            else:
                row_type = row_list[1]
                tr_class = "row-tvalue" if row_type == "T-value" else "row-estimate"
                html.append(f"<tr class='{tr_class}'>")
                for i, col in enumerate(row_list):
                    val = str(col)
                    style = ""
                    try:
                        num = float(val)
                        if abs(num) >= 1.96 and i > 1:
                            style = "class='sig'" if num > 0 else "class='negative-sig'"
                    except:
                        pass
                    
                    if row_type == "T-value" and i > 1 and val != '':
                        val = f"({val})"
                    html.append(f"<td {style}>{val}</td>")
                html.append("</tr>")
        
        html.append("</table>")
        return "".join(html)

    # PAGE 1: MAX Portfolios (EW & VW)
    page1 = []
    page1.append("<div class='page'>")
    page1.append("<h2>Portfolio Sorts: MAX Effect</h2>")
    page1.append("<div class='grid-container'>")
    
    # Left Column: EW
    page1.append("<div>")
    page1.append(f"<h3>Equal-Weighted</h3>{render_table('Portfolio_MAX1_EW')}")
    page1.append("</div>")
    
    # Right Column: VW
    page1.append("<div>")
    page1.append(f"<h3>Value-Weighted</h3>{render_table('Portfolio_MAX1_VW')}")
    page1.append("</div>")
    
    page1.append("</div></div>") # End Grid / Page

    # PAGE 2: IVOL Portfolios (EW & VW)
    page2 = []
    page2.append("<div class='page'>")
    page2.append("<h2>Portfolio Sorts: IVOL Effect</h2>")
    page2.append("<div class='grid-container'>")
    
    # Left Column: EW
    page2.append("<div>")
    page2.append(f"<h3>Equal-Weighted</h3>{render_table('Portfolio_IVOL_EW')}")
    page2.append("</div>")
    
    # Right Column: VW
    page2.append("<div>")
    page2.append(f"<h3>Value-Weighted</h3>{render_table('Portfolio_IVOL_VW')}")
    page2.append("</div>")
    
    page2.append("</div></div>") # End Grid / Page

    # --- FM Pages Helper ---
    def get_fm_chunks(sheet_name):
        if sheet_name not in xls.sheet_names:
            print(f"Warning: Sheet {sheet_name} not found.")
            return []
        
        df_fm = pd.read_excel(xls, sheet_name=sheet_name, header=None).fillna('')
        chunks = []
        current_chunk = []
        
        for idx, row in df_fm.iterrows():
            row_list = row.tolist()
            non_empty = [x for x in row_list if x != '']
            
            if len(non_empty) == 1:
                # Title row (e.g. "Fama-MacBeth ... - Cloudy")
                if current_chunk: chunks.append(current_chunk)
                current_chunk = [row] 
            else:
                current_chunk.append(row)
        if current_chunk: chunks.append(current_chunk)
        return chunks

    def render_fm_page(chunks_list, title_main):
        html = []
        html.append("<div class='page'>")
        html.append(f"<h2>{title_main}</h2>")
        html.append("<div class='grid-container'>")
        
        for i, chunk in enumerate(chunks_list):
            chunk_html = ["<table>"]
            
            # Title Processing
            title_row = chunk[0].tolist()
            # Extract "Cloudy" from "Fama-MacBeth (MAX Model) - Cloudy"
            title_text = [x for x in title_row if x != ''][0].split("-")[-1].strip()
            chunk_html.append(f"<tr><td colspan='7' style='background:#f0f0f0; font-weight:bold; font-size:7pt; text-align:center;'>{title_text}</td></tr>")
            
            for row in chunk[1:]:
                row_list = row.tolist()
                if 'Type' in row_list:
                     chunk_html.append("<tr>")
                     for col in row_list:
                         c = str(col).replace("Normal-High", "N-H").replace("Normal-Low", "N-L")
                         html_val = f"<th>{c}</th>" if c else "<th></th>"
                         chunk_html.append(html_val)
                     chunk_html.append("</tr>")
                else:
                    row_type = row_list[1]
                    tr_class = "row-tvalue" if row_type == "T-value" else "row-estimate"
                    chunk_html.append(f"<tr class='{tr_class}'>")
                    for k, col in enumerate(row_list):
                        val = str(col)
                        style = ""
                        try:
                            num = float(val)
                            # Significance check (cols > 1 are numeric data)
                            if abs(num) >= 1.96 and k > 1:
                                style = "class='sig'" if num > 0 else "class='negative-sig'"
                        except:
                            pass
                        
                        if row_type == "T-value" and k > 1 and val != '':
                            val = f"({val})"
                        chunk_html.append(f"<td {style}>{val}</td>")
                    chunk_html.append("</tr>")
            
            chunk_html.append("</table>")
            html.append(f"<div class='table-section'>{''.join(chunk_html)}</div>")
            
        html.append("</div></div>")
        return "".join(html)

    # PAGE 3: FM MAX Model (All 6 vars)
    fm_max_chunks = get_fm_chunks('FM_MAX1')
    page3 = render_fm_page(fm_max_chunks, "Fama-MacBeth: MAX Model")

    # PAGE 4: FM IVOL Model (All 6 vars)
    fm_ivol_chunks = get_fm_chunks('FM_IVOL')
    page4 = render_fm_page(fm_ivol_chunks, "Fama-MacBeth: IVOL Model")

    # Assemble
    full_html = [
        "<!DOCTYPE html><html><head>",
        CSS,
        "</head><body>",
        "".join(page1),
        "".join(page2),
        page3,
        page4,
        "</body></html>"
    ]
    
    with open(HTML_PATH, "w") as f:
        f.write("\n".join(full_html))
    return HTML_PATH

def main():
    if not EXCEL_PATH.exists():
        print(f"Error: {EXCEL_PATH} not found.")
        return

    html_file = generate_html()
    print(f"HTML saved to {html_file}")
    
    pdf_file = HTML_PATH.with_suffix(".pdf")
    print(f"Converting to PDF: {pdf_file}")
    
    asyncio.run(html_to_pdf(html_file, pdf_file, scale=1.0))
    print("Done.")

if __name__ == "__main__":
    main()
