import json

def run():
    with open("excel_data.json", "r", encoding="utf-8") as f:
        all_data = json.load(f)
        
    for sheet_name, rows in all_data.items():
        print(f"=== SHEET: {sheet_name} ===")
        for i, row in enumerate(rows):
            # Coba cari key yang mengandung kata 'Case' atau 'Troubleshot' atau 'Root'
            case = row.get('Case') or row.get('Unnamed: 4') or row.get('CASE') or ""
            troubleshoot = row.get('TROUBLESHOT MKT') or row.get('Unnamed: 7') or row.get('TROUBLESHOOT') or ""
            root_cause = row.get('Root Couse ') or row.get('Unnamed: 6') or row.get('ROOT CAUSE') or ""
            
            values = [str(v) for v in row.values() if str(v).strip() != 'nan' and str(v).strip() != '']
            if len(values) > 3:
                # cek apakah ini row header dengan mengecek apakah valuesnya berisi kata-kata seperti TANGGAL
                if "TANGGAL" in values and "CASE" in values:
                    continue
                
                print(f"--- Row {i} ---")
                for k, v in row.items():
                    if str(v).strip() != 'nan' and str(v).strip() != '':
                        print(f"{k}: {v}")
        print("\n\n")

if __name__ == "__main__":
    run()
