import pandas as pd
import serial
import time
import os
import secrets
from datetime import datetime
import ascon  # Functional API

# Configuration
excel_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/dataset/100_test.xlsx'
log_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/ascon_transmission_log.csv'
serial_port = 'COM4'
baud_rate = 9600
interval = 10  # seconds
VARIANT = "Ascon-128"

# Use a fixed key during session (16 bytes for Ascon-128)
key = secrets.token_bytes(16)

def convert_row_to_compact_string(row_dict):
    try:
        date_str = row_dict.get("STATUS DATE", "").strip()
        dt = datetime.strptime(date_str, "%m/%d/%Y %H:%M:%S")
        dval = dt.strftime("%Y%m%d%H%M%S")
        compact = (
            f"I{row_dict.get('ITEM', '')}"
            f"F{row_dict.get('FW VERSION', '')}"
            f"H{row_dict.get('HW VERSIÓN', '')}"
            f"T{row_dict.get('TEMPERATURE', '')}"
            f"M{row_dict.get('MILIVOLTS', '')}"
            f"D{dval}"
        )
        return compact
    except Exception as e:
        print(f"Skipping row due to date error: {e}")
        return None

def encrypt_ascon(payload):
    nonce = secrets.token_bytes(16)
    start = time.perf_counter()
    ciphertext = ascon.encrypt(
        key=key,
        nonce=nonce,
        associateddata=b"",
        plaintext=payload.encode(),
        variant=VARIANT
    )
    end = time.perf_counter()
    encryption_time = round((end - start) * 1000, 4)  # ms
    full_bytes = nonce + ciphertext
    return full_bytes.hex(), encryption_time

def send_payload(serial_conn, payload_hex):
    send_time_start = round(time.time(), 5)
    serial_conn.write(f'AT+CMSGHEX="{payload_hex}"\r\n'.encode())
    response_lines = []
    while True:
        line = serial_conn.readline().decode(errors='ignore').strip()
        if line:
            response_lines.append(line)
            if "Done" in line or "RXWIN" in line or "ERROR" in line:
                break
    send_time_end = round(time.time(), 5)
    return response_lines, send_time_start, send_time_end

def log_entry(row_idx, payload_hex, enc_time, send_start, send_end, responses):
    entry = {
        "Row": row_idx,
        "Send_Started": f"{send_start:.5f}",
        "Send_Confirmed": f"{send_end:.5f}",
        "Payload_Hex": payload_hex,
        "Encryption_Time_ms": enc_time,
        "Response": " | ".join(responses)
    }
    pd.DataFrame([entry]).to_csv(log_file, mode='a', index=False, header=not os.path.exists(log_file))

def main():
    df = pd.read_excel(excel_file, dtype=str)
    with serial.Serial(serial_port, baud_rate, timeout=3) as serial_conn:
        print(f"Connected to {serial_port}")
        for index, row in df.iterrows():
            compacted = convert_row_to_compact_string(row.to_dict())
            if not compacted:
                continue
            encrypted_hex, enc_time = encrypt_ascon(compacted)
            print(f"Sending encrypted payload (Row {index}): {encrypted_hex}")
            responses, send_start, send_end = send_payload(serial_conn, encrypted_hex)
            for r in responses:
                print(f"Response: {r}")
            log_entry(index, encrypted_hex, enc_time, send_start, send_end, responses)
            print(f"Waiting {interval} seconds...\n")
            time.sleep(interval)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTransmission stopped by user.")
