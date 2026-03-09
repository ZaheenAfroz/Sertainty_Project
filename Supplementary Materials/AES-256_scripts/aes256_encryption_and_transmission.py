import pandas as pd
import serial
import time
import os
import secrets
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# === Configuration Paths and Parameters ===
excel_file = 'C:/Users/zahee/.../100_test.xlsx'  # Input Excel file with raw data
log_file = 'C:/Users/zahee/.../aes256_transmission_log.csv'  # Output log file to store transmission info
serial_port = 'COM4'  # Serial port for LoRa-E5 communication
baud_rate = 9600  # Baud rate for serial communication
interval = 10  # Wait time (in seconds) between transmissions

# === Generate a fixed 256-bit (32-byte) AES key for this session ===
key = AESGCM.generate_key(bit_length=256)
print("🔐 AES-256 Key (hex):", key.hex())

# === Function: Convert a row of sensor data into compact string format ===
def convert_row_to_compact_string(row_dict):
    try:
        # Parse the timestamp string into datetime format
        date_str = row_dict.get("STATUS DATE", "").strip()
        dt = datetime.strptime(date_str, "%m/%d/%Y %H:%M:%S")
        dval = dt.strftime("%Y%m%d%H%M%S")  # Reformat as compact date string

        # Construct compact string with prefix markers for each field
        return (
            f"I{row_dict.get('ITEM', '')}"
            f"F{row_dict.get('FW VERSION', '')}"
            f"H{row_dict.get('HW VERSIÓN', '')}"
            f"T{row_dict.get('TEMPERATURE', '')}"
            f"M{row_dict.get('MILIVOLTS', '')}"
            f"D{dval}"
        )
    except:
        return None  # Return None if any parsing error occurs

# === Function: Encrypts the compact string using AES-GCM ===
def encrypt_aes(payload):
    nonce = secrets.token_bytes(12)  # Generate a random 12-byte nonce
    aesgcm = AESGCM(key)  # Create AESGCM object with 256-bit key

    # Measure encryption time
    start = time.perf_counter()
    ciphertext = aesgcm.encrypt(nonce, payload.encode(), b"")  # Encrypt without AAD
    end = time.perf_counter()
    encryption_time = round((end - start) * 1000, 4)  # in milliseconds

    encrypted_bytes = nonce + ciphertext  # Combine nonce and ciphertext
    return encrypted_bytes.hex(), encryption_time, nonce.hex(), key.hex()

# === Function: Sends hex payload over serial using AT+CMSGHEX command ===
def send_payload(serial_conn, payload_hex):
    send_time_start = round(time.time(), 5)  # Timestamp before sending
    try:
        serial_conn.write(f'AT+CMSGHEX="{payload_hex}"\r\n'.encode())  # Send payload via AT command
    except Exception as e:
        return [f"Transmission error: {e}"], send_time_start, send_time_start

    # Read LoRa response line-by-line
    response_lines = []
    start_time = time.time()
    while True:
        if time.time() - start_time > 10:  # Timeout after 10 seconds
            response_lines.append("Timeout: No response within 10 seconds")
            break
        line = serial_conn.readline().decode(errors='ignore').strip()
        if line:
            response_lines.append(line)
            if "Done" in line or "RXWIN" in line or "ERROR" in line:
                break
    send_time_end = round(time.time(), 5)  # Timestamp after sending
    return response_lines, send_time_start, send_time_end

# === Function: Logs metadata and encryption/transmission info ===
def log_entry(row_idx, payload_hex, enc_time, nonce, key, send_start, send_end, responses):
    entry = {
        "Row": row_idx,
        "Send_Started": f"{send_start:.5f}",
        "Send_Confirmed": f"{send_end:.5f}",
        "Payload_Hex": payload_hex,
        "Encryption_Time_ms": enc_time,
        "Nonce_Hex": nonce,
        "Key_Hex": key,
        "Response": " | ".join(responses)  # Concatenate multiple response lines
    }
    # Append to CSV (write header only if file does not exist)
    pd.DataFrame([entry]).to_csv(log_file, mode='a', index=False, header=not os.path.exists(log_file))

# === Main Process ===
def main():
    df = pd.read_excel(excel_file, dtype=str)  # Read all rows as strings from Excel

    try:
        with serial.Serial(serial_port, baud_rate, timeout=3) as serial_conn:
            print(f"✅ Connected to {serial_port}")

            # Loop through each row in the dataset
            for index, row in df.iterrows():
                compacted = convert_row_to_compact_string(row.to_dict())
                if not compacted:
                    continue  # Skip if compact conversion failed

                # Encrypt the compacted payload
                encrypted_hex, enc_time, nonce, key_hex = encrypt_aes(compacted)
                print(f"🔐 Encrypted Payload (Row {index}): {encrypted_hex}")

                # Send encrypted payload over LoRa
                responses, send_start, send_end = send_payload(serial_conn, encrypted_hex)
                for r in responses:
                    print(f"📡 Response: {r}")

                # Log the entire transaction to CSV
                log_entry(index, encrypted_hex, enc_time, nonce, key_hex, send_start, send_end, responses)

                # Wait for the next transmission
                print(f"⏱️ Waiting {interval} seconds...\n")
                time.sleep(interval)

    except serial.SerialException as e:
        print(f"❌ Serial connection failed: {e}")

# === Entry Point ===
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Transmission stopped by user.")
