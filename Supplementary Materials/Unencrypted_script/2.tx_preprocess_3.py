#import necessary libraries
import pandas as pd
import serial
import time
import os
import base64
from datetime import datetime

def convert_row_to_compact_string(row_dict):
    """
    Converts a single row from the Excel sheet into a compact formatted string.
    This function extracts selected fields and constructs a string using key prefixes.

    Format:
        I[item]F[fw_version]H[hw_version]T[temperature]M[millivolts]D[datetime]

    Parameters:
        row_dict (dict): Dictionary representing a row of the DataFrame.

    Returns:
        str or None: A compact string ready for transmission, or None if date parsing fails.
    """
    try:
        # Parse date from the "STATUS DATE" field and convert it to YYYYMMDDHHMMSS
        date_str = row_dict.get("STATUS DATE", "").strip()
        dt = datetime.strptime(date_str, "%m/%d/%Y %H:%M:%S")
        dval = dt.strftime("%Y%m%d%H%M%S")

        # Construct compact string using fixed field order and markers
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

def send_payload(serial_conn, payload):
    """
    Sends a Base64-encoded payload over LoRaWAN using AT+CMSG and listens for confirmation.

    Parameters:
        serial_conn (serial.Serial): Open serial connection to LoRa-E5
        payload (str): Encoded Base64 string to send

    Returns:
        tuple:
            - response_lines (list): List of response lines from the LoRa-E5
            - send_time_start (float): Timestamp before sending
            - send_time_end (float): Timestamp after receiving confirmation
    """
    send_time_start = round(time.time(), 5)
    serial_conn.write(f'AT+CMSG="{payload}"\r\n'.encode())

    response_lines = []
    while True:
        # Read one line at a time and strip unwanted characters
        line = serial_conn.readline().decode(errors='ignore').strip()
        if line:
            response_lines.append(line)
            # Exit loop if confirmation or error is received
            if "Done" in line or "RXWIN" in line or "ERROR" in line:
                break

    send_time_end = round(time.time(), 5)
    return response_lines, send_time_start, send_time_end

def log_chunk(row_idx, chunk_idx, chunk_payload, response_lines, log_path, send_start, send_end):
    """
    Logs the transmission details of a payload chunk to a CSV file.

    Parameters:
        row_idx (int): Original row index in the Excel file
        chunk_idx (str): Chunk identifier (e.g., C1, C2, ...)
        chunk_payload (str): Base64 encoded payload string
        response_lines (list): Response lines from the LoRa-E5
        log_path (str): Path to the CSV log file
        send_start (float): Timestamp before sending
        send_end (float): Timestamp after confirmation
    """
    log_entry = {
        "Row": row_idx,
        "Chunk": chunk_idx,
        "Send_Started": f"{send_start:.5f}",
        "Send_Confirmed": f"{send_end:.5f}",
        "payload": chunk_payload,
        "Response": " | ".join(response_lines)
    }
    # Append the log entry to the file (write headers only if file doesn't exist)
    pd.DataFrame([log_entry]).to_csv(log_path, mode='a', index=False, header=not os.path.exists(log_path))

def main():
    """
    Main function that loads data from an Excel file, converts each row into
    formatted chunks, and sends them over LoRaWAN using a serial connection.
    Each transmission is logged for future reference.
    """
    # File paths and serial config
    excel_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/dataset/100_test.xlsx'
    log_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/transmission_log_t1.csv'
    serial_port = 'COM4'
    baud_rate = 9600
    interval = 5  # Seconds between chunk transmissions

    # Load the Excel file as DataFrame (force all values to strings)
    df = pd.read_excel(excel_file, dtype=str)
    all_chunks = []

    # Iterate through each row to build payload chunks
    for index, row in df.iterrows():   #one row at a time
        payload = convert_row_to_compact_string(row.to_dict())
        if not payload:
            continue  # Skip malformed rows

        # Break long payloads into 51-character chunks
        chunk_size = 51
        chunks = [payload[i:i+chunk_size] for i in range(0, len(payload), chunk_size)]

        for chunk_idx, chunk in enumerate(chunks):
            # Encode each chunk to Base64 to ensure safe transmission
            encoded_payload = base64.b64encode(chunk.encode()).decode()
            all_chunks.append((index, f"C{chunk_idx+1}", encoded_payload))

    # Open serial port and transmit all payloads
    with serial.Serial(serial_port, baud_rate, timeout=3) as serial_conn:
        print(f"Connected to {serial_port}. Sending {len(all_chunks)} payloads...\n")

        for row_idx, chunk_idx, chunk in all_chunks:
            print(f"Sending (Row {row_idx}, {chunk_idx}): {chunk}")
            responses, send_start, send_end = send_payload(serial_conn, chunk)   #Sending base64-encoded chunk
            for r in responses:
                print(f"Response: {r}")
            log_chunk(row_idx, chunk_idx, chunk, responses, log_file, send_start, send_end)
            print(f"Waiting {interval} seconds...\n")
            time.sleep(interval)  # Delay to comply with LoRa duty cycle

# Run main function safely, support Ctrl+C exit
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTransmission stopped by user.")
