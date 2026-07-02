import pandas as pd
import json
import sys

try:
    xls = pd.ExcelFile("2026.xlsx")
    all_data = {}
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = df.astype(str)
        all_data[sheet_name] = df.to_dict(orient="records")
        
    with open("excel_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"SUCCESS: Read {len(xls.sheet_names)} sheets: {xls.sheet_names}")
except Exception as e:
    print(f"ERROR: {e}")
