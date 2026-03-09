import os
import json
import pandas as pd
import binascii
import base64
import re

# === CONFIGURATION SECTION ===

# Path to the raw NS (Network Server) latency log CSV that contains JSON strings
NS_LOG_PATH = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\ns_latency_log.csv"

# Output path where the cleaned DataFrame with extracted payloads and packet_hash will be saved
CLEANED_LOG_OUTPUT = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\ns_latency_cleaned_uxp.csv"

# Folder where the decoded `.chunk` files will be reconstructed and saved
OUTPUT_FOLDER = r"C:\Users\zahee\OneDrive\Desktop\May_test\Split3"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

# === STEP 1: Function to Extract Payload and Packet Hash from raw JSON column ===

def extract_from_json(raw):
    """
    Parses a JSON-formatted string and extracts the 'payload' and 'packet_hash'.
    Returns a Series with [payload, packet_hash].

    Args:
        raw (str): A JSON-formatted string.

    Returns:
        pd.Series: Contains extracted payload and packet_hash.
    """
    try:
        obj = json.loads(raw)
        payload = obj.get("params", {}).get("payload", None)
        packet_hash = obj.get("meta", {}).get("packet_hash", None)
        return pd.Series([payload, packet_hash])
    except:
        return pd.Series([None, None])  # Return None if parsing fails

# === STEP 2: Clean the filename to remove invalid characters ===

def sanitize_filename(name):
    """
    Removes or replaces characters that are invalid in Windows filenames.

    Args:
        name (str): Raw filename string.

    Returns:
        str: Sanitized filename.
    """
    name = name.strip().replace('\x00', '')  # Remove null byte
    return re.sub(r'[<>:"/\\|?*]', '', name)  # Replace invalid characters

# === STEP 3: Decode Base64 payload and reconstruct chunk files ===

def reconstruct_chunk_from_base64(payload_b64):
    """
    Decodes a base64-encoded payload and reconstructs the original chunk file.
    The payload must contain a filename and binary data separated by '|'.

    Args:
        payload_b64 (str): Base64-encoded payload string.

    Returns:
        Tuple[bool, str]: (True, filename) if successful, otherwise (False, error message)
    """
    try:
        # Decode base64 into raw bytes
        raw_bytes = base64.b64decode(payload_b64)

        # Validate presence of '|' delimiter (ASCII 124)
        if b'|' not in raw_bytes:
            return False, "Missing '|' delimiter in decoded payload"

        # Split into filename and binary data
        filename_bytes, binary_data = raw_bytes.split(b'|', 1)
        filename = filename_bytes.decode(errors='replace').strip()
        filename = sanitize_filename(filename)

        # Write binary data to file
        path = os.path.join(OUTPUT_FOLDER, filename)
        with open(path, 'wb') as f:
            f.write(binary_data)

        return True, filename

    except Exception as e:
        return False, f"Error decoding payload: {e}"

# === STEP 4: Main Pipeline Execution ===

def main():
    """
    Main pipeline for:
    - Reading raw JSON logs,
    - Extracting payloads and packet hashes,
    - Saving a cleaned CSV log,
    - Reconstructing .chunk files from base64 payloads.
    """
    print("📥 Reading NS latency log...")
    df = pd.read_csv(NS_LOG_PATH)  # Load raw CSV

    # Apply extraction to each row
    df[['payload', 'packet_hash']] = df['raw_json'].apply(extract_from_json)

    # Drop rows where packet_hash is missing
    df = df[df['packet_hash'].notna()]

    # Keep only the first occurrence of each unique packet_hash
    df = df.drop_duplicates(subset='packet_hash', keep='first').reset_index(drop=True)

    # Save cleaned log
    df.to_csv(CLEANED_LOG_OUTPUT, index=False)
    print(f"✅ Cleaned log saved to: {CLEANED_LOG_OUTPUT}")
    print(f"📦 Total unique payloads: {len(df)}")

    # Begin reconstruction of .chunk files from base64 payloads
    reconstructed = 0
    for i, row in df.iterrows():
        payload = row['payload']
        if isinstance(payload, str):
            success, result = reconstruct_chunk_from_base64(payload)
            if success:
                print(f"✅ Row {i}: Reconstructed {result}")
                reconstructed += 1
            else:
                print(f"❌ Row {i}: {result}")  # Show error message
        else:
            print(f"⚠️ Row {i}: Invalid payload")  # Payload was not a valid string

    print(f"\n🎯 Total reconstructed .chunk files: {reconstructed}")

# === ENTRY POINT ===

if __name__ == "__main__":
    main()
