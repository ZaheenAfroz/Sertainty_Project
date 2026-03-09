
import pandas as pd
import json
from datetime import datetime

# === File paths ===
original_data_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/dataset/100_test.xlsx'
xtea_log_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/xtea_transmission_log.csv'
ns_log_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/ns_latency_log.csv'
decrypted_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/xtea_decrypted_output.csv'
output_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/processed_log_xtea.csv'

# === Load logs ===
xtea_log = pd.read_csv(xtea_log_path)
ns_log = pd.read_csv(ns_log_path)
decrypted_log = pd.read_csv(decrypted_path)
original_data = pd.read_excel(original_data_path)

# === Rename NS columns ===
ns_log.rename(columns={'ec2_receive': 'ec2_time', 'ns_publish': 'meta_time'}, inplace=True)

# === Extract fields from NS log ===
def extract_field(raw, *keys):
    try:
        data = json.loads(raw)
        for key in keys:
            data = data.get(key, {})
        return data if not isinstance(data, dict) else None
    except:
        return None

ns_log['rx_time'] = ns_log['raw_json'].apply(lambda x: extract_field(x, 'params', 'rx_time'))
ns_log['device_id'] = ns_log['raw_json'].apply(lambda x: extract_field(x, 'meta', 'device'))
ns_log['payload'] = ns_log['raw_json'].apply(lambda x: extract_field(x, 'params', 'payload'))
ns_log['packet_hash'] = ns_log['raw_json'].apply(lambda x: extract_field(x, 'meta', 'packet_hash'))

# === Drop duplicates based on packet_hash ===
ns_trimmed = ns_log.drop_duplicates(subset='packet_hash', keep='first').reset_index(drop=True)
xtea_trimmed = xtea_log.iloc[:len(ns_trimmed)].reset_index(drop=True)
decrypted_trimmed = decrypted_log.iloc[:len(ns_trimmed)].reset_index(drop=True)
original_trimmed = original_data.iloc[:len(ns_trimmed)].reset_index(drop=True)

# === Reconstruct compacted payload from original values ===
def compact_payload(row):
    try:
        dt = datetime.strptime(row['STATUS DATE'], "%m/%d/%Y %H:%M:%S")
        dval = dt.strftime("%Y%m%d%H%M%S")
        compact = (
            f"I{row['ITEM']}"
            f"F{row['FW VERSION']}"
            f"H{row['HW VERSIÓN']}"
            f"T{row['TEMPERATURE']}"
            f"M{row['MILIVOLTS']}"
            f"D{dval}"
        )
        return compact
    except:
        return None

original_trimmed['reconstructed'] = original_trimmed.apply(compact_payload, axis=1)
decrypted_trimmed['decrypted_payload'] = decrypted_trimmed['Decrypted_Payload'].astype(str).str.strip()

# === Add encryption and decryption fields ===
ns_trimmed['send_time'] = xtea_trimmed['Send_Started'].values
ns_trimmed['encryption_time'] = xtea_trimmed['Encryption_Time_ms'].values
ns_trimmed['decryption_time'] = decrypted_trimmed['Decryption_Time_ms'].values

# === Compare and tag match (Y/N) ===
ns_trimmed['matched'] = (original_trimmed['reconstructed'] == decrypted_trimmed['decrypted_payload']).map({True: 'Y', False: 'N'})

# === Latency calculations in ms ===
ns_trimmed['ed_gateway_latency'] = abs(ns_trimmed['rx_time'] - ns_trimmed['send_time']) * 1000
ns_trimmed['gateway_ns_latency'] = abs(ns_trimmed['meta_time'] - ns_trimmed['rx_time']) * 1000
ns_trimmed['ns_as_latency'] = ns_trimmed['latency_as_ns'] * 1000

# === Final output dataframe ===
final_df = ns_trimmed[[
    'topic', 'device_id', 'payload', 'packet_hash',
    'send_time', 'rx_time', 'meta_time', 'ec2_time',
    'ed_gateway_latency', 'gateway_ns_latency', 'ns_as_latency',
    'encryption_time', 'decryption_time', 'matched'
]]

# === Save output ===
final_df.to_csv(output_path, index=False)
print(f"✅ Final enhanced log saved to:\n{output_path}")
