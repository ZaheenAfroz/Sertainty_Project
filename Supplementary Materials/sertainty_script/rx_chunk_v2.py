import os
import json
import pandas as pd
import binascii
import re

# === CONFIG ===
NS_LOG_PATH = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\ns_latency_log.csv"
OUTPUT_CLEANED_CSV = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\ns_latency_cleaned_payload.csv"
OUTPUT_FOLDER = r"C:\Users\zahee\OneDrive\Desktop\May_test\Split2"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Extract payload and packet_hash ===
def extract_from_json(raw):
    try:
        parsed = json.loads(raw)
        payload = parsed.get("params", {}).get("payload", None)
        packet_hash = parsed.get("meta", {}).get("packet_hash", None)
        return pd.Series([payload, packet_hash])
    except:
        return pd.Series([None, None])

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

        # Decode data
        try:
            filedata = binascii.unhexlify(data_hex)
        except Exception as e:
            return False, f"Data decoding failed: {e}"

        # Write to file
        out_path = os.path.join(OUTPUT_FOLDER, filename)
        with open(out_path, 'wb') as f:
            f.write(filedata)
        return True, filename

    except Exception as e:
        return False, f"Unhandled error: {e}"

# === Main pipeline
def main():
    print("📥 Loading and cleaning NS latency log...")
    df = pd.read_csv(NS_LOG_PATH)

    df[['payload', 'packet_hash']] = df['raw_json'].apply(extract_from_json)
    df = df[df['packet_hash'].notna()]
    df = df.drop_duplicates(subset='packet_hash', keep='first').reset_index(drop=True)

    df.to_csv(OUTPUT_CLEANED_CSV, index=False)
    print(f"✅ Cleaned log saved to: {OUTPUT_CLEANED_CSV}")
    print(f"📦 Unique payloads to reconstruct: {len(df)}")

    # Reconstruct chunks
    success_count = 0
    for i, row in df.iterrows():
        payload = row['payload']
        if isinstance(payload, str):
            success, result = reconstruct_chunk(payload)
            if success:
                print(f"✅ Row {i}: Reconstructed {result}")
                success_count += 1
            else:
                print(f"❌ Row {i}: {result}")
        else:
            print(f"⚠️ No payload in row {i}")

    print(f"\n🎯 Total successfully reconstructed chunks: {success_count}")

if __name__ == "__main__":
    main()
