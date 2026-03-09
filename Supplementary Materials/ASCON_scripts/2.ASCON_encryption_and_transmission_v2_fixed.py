import pandas as pd
import serial
import time
import os
import secrets
from datetime import datetime
from ascon import encrypt  # ASCON encryption library

# === Configuration ===
excel_file = '.../100_test.xlsx'  # Path to Excel data
log_file = '.../ascon_transmission_log.csv'  # Path to save transmission log
serial_port = 'COM4'  # Serial port to which the LoRa device is connected
baud_rate = 9600  # Communication baud rate
interval = 8  # Time delay between transmissions in seconds
VARIANT = "Ascon-128"  # ASCON variant to use for encryption

# === Generate and display a random 128-bit key for ASCON encryption ===
key = secrets.token_bytes(16)  # 16 bytes = 128 bits
print("🔐 ASCON Key (hex):", key.hex())

# === Function to convert a data row into a compact encoded string ===
def convert_row_to_compact_string(row_dict):
    try:
        date_str = row_dict.get("STATUS DATE", "").strip()
        dt = datetime.strptime(date_str, "%m/%d/%Y %H:%M:%S")
        dval = dt.strftime("%Y%m%d%H%M%S")  # Format date as compact string
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

# === Function to encrypt a payload using ASCON ===
def encrypt_ascon(payload):
    nonce = secrets.token_bytes(16)  # Generate 128-bit nonce
    start = time.perf_counter()
    ciphertext = encrypt(
        key=key,
        nonce=nonce,
        associateddata=b"",  # No associated data used
        plaintext=payload.encode(),
        variant=VARIANT
    )
    end = time.perf_counter()
    encryption_time = round((end - start) * 1000, 4)  # in milliseconds
    encrypted_bytes = nonce + ciphertext  # Prepend nonce for later decryption
    return encrypted_bytes.hex(), encryption_time, nonce.hex(), key.hex()

# === Function to send encrypted hex payload over LoRa via serial AT command ===
def send_payload(serial_conn, payload_hex):
    send_time_start = round(time.time(), 5)
    try:
        serial_conn.write(f'AT+CMSGHEX="{payload_hex}"\r\n'.encode())
    except Exception as e:
        return [f"Transmission error: {e}"], send_time_start, send_time_start

    # Read response from serial until timeout or success message
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

# === Function to log one transmission entry to CSV ===
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

# === Main execution logic ===
def main():
    df = pd.read_excel(excel_file, dtype=str)  # Load input Excel file
    try:
        # Open serial connection to LoRa device
        with serial.Serial(serial_port, baud_rate, timeout=3) as serial_conn:
            print(f"✅ Connected to {serial_port}")
            for index, row in df.iterrows():
                # Prepare payload string
                compacted = convert_row_to_compact_string(row.to_dict())
                if not compacted:
                    continue
                # Encrypt using ASCON
                encrypted_hex, enc_time, nonce, key_hex = encrypt_ascon(compacted)
                print(f"🔐 Encrypted Payload (Row {index}): {encrypted_hex}")
                # Send encrypted payload via serial
                responses, send_start, send_end = send_payload(serial_conn, encrypted_hex)
                for r in responses:
                    print(f"📡 Response: {r}")
                # Log transmission details
                log_entry(index, encrypted_hex, enc_time, nonce, key_hex, send_start, send_end, responses)
                print(f"⏱️ Waiting {interval} seconds...\n")
                time.sleep(interval)
    except serial.SerialException as e:
        print(f"❌ Serial connection failed: {e}")

# === Run the main function ===
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Transmission stopped by user.")
