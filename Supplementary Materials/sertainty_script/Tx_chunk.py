import os
import serial
import time
import binascii
import pandas as pd
from datetime import datetime

# === CONFIGURATION ===
# Folder containing the .chunk files to transmit
SPLITTED_FOLDER = r"C:\Users\zahee\OneDrive\Desktop\May_test\Split"

# Serial communication settings for the LoRa-E5 device
SERIAL_PORT = 'COM4'
BAUD_RATE = 9600

# Path to CSV file where transmission logs will be stored
LOG_FILE = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\June scripts\sertainty_script\chunk_transmission_log.csv"

# File extension used for identifying chunked payloads
CHUNK_EXTENSION = '.chunk'

# Time (in seconds) to wait between sending two chunk files
WAIT_INTERVAL = 15

# === HELPER FUNCTION: Send hex payload over serial port ===
def send_payload(serial_conn, payload_hex):
    """
    Sends a hex-encoded payload over the serial connection using AT+CMSGHEX command.

    Args:
        serial_conn (serial.Serial): Open serial connection.
        payload_hex (str): Hex-encoded payload string.

    Returns:
        Tuple: (list of response lines from the device, send start time, send end time)
    """
    send_start = round(time.time(), 5)  # Capture the transmission start time
    command = f'AT+CMSGHEX="{payload_hex}"\r\n'.encode()  # Format AT command
    serial_conn.write(command)  # Send the command

    response_lines = []
    while True:
        # Read device response line-by-line
        line = serial_conn.readline().decode(errors='ignore').strip()
        if line:
            response_lines.append(line)
            # Stop reading once transmission is complete or error occurs
            if "Done" in line or "RXWIN" in line or "ERROR" in line:
                break

    send_end = round(time.time(), 5)  # Capture end time
    return response_lines, send_start, send_end

# === HELPER FUNCTION: Log each transmission ===
def log_transmission(full_path, payload_hex, response_lines, send_start, send_end):
    """
    Logs the transmission details into a CSV file.

    Args:
        full_path (str): Full file path of the transmitted chunk.
        payload_hex (str): Hex-encoded payload sent.
        response_lines (list): Response messages received from the device.
        send_start (float): Timestamp when sending started.
        send_end (float): Timestamp when sending ended.
    """
    file_name = os.path.basename(full_path)  # Extract filename only

    log_entry = {
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "File": file_name,
        "Send_Start": send_start,
        "Send_End": send_end,
        "Payload_Hex": payload_hex,
        "Response": " | ".join(response_lines)  # Concatenate response lines
    }

    df = pd.DataFrame([log_entry])
    # Append to log file (create header only if file doesn't exist)
    df.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))

# === MAIN FUNCTION ===
def main():
    """
    Main logic for transmitting all .chunk files in the specified folder over LoRaWAN.
    """
    # Get all files ending in .chunk (excluding .meta files)
    chunk_files = [f for f in os.listdir(SPLITTED_FOLDER)
                   if f.endswith(CHUNK_EXTENSION) and not f.endswith('.meta')]
    chunk_files.sort()  # Ensure consistent order

    if not chunk_files:
        print("No .chunk files found.")
        return

    print(f"Found {len(chunk_files)} .chunk files to transmit.\n")

    # Open serial connection to LoRa-E5 board
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=3) as conn:
        for file_name in chunk_files:
            full_path = os.path.join(SPLITTED_FOLDER, file_name)

            try:
                # Read binary content of the chunk file
                with open(full_path, 'rb') as f:
                    binary_data = f.read()

                # Convert filename to hex
                filename_bytes = file_name.encode()
                filename_hex = binascii.hexlify(filename_bytes).decode()

                # Use '|' (ASCII 124 = 0x7C) as delimiter between filename and data
                delimiter_hex = '7c'

                # Convert binary content to hex string
                content_hex = binascii.hexlify(binary_data).decode()

                # Final payload = filename_hex + delimiter + content_hex
                payload_hex = filename_hex + delimiter_hex + content_hex

                print(f"Sending {file_name} ({len(payload_hex)} hex chars)...")
                responses, t_start, t_end = send_payload(conn, payload_hex)

                # Display each response line
                for r in responses:
                    print(f"  ↪ {r}")

                # Log the transmission
                log_transmission(full_path, payload_hex, responses, t_start, t_end)

                # Wait before next transmission
                print(f"Waiting {WAIT_INTERVAL} seconds...\n")
                time.sleep(WAIT_INTERVAL)

            except Exception as e:
                print(f"Error reading or sending {file_name}: {e}")

# === ENTRY POINT ===
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Transmission manually interrupted.")
