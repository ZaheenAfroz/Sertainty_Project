import pandas as pd
import time
from ascon import decrypt
from datetime import datetime

# === File paths ===
log_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/ascon_transmission_log.csv'
output_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/ascon_decrypted_output.csv'
VARIANT = "Ascon-128"  # Specifies which ASCON variant is used (e.g., Ascon-128)

# === Load the encrypted transmission log ===
df = pd.read_csv(log_path)

# === Function to decrypt ASCON encrypted payloads ===
def decrypt_ascon(row):
    try:
        # Convert key and nonce from hex to bytes
        key = bytes.fromhex(row['Key_Hex'])
        nonce = bytes.fromhex(row['Nonce_Hex'])

        # Extract the actual ciphertext (excluding the nonce which is the first 16 bytes)
        encrypted = bytes.fromhex(row['Payload_Hex'])[16:]

        # Measure decryption time
        start = time.perf_counter()
        decrypted_bytes = decrypt(
            key=key,
            nonce=nonce,
            associateddata=b"",
            ciphertext=encrypted,
            variant=VARIANT
        )
        end = time.perf_counter()

        # Decode the result into plaintext string
        decrypted_text = decrypted_bytes.decode()
        decryption_time = round((end - start) * 1000, 4)  # Convert time to milliseconds
        return decrypted_text, decryption_time
    except Exception:
        return None, None  # In case of decryption or decoding failure

# === Apply decryption to each row of the log ===
df[['Decrypted_Payload', 'Decryption_Time_ms']] = df.apply(lambda row: pd.Series(decrypt_ascon(row)), axis=1)

# === Function to parse the compacted string format back to its original fields ===
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

        # Parse based on known structure e.g., "I[item]F[fw]H[hw]T[temp]M[mv]D[datetime]"
        if 'F' in compact: result["ITEM"] = try_int(compact.split('F')[0][1:])
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

# === Helper function to safely convert string to integer ===
def try_int(val):
    try:
        return int(val)
    except:
        return None

# === Apply parsing to all decrypted payloads ===
parsed = df['Decrypted_Payload'].apply(parse_compact).apply(pd.Series)

# === Merge parsed data with original dataframe ===
df = pd.concat([df, parsed], axis=1)

# === Save final decrypted and parsed log ===
df.to_csv(output_path, index=False)
print(f"✅ Decrypted log saved to:\n{output_path}")
