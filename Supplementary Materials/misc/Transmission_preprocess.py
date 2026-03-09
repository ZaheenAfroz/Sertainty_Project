import pandas as pd
import serial
import time
import os
from datetime import datetime

def convert_row_to_compact_string(row_dict):
    try:
        # Parse date as YYYYMMDDHHMMSS for D field
        date_str = row_dict.get("STATUS DATE", "07/17/2024 12:53:55").strip()
        try:
            dt = datetime.strptime(date_str, "%m/%d/%Y %H:%M:%S")
            dval = dt.strftime("%Y%m%d%H%M%S")
        except Exception:
            dval = "20240101000000"  # fallback default

        # Create compact string
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
        print(f"Conversion error: {e}")
        return None

def send_payload(serial_conn, payload_chunk):
    serial_conn.write(f'AT+MSG="{payload_chunk}"\r\n'.encode())
    time.sleep(2)
    response_lines = []
    while serial_conn.in_waiting:
        line = serial_conn.readline().decode(errors='ignore').strip() 
        response_lines.append(line)
    return response_lines

def log_chunk(row_idx, chunk_idx, chunk_payload, response_lines, log_path, send_time):
    log_entry = {
        "Row": row_idx,
        "Chunk": chunk_idx,
        "Send_Unix_Time": f"{send_time:.5f}",  # Timestamp when payload is sent
        "Payload": chunk_payload,
        "Response": " | ".join(response_lines)
    }
    pd.DataFrame([log_entry]).to_csv(log_path, mode='a', index=False, header=not os.path.exists(log_path))

def main():
    excel_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/dataset/micro_data.xlsx'
    #excel_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/dataset/ami_activity_07_17_2024_12_56_38.xlsx'
    log_file = 'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/transmission_log_t1.csv'
    serial_port = 'COM4'
    baud_rate = 9600
    interval = 1.5  # seconds between chunks      

    df = pd.read_excel(excel_file, dtype=str)
    all_chunks = []

    # Prepare all payloads as compact strings per row
    for index, row in df.iterrows():
        payload = convert_row_to_compact_string(row.to_dict())
        if not payload:
            continue
        # For small payloads, chunking is likely unnecessary, but you can split if needed
        chunk_size = 51
        chunks = [payload[i:i+chunk_size] for i in range(0, len(payload), chunk_size)]
        for chunk_idx, chunk in enumerate(chunks):
            all_chunks.append((index, f"C{chunk_idx+1}", chunk))
        # No EOR marker appended!

    # Transmit each chunk and log send time
    with serial.Serial(serial_port, baud_rate, timeout=3) as serial_conn:
        print(f"Connected to {serial_port}. Sending {len(all_chunks)} chunks...\n")
        for row_idx, chunk_idx, chunk in all_chunks:
            send_time = round(time.time(), 5)  # Timestamp with 3 decimal precision
            print(f"Sending (Row {row_idx}, {chunk_idx}): {chunk}")
            responses = send_payload(serial_conn, chunk)
            for r in responses:
                print(f"Response: {r}")
            log_chunk(row_idx, chunk_idx, chunk, responses, log_file, send_time)
            print(f"Waiting {interval} seconds...\n")
            time.sleep(interval)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTransmission stopped by user.")

