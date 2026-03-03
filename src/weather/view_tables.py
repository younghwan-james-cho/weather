import pandas as pd
from pathlib import Path

# Load Excel blocks
xl = pd.ExcelFile('reports/chen_2025_replication.xlsx')
table_1 = xl.parse('Table 1 (MAX Sort)')
table_13 = xl.parse('Table 13 (FM Reg)')

# Replace NaNs with blanks
table_1 = table_1.fillna('')
table_13 = table_13.fillna('')

# Generate HTML
html = f"""
<html>
<head>
<style>
    body {{ font-family: "Times New Roman", Times, serif; padding: 40px; background-color: #ffffff; color: #000000; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 1200px; margin-bottom: 50px; font-size: 14px; border-top: 2px solid black; border-bottom: 2px solid black; }}
    th, td {{ border: none; padding: 6px 10px; text-align: left; }}
    th {{ font-weight: bold; border-bottom: 1px solid black; }}
    td {{ background-color: transparent; }}
    .title {{ font-size: 16px; font-weight: bold; margin-bottom: 5px; }}
    .subtitle {{ font-size: 14px; margin-bottom: 15px; font-style: italic; }}
</style>
</head>
<body>
    <div class="title">Table 1: Weekly Portfolios Sorted on MAX</div>
    {table_1.to_html(index=False)}
    
    <div class="title">Table 13: Fama-MacBeth Regressions</div>
    {table_13.to_html(index=False)}
</body>
</html>
"""

with open('reports/tables.html', 'w') as f:
    f.write(html)

print("Saved reports/tables.html")
