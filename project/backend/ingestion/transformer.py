from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

class GECTransformer:
    """
    Handles deep JSON flattening and data normalization for GEC Excels.
    Ensures all 153+ columns are preserved in the 'raw_metrics' field.
    """

    @staticmethod
    def flatten_row(row: pd.Series, column_map: Dict[int, str]) -> Dict[str, Any]:
        """
        Convert a raw pandas Series into a dictionary with both 
        canonical fields and a 'raw_metrics' JSONB payload.
        """
        raw_data = {}
        for idx, val in row.items():
            # Get canonical name if mapped, otherwise use 'col_{idx}'
            key = column_map.get(idx, f"col_{idx}")
            
            # Clean value
            if pd.isna(val) or str(val).strip().lower() in ("nan", "none", ""):
                raw_data[key] = None
            else:
                try:
                    # Try converting to float if it looks numeric
                    if isinstance(val, str):
                        clean_v = val.replace(",", "").strip()
                        if clean_v.replace(".", "", 1).isdigit():
                            raw_data[key] = float(clean_v)
                        else:
                            raw_data[key] = val
                    else:
                        raw_data[key] = val
                except:
                    raw_data[key] = val
                    
        return raw_data

    @staticmethod
    def build_metadata(row: Dict[str, Any], exclude_keys: List[str]) -> Dict[str, Any]:
        """
        Extract all fields NOT in the primary schema into a metadata dict.
        """
        return {k: v for k, v in row.items() if k not in exclude_keys and v is not None}
