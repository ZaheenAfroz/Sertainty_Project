
import pandas as pd
import serial
import time
import os
import secrets
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

# Configuration
excel_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/dataset/micro_data.xlsx'
log_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/chacha20_transmission_log.csv'
serial_port = 'COM4'
baud_rate = 9600
interval = 8

# Fixed 32-byte key for ChaCha20
key = ChaCha20Poly1305.generate_key()
print("🔐 ChaCha20 Key (hex):", key.hex())

def convert_row_to_compact_string(row_dict):
    try:
        date_str = row_dict.get("STATUS DATE", "").strip()
        dt = datetime.strptime(date_str, "%m/%d/%Y %H:%M:%S")
        dval = dt.strftime("%Y%m%d%H%M%S")
        return (
            f"I{row_dict.get('ITEM', '')}"
            f"F{row_dict.get('FW VERSION', '')}"
            f"H{row_dict.get('HW VERSIÓN', '')}"
            f"T{row_dict.get('TEMPERATURE', '')}"
            f"M{row_dict.get('MILIVOLTS', '')}"
            f"D{dval}"
        )
    except:
        return None

def encrypt_chacha20(payload):
    nonce = secrets.token_bytes(12)  # 12-byte nonce for ChaCha20-Poly1305
    chacha = ChaCha20Poly1305(key)
    start = time.perf_counter()
    ciphertext = chacha.encrypt(nonce, payload.encode(), b"")
    end = time.perf_counter()
    encryption_time = round((end - start) * 1000, 4)
    encrypted_bytes = nonce + ciphertext
    return encrypted_bytes.hex(), encryption_time, nonce.hex(), key.hex()

def send_payload(serial_conn, payload_hex):
    send_time_start = round(time.time(), 5)
    try:
        serial_conn.write(f'AT+CMSGHEX="{payload_hex}"\r\n'.encode())
    except Exception as e:
        return [f"Transmission error: {e}"], send_time_start, send_time_start

    response_lines = []
    start_time = time.time()
    while True:
        if time.time() - start_time > 10:
            response_lines.append("Timeout: No response within 10 seconds")
            break
        line = serial_conn.readline().decode(errors='ignore').strip()
        if line:
            response_lines.append(line)
            if "Done" in line or "RXWIN" in line or "ERROR" in line:
                break
    send_time_end = round(time.time(), 5)
    return response_lines, send_time_start, send_time_end

def log_entry(row_idx, payload_hex, enc_time, nonce, key, send_start, send_end, responses):
    entry = {
        "Row": row_idx,
        "Send_Started": f"{send_start:.5f}",
        "Send_Confirmed": f"{send_end:.5f}",
        "Payload_Hex": payload_hex,
        "Encryption_Time_ms": enc_time,
        "Nonce_Hex": nonce,
        "Key_Hex": key,
        "Response": " | ".join(responses)
    }
    pd.DataFrame([entry]).to_csv(log_file, mode='a', index=False, header=not os.path.exists(log_file))

def main():
    df = pd.read_excel(excel_file, dtype=str)
    try:
        with serial.Serial(serial_port, baud_rate, timeout=3) as serial_conn:
            print(f"✅ Connected to {serial_port}")
            for index, row in df.iterrows():
                compacted = convert_row_to_compact_string(row.to_dict())
                if not compacted:
                    continue
                encrypted_hex, enc_time, nonce, key_hex = encrypt_chacha20(compacted)
                print(f"🔐 Encrypted Payload (Row {index}): {encrypted_hex}")
                responses, send_start, send_end = send_payload(serial_conn, encrypted_hex)
                for r in responses:
                    print(f"📡 Response: {r}")
                log_entry(index, encrypted_hex, enc_time, nonce, key_hex, send_start, send_end, responses)
                print(f"⏱️ Waiting {interval} seconds...\n")
                time.sleep(interval)
    except serial.SerialException as e:
        print(f"❌ Serial connection failed: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Transmission stopped by user.")
