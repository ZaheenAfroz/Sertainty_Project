
import pandas as pd
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from datetime import datetime

# === File Paths ===
# Path to the encrypted AES-256 transmission log (CSV)
log_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/aes256_transmission_log.csv'

# Path to save the decrypted output and parsed fields
output_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/aes256_decrypted_output.csv'

# === Load Encrypted Transmission Data ===
df = pd.read_csv(log_path)  # The CSV must contain columns: 'Key_Hex', 'Nonce_Hex', 'Payload_Hex'

# === AES-256-GCM Decryption Function ===
def decrypt_aes(row):
    """
    Decrypts AES-GCM encrypted payload using the provided key and nonce.
    Measures decryption time in milliseconds.

    Args:
        row (pd.Series): A row from the DataFrame containing 'Key_Hex', 'Nonce_Hex', 'Payload_Hex'.

    Returns:
        Tuple[str, float]: Decrypted string and decryption time in ms. Returns (None, None) on failure.
    """
    try:
        key = bytes.fromhex(row['Key_Hex'])        # 256-bit key (32 bytes)
        nonce = bytes.fromhex(row['Nonce_Hex'])    # 96-bit nonce (12 bytes)
        encrypted = bytes.fromhex(row['Payload_Hex'])[12:]  # Skip embedded nonce if present
        aesgcm = AESGCM(key)

        start = time.perf_counter()
        decrypted_bytes = aesgcm.decrypt(nonce, encrypted, b"")  # Empty associated data
        end = time.perf_counter()

        decrypted_text = decrypted_bytes.decode()  # Convert bytes to UTF-8 string
        decryption_time = round((end - start) * 1000, 4)  # Decryption time in ms
        return decrypted_text, decryption_time

    except Exception:
        return None, None

# === Apply Decryption to All Rows ===
# Adds two new columns: Decrypted_Payload and Decryption_Time_ms
df[['Decrypted_Payload', 'Decryption_Time_ms']] = df.apply(
    lambda row: pd.Series(decrypt_aes(row)), axis=1
)

# === Utility: Safe Integer Conversion ===
def try_int(val):
    """
    Safely converts a string to integer. Returns None on failure.
    """
    try:
        return int(val)
    except:
        return None

# === Compact String Parser ===
def parse_compact(compact):
    """
    Extracts structured fields from a decrypted payload string formatted like:
    'I001F001H001T024M3620D20250625125032'

    Args:
        compact (str): Decrypted string containing sensor metadata.

    Returns:
        dict: Dictionary with parsed values (ITEM, FW VERSION, etc.)
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

        # Extract fields based on letter delimiters
        if 'F' in compact: result["ITEM"] = try_int(compact.split('F')[0][1:])
        if 'F' in compact and 'H' in compact: result["FW VERSION"] = try_int(compact.split('F')[1].split('H')[0])
        if 'H' in compact and 'T' in compact: result["HW VERSION"] = try_int(compact.split('H')[1].split('T')[0])
        if 'T' in compact and 'M' in compact: result["TEMPERATURE"] = try_int(compact.split('T')[1].split('M')[0])
        if 'M' in compact and 'D' in compact: result["MILIVOLTS"] = try_int(compact.split('M')[1].split('D')[0])

        # Convert date string to datetime format
        if 'D' in compact:
            dt_str = compact.split('D')[1]
            if dt_str.isdigit():
                result["STATUS DATE"] = datetime.strptime(dt_str, "%Y%m%d%H%M%S")

    except:
        pass  # Return partially parsed result if any step fails

    return result

# === Parse and Expand Decrypted Payloads ===
# Apply parsing to the decrypted payload column
parsed = df['Decrypted_Payload'].apply(parse_compact).apply(pd.Series)

# Concatenate the parsed results back to the original DataFrame
df = pd.concat([df, parsed], axis=1)

# === Save Final Output ===
# Save the full DataFrame with decrypted payloads and extracted fields
df.to_csv(output_path, index=False)
print(f"✅ Decrypted log saved to:\n{output_path}")
