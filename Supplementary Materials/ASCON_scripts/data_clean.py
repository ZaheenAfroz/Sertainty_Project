# Construct the full enhanced data processing script

import pandas as pd
import json

# === File paths ===
original_data_path= r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/dataset/micro_data.xlsx'
ascon_log_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/ascon_transmission_log.csv'
ns_log_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/ns_latency_log.csv'
decrypted_path=r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/ascon_decrypted_output.xlsx'
output_path = r'C:/Users/zahee/OneDrive - Texas State University/Documents/Sertainty project/code_2025/scripts/processed_log_with_encryption_decryption.csv'

# === Load logs ===
ascon_log = pd.read_csv(ascon_log_path)
ns_log = pd.read_csv(ns_log_path)

# === Rename NS columns ===
ns_log.rename(columns={'ec2_receive': 'ec2_time', 'ns_publish': 'meta_time'}, inplace=True)

# === Trim lengths to match ===
min_len = min(len(ascon_log), len(ns_log))
ascon_trimmed = ascon_log.iloc[:min_len].copy().reset_index(drop=True)
ns_trimmed = ns_log.iloc[:min_len].copy().reset_index(drop=True)

# === Extract rx_time and device_id from raw_json ===
def extract_field(raw, *keys):
    try:
        data = json.loads(raw)
        for key in keys:
            data = data.get(key, {})
        return data if not isinstance(data, dict) else None
    except:
        return None

ns_trimmed['rx_time'] = ns_trimmed['raw_json'].apply(lambda x: extract_field(x, 'params', 'rx_time'))
ns_trimmed['device_id'] = ns_trimmed['raw_json'].apply(lambda x: extract_field(x, 'meta', 'device'))

# === Add encryption fields ===
ns_trimmed['send_time'] = ascon_trimmed['Send_Started'].values
ns_trimmed['encryption_time'] = ascon_trimmed['Encryption_Time_ms'].values

# === Latency calculations (all in ms) ===
ns_trimmed['ed_gateway_latency'] = abs(ns_trimmed['rx_time'] - ns_trimmed['send_time']) * 1000
ns_trimmed['gateway_ns_latency'] = abs(ns_trimmed['meta_time'] - ns_trimmed['rx_time']) * 1000
ns_trimmed['ns_as_latency'] = ns_trimmed['latency_as_ns'] * 1000  # convert from sec to ms

# === Final column selection and order ===
final_df = ns_trimmed[[
    'topic', 'device_id', 'payload', 'packet_hash', 'send_time',
    'rx_time', 'meta_time', 'ec2_time',
    'ed_gateway_latency', 'gateway_ns_latency', 'ns_as_latency', 'encryption_time'
]]

# === Save output ===
final_df.to_csv(output_path, index=False)
print(f"✅ Final enhanced transmission log saved to:\\n{output_path}")

