import pandas as pd
import os
from pathlib import Path
from typing import List, Dict


class EPCAnalyzer:
    def __init__(self):
        self.min_prefix_length = 6
        self.analysis_results = []
    
    def load_epcs(self, file_path: str) -> List[str]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        epcs = []
        if path.suffix.lower() in ['.txt', '.csv']:
            with open(path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    epc = line.strip()
                    if epc and len(epc) == 24 and all(c in '0123456789ABCDEFabcdef' for c in epc):
                        epcs.append(epc.upper())
                    elif epc:
                        print(f"Skipping invalid EPC at line {line_num}: {epc}")
        
        elif path.suffix.lower() == '.xlsx':
            df = pd.read_excel(path, header=None, engine='openpyxl')
            for idx, epc in enumerate(df.iloc[:, 0], 1):
                epc = str(epc).strip()
                if len(epc) == 24 and all(c in '0123456789ABCDEFabcdef' for c in epc):
                    epcs.append(epc.upper())
                else:
                    print(f"Skipping invalid EPC at row {idx}: {epc}")
        
        else:
            raise ValueError("Unsupported file format. Use .txt, .csv, or .xlsx")
        
        if not epcs:
            raise ValueError("No valid EPCs found in file")
        
        print(f"Loaded {len(epcs)} valid EPCs from {path.name}")
        return epcs
    
    def group_and_analyze(self, epcs: List[str]) -> pd.DataFrame:
        groups = []
        remaining = epcs[:]
        
        while remaining:
            base = remaining.pop(0)
            group = [base]
            i = 0
            while i < len(remaining):
                common_len = sum(1 for a, b in zip(base, remaining[i]) if a == b)
                if common_len >= self.min_prefix_length:
                    group.append(remaining.pop(i))
                else:
                    i += 1
            groups.append(group)
        
        results = []
        for gid, group in enumerate(groups, 1):
            if len(group) == 1:
                results.append({
                    'Group_ID': gid,
                    'Prefix': '',
                    'Prefix_Bytes': 0,
                    'Suffix_Bytes': 12,
                    'Suffix_Count': 1,
                    'Total_Payload_Bytes': 14,
                    'EPCs_SF7_51B': 3,
                    'EPCs_SF12_11B': 0,
                    'Compression_%': 0
                })
            else:
                prefix_len = min(len(min(group, key=len)), 
                               max(self.min_prefix_length,
                                   sum(1 for chars in zip(*group) if len(set(chars)) == 1)))
                
                prefix = group[0][:prefix_len]
                prefix_bytes = prefix_len // 2
                suffix_bytes = (24 - prefix_len) // 2
                suffix_count = len(group)
                
                total_payload = 2 + prefix_bytes + (suffix_count * suffix_bytes)
                overhead = 2 + prefix_bytes
                epcs_sf7 = max(0, (51 - overhead) // suffix_bytes) if suffix_bytes > 0 else 0
                epcs_sf12 = max(0, (11 - overhead) // suffix_bytes) if suffix_bytes > 0 else 0
                uncompressed = len(group) * 12
                compression = round(((uncompressed - total_payload) / uncompressed * 100), 1)
                
                results.append({
                    'Group_ID': gid,
                    'Prefix': prefix,
                    'Prefix_Bytes': prefix_bytes,
                    'Suffix_Bytes': suffix_bytes,
                    'Suffix_Count': suffix_count,
                    'Total_Payload_Bytes': total_payload,
                    'EPCs_SF7_51B': epcs_sf7,
                    'EPCs_SF12_11B': epcs_sf12,
                    'Compression_%': compression
                })
        
        self.analysis_results = results
        return pd.DataFrame(results)
    
    def save_results(self, df: pd.DataFrame, output_path: str) -> str:
        """✅ CORRIGÉ : Sauvegarde directe du DataFrame reçu"""
        try:
            df.to_excel(output_path, index=False, engine='openpyxl')
            print(f"✅ Excel file created successfully at: {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ Error saving Excel file: {e}")
            return None
    
    def print_summary(self, df: pd.DataFrame):
        print("\n" + "="*80)
        print("EPC LoRaWAN Compression Analysis")
        print("="*80)
