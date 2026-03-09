
import pandas as pd
import time
from xtea import decrypt as xtea_decrypt
from datetime import datetime

# File paths
log_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/xtea_transmission_log.csv'
output_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/xtea_decrypted_output.csv'

# Load the transmission log
df = pd.read_csv(log_path)

def decrypt_xtea(row):
    try:
        key = bytes.fromhex(row['Key_Hex'])
        encrypted = bytes.fromhex(row['Payload_Hex'])
        start = time.perf_counter()
        decrypted_bytes = xtea_decrypt(encrypted, key)
        end = time.perf_counter()
        decrypted_text = decrypted_bytes.decode(errors='ignore')
        decryption_time = round((end - start) * 1000, 4)
        return decrypted_text, decryption_time
    except Exception:
        return None, None

# Apply decryption
df[['Decrypted_Payload', 'Decryption_Time_ms']] = df.apply(lambda row: pd.Series(decrypt_xtea(row)), axis=1)

# Field extraction
def try_int(val):
    try:
        return int(val)
    except:
        return None

def parse_compact(compact):
    result = {
        "ITEM": None,
        "FW VERSION": None,
        "HW VERSION": None,
        "TEMPERATURE": None,
        "MILIVOLTS": None,
        "STATUS DATE": None
    }
    try:
        if not isinstance(compact, str) or not compact:
            return result
        if 'F' in compact: result["ITEM"] = try_int(compact.split('F')[0][1:])  # after I
        if 'F' in compact and 'H' in compact: result["FW VERSION"] = try_int(compact.split('F')[1].split('H')[0])
        if 'H' in compact and 'T' in compact: result["HW VERSION"] = try_int(compact.split('H')[1].split('T')[0])
        if 'T' in compact and 'M' in compact: result["TEMPERATURE"] = try_int(compact.split('T')[1].split('M')[0])
        if 'M' in compact and 'D' in compact: result["MILIVOLTS"] = try_int(compact.split('M')[1].split('D')[0])
        if 'D' in compact:
            dt_str = compact.split('D')[1]
            if dt_str.isdigit():
                result["STATUS DATE"] = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
    except:
        pass
    return result

# Parse all decrypted rows
parsed = df['Decrypted_Payload'].apply(parse_compact).apply(pd.Series)
df = pd.concat([df, parsed], axis=1)

# Save decrypted output
df.to_csv(output_path, index=False)
print(f"✅ Decrypted log saved to:\n{output_path}")
