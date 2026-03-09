import pandas as pd
import time
from speck import decrypt as speck_decrypt  # Import custom SPECK decryption function
from datetime import datetime

# -------------------- File Paths --------------------
log_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/speck_transmission_log.csv'
output_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/speck_decrypted_output.csv'

# ---------------- Load Transmission Log ----------------
df = pd.read_csv(log_path)  # Load previously logged transmission data

# ------------------ Decryption Function ------------------
def decrypt_speck(row):
    """
    Decrypts a single row's payload using the corresponding SPECK key.
    Returns: decrypted string, decryption time in milliseconds
    """
    try:
        key = bytes.fromhex(row['Key_Hex'])              # Convert hex string back to bytes
        encrypted = bytes.fromhex(row['Payload_Hex'])    # Convert encrypted hex payload to bytes
        start = time.perf_counter()
        decrypted_bytes = speck_decrypt(encrypted, key)  # Decrypt using custom speck_decrypt function
        end = time.perf_counter()
        decrypted_text = decrypted_bytes.decode(errors='ignore')  # Convert bytes to string
        decryption_time = round((end - start) * 1000, 4)  # Decryption time in ms
        return decrypted_text, decryption_time
    except Exception:
        return None, None

# ---------------- Apply Decryption to Each Row ----------------
# Generates two new columns: Decrypted_Payload and Decryption_Time_ms
df[['Decrypted_Payload', 'Decryption_Time_ms']] = df.apply(
    lambda row: pd.Series(decrypt_speck(row)), axis=1
)

# ------------------- Data Parsing Functions -------------------
def try_int(val):
    """Tries to convert a value to integer, returns None if it fails."""
    try:
        return int(val)
    except:
        return None

def parse_compact(compact):
    """
    Parses a compact encoded payload string and extracts structured fields.
    Input: A string like 'I12F104H202T25M3400D20250625213545'
    Output: Dictionary with parsed fields.
    """
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

        # Parse each field by splitting at tag boundaries
        if 'F' in compact: result["ITEM"] = try_int(compact.split('F')[0][1:])
        if 'F' in compact and 'H' in compact: result["FW VERSION"] = try_int(compact.split('F')[1].split('H')[0])
        if 'H' in compact and 'T' in compact: result["HW VERSION"] = try_int(compact.split('H')[1].split('T')[0])
        if 'T' in compact and 'M' in compact: result["TEMPERATURE"] = try_int(compact.split('T')[1].split('M')[0])
        if 'M' in compact and 'D' in compact: result["MILIVOLTS"] = try_int(compact.split('M')[1].split('D')[0])

        # Convert compact datetime string to datetime object
        if 'D' in compact:
            dt_str = compact.split('D')[1]
            if dt_str.isdigit():
                result["STATUS DATE"] = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
    except:
        pass
    return result

# ------------------ Parse Decrypted Payload ------------------
# Applies the parser to each decrypted payload and expands into columns
parsed = df['Decrypted_Payload'].apply(parse_compact).apply(pd.Series)

# Append parsed columns to the original DataFrame
df = pd.concat([df, parsed], axis=1)

# ------------------ Save Output to CSV ------------------
df.to_csv(output_path, index=False)
print(f"✅ Decrypted log saved to:\n{output_path}")
