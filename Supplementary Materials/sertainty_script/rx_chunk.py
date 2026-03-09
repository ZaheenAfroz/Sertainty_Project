import os
import json
import pandas as pd
import binascii
import re

# === CONFIG ===
NS_LOG_PATH = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\ns_latency_log.csv"
OUTPUT_FOLDER = r"C:\Users\zahee\OneDrive\Desktop\May_test\Split2"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Extract payload from raw_json
def extract_payload(raw_json_str):
    try:
        data = json.loads(raw_json_str)
        return data.get("params", {}).get("payload", None)
    except Exception as e:
        print(f"⚠️ JSON parse error: {e}")
        return None

# === Sanitize file name
def sanitize_filename(filename):
    filename = filename.strip().replace('\x00', '')
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    return filename

# === Reconstruct .chunk file from payload
def reconstruct_chunk(payload_hex):
    try:
        if '7c' not in payload_hex:
            return False, "Invalid payload: delimiter '7c' not found"
        
        filename_hex, data_hex = payload_hex.split('7c', 1)

        # Decode filename
        try:
            filename_bytes = binascii.unhexlify(filename_hex)
            filename = filename_bytes.decode(errors='replace').strip()
            filename = sanitize_filename(filename)
        except Exception as e:
            return False, f"Filename decoding failed: {e}"

        # Decode file content
        try:
            filedata = binascii.unhexlify(data_hex)
        except Exception as e:
            return False, f"Data decoding failed: {e}"

        # Save to disk
        full_path = os.path.join(OUTPUT_FOLDER, filename)
        with open(full_path, 'wb') as f:
            f.write(filedata)
        return True, filename

    except Exception as e:
        return False, f"Unhandled error: {e}"

# === Main function
def main():
    df = pd.read_csv(NS_LOG_PATH)

    # Extract payload from each raw_json row
    df['payload'] = df['raw_json'].apply(extract_payload)

    success_count = 0
    for i, row in df.iterrows():
        payload = row['payload']
        if isinstance(payload, str):
            success, result = reconstruct_chunk(payload)
            if success:
                print(f"✅ Row {i}: Reconstructed file {result}")
                success_count += 1
            else:
                print(f"❌ Row {i}: {result}")
        else:
            print(f"⚠️ No payload found in row {i}")

    print(f"\n🎯 Total successfully reconstructed chunks: {success_count}")

if __name__ == "__main__":
    main()
