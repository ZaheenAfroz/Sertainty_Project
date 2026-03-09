import pandas as pd
import json
from datetime import datetime

# === File paths ===
# Define paths for input and output files
original_data_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/dataset/100_test.xlsx'
speck_log_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/speck_transmission_log.csv'
ns_log_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/ns_latency_log.csv'
decrypted_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/speck_decrypted_output.csv'
output_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/processed_log_speck.csv'

# === Load logs into pandas DataFrames ===
speck_log = pd.read_csv(speck_log_path)               # Contains encryption time, send timestamp, payload, etc.
ns_log = pd.read_csv(ns_log_path)                     # Contains LoRa NS payloads and timestamps
decrypted_log = pd.read_csv(decrypted_path)           # Contains decrypted payloads and decryption time
original_data = pd.read_excel(original_data_path)     # Original unencrypted dataset for payload matching

# === Rename Network Server log columns for consistency ===
ns_log.rename(columns={'ec2_receive': 'ec2_time', 'ns_publish': 'meta_time'}, inplace=True)

# === Extract needed fields from nested JSON string in 'raw_json' column ===
def extract_field(raw, *keys):
    """
    Safely extracts a nested field from a JSON string using a variable key path.
    Returns None if the field is missing or invalid.
    """
    try:
        data = json.loads(raw)
        for key in keys:
            data = data.get(key, {})
        return data if not isinstance(data, dict) else None
    except:
        return None

# Apply field extraction to required fields
ns_log['rx_time'] = ns_log['raw_json'].apply(lambda x: extract_field(x, 'params', 'rx_time'))
ns_log['device_id'] = ns_log['raw_json'].apply(lambda x: extract_field(x, 'meta', 'device'))
ns_log['payload'] = ns_log['raw_json'].apply(lambda x: extract_field(x, 'params', 'payload'))
ns_log['packet_hash'] = ns_log['raw_json'].apply(lambda x: extract_field(x, 'meta', 'packet_hash'))

# === Remove duplicate packets to keep only the first instance of each unique transmission ===
ns_trimmed = ns_log.drop_duplicates(subset='packet_hash', keep='first').reset_index(drop=True)
speck_trimmed = speck_log.iloc[:len(ns_trimmed)].reset_index(drop=True)
decrypted_trimmed = decrypted_log.iloc[:len(ns_trimmed)].reset_index(drop=True)
original_trimmed = original_data.iloc[:len(ns_trimmed)].reset_index(drop=True)

# === Reconstruct the original compacted string from the original Excel dataset for comparison ===
def compact_payload(row):
    """
    Reconstructs the compact encoded payload from original fields.
    Format: I{item}F{fw}H{hw}T{temp}M{mv}D{datetime}
    """
    try:
        dt = datetime.strptime(row['STATUS DATE'], "%m/%d/%Y %H:%M:%S")
        dval = dt.strftime("%Y%m%d%H%M%S")  # Convert date to compact string
        compact = (
            f"I{row['ITEM']}"
            f"F{row['FW VERSION']}"
            f"H{row['HW VERSIÓN']}"  # Note: Check for typo in column name
            f"T{row['TEMPERATURE']}"
            f"M{row['MILIVOLTS']}"
            f"D{dval}"
        )
        return compact
    except:
        return None

# Apply payload reconstruction
original_trimmed['reconstructed'] = original_trimmed.apply(compact_payload, axis=1)

# Clean whitespace from decrypted payload for accurate matching
decrypted_trimmed['decrypted_payload'] = decrypted_trimmed['Decrypted_Payload'].astype(str).str.strip()

# === Merge encryption and decryption times from logs ===
ns_trimmed['send_time'] = speck_trimmed['Send_Started'].values
ns_trimmed['encryption_time'] = speck_trimmed['Encryption_Time_ms'].values
ns_trimmed['decryption_time'] = decrypted_trimmed['Decryption_Time_ms'].values

# === Compare reconstructed vs decrypted payloads to tag correctness ===
ns_trimmed['matched'] = (
    original_trimmed['reconstructed'] == decrypted_trimmed['decrypted_payload']
).map({True: 'Y', False: 'N'})  # 'Y' for match, 'N' for mismatch

# === Calculate end-device to gateway, gateway to NS, and NS to AS latency in milliseconds ===
ns_trimmed['ed_gateway_latency'] = abs(ns_trimmed['rx_time'] - ns_trimmed['send_time']) * 1000
ns_trimmed['gateway_ns_latency'] = abs(ns_trimmed['meta_time'] - ns_trimmed['rx_time']) * 1000
ns_trimmed['ns_as_latency'] = ns_trimmed['latency_as_ns'] * 1000  # Already exists from ns_log

# === Final cleaned and structured output ===
final_df = ns_trimmed[[
    'topic', 'device_id', 'payload', 'packet_hash',
    'send_time', 'rx_time', 'meta_time', 'ec2_time',
    'ed_gateway_latency', 'gateway_ns_latency', 'ns_as_latency',
    'encryption_time', 'decryption_time', 'matched'
]]

# === Save the final DataFrame to CSV ===
final_df.to_csv(output_path, index=False)
print(f"✅ Final enhanced log saved to:\n{output_path}")
