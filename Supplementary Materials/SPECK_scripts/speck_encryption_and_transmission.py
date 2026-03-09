import pandas as pd
import serial
import time
import os
import secrets
from datetime import datetime
from speck import encrypt as speck_encrypt  # Importing the encryption function from custom SPECK module

# ----------------------- Configuration -----------------------
excel_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/dataset/100_test.xlsx'
log_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/speck_transmission_log.csv'
serial_port = 'COM4'            # Change to your actual LoRa serial port
baud_rate = 9600                # Baud rate for serial communication
interval = 8                    # Delay between transmissions (in seconds)

# Generate a random 24-byte key for SPECK (used as 128-bit key internally)
key = secrets.token_bytes(24)
print("🔐 SPECK Key (hex):", key.hex())

# ------------------ Convert Excel Row to String ------------------
def convert_row_to_compact_string(row_dict):
    """
    Convert a row of Excel data into a compact string format.
    Returns a structured string like: I{item}F{fw}H{hw}T{temp}M{mv}D{datetime}
    """
    try:
        date_str = row_dict.get("STATUS DATE", "").strip()
        dt = datetime.strptime(date_str, "%m/%d/%Y %H:%M:%S")
        dval = dt.strftime("%Y%m%d%H%M%S")  # Convert datetime to compact format
        return (
            f"I{row_dict.get('ITEM', '')}"
            f"F{row_dict.get('FW VERSION', '')}"
            f"H{row_dict.get('HW VERSIÓN', '')}"
            f"T{row_dict.get('TEMPERATURE', '')}"
            f"M{row_dict.get('MILIVOLTS', '')}"
            f"D{dval}"
        )
    except:
        return None  # If any parsing fails, return None

# ---------------------- Encryption Function ----------------------
def encrypt_speck(payload):
    """
    Encrypt the payload using the SPECK cipher.
    Returns the hex-encoded ciphertext, encryption time (ms), and key used.
    """
    start = time.perf_counter()
    ciphertext = speck_encrypt(payload.encode(), key)
    end = time.perf_counter()
    encryption_time = round((end - start) * 1000, 4)  # Time in milliseconds
    return ciphertext.hex(), encryption_time, key.hex()

# --------------------- Transmission Function ---------------------
def send_payload(serial_conn, payload_hex):
    """
    Sends the encrypted payload as hex over the serial connection.
    Waits for confirmation or error response.
    """
    send_time_start = round(time.time(), 5)
    try:
        # Send the payload using AT command for LoRa module
        serial_conn.write(f'AT+CMSGHEX="{payload_hex}"\r\n'.encode())
    except Exception as e:
        return [f"Transmission error: {e}"], send_time_start, send_time_start

    # Read response lines from the serial port
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

# ----------------------- Logging Function ------------------------
def log_entry(row_idx, payload_hex, enc_time, key, send_start, send_end, responses):
    """
    Logs the transmission details into a CSV file.
    Includes timing, payload, key, and gateway responses.
    """
    entry = {
        "Row": row_idx,
        "Send_Started": f"{send_start:.5f}",
        "Send_Confirmed": f"{send_end:.5f}",
        "Payload_Hex": payload_hex,
        "Encryption_Time_ms": enc_time,
        "Key_Hex": key,
        "Response": " | ".join(responses)
    }
    pd.DataFrame([entry]).to_csv(log_file, mode='a', index=False, header=not os.path.exists(log_file))

# ---------------------------- Main ------------------------------
def main():
    df = pd.read_excel(excel_file, dtype=str)
    try:
        with serial.Serial(serial_port, baud_rate, timeout=3) as serial_conn:
            print(f"✅ Connected to {serial_port}")
            for index, row in df.iterrows():
                compacted = convert_row_to_compact_string(row.to_dict())
                if not compacted:
                    continue  # Skip if formatting failed
                encrypted_hex, enc_time, key_hex = encrypt_speck(compacted)
                print(f"🔐 Encrypted Payload (Row {index}): {encrypted_hex}")
                responses, send_start, send_end = send_payload(serial_conn, encrypted_hex)
                for r in responses:
                    print(f"📡 Response: {r}")
                log_entry(index, encrypted_hex, enc_time, key_hex, send_start, send_end, responses)
                print(f"⏱️ Waiting {interval} seconds...\n")
                time.sleep(interval)
    except serial.SerialException as e:
        print(f"❌ Serial connection failed: {e}")

# ------------------------- Script Start -------------------------
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Transmission stopped by user.")
