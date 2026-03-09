import pandas as pd
import json

# ---------------------------------------------
# File paths for input logs and output CSV
# ---------------------------------------------
ns_log_path = r'C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\ns_latency_log.csv'
tx_log_path = r'C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\transmission_log_t1.csv'
output_path = r'C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\ns_latency_log_cleaned.csv'

# ---------------------------------------------
# Load the two CSV log files:
# - df_ns: LoRaWAN network server log with raw JSON
# - df_tx: Local transmission log with send timestamps
# ---------------------------------------------
df_ns = pd.read_csv(ns_log_path)
df_tx = pd.read_csv(tx_log_path)

# ---------------------------------------------
# Rename JSON timestamp columns in network server log
# - ec2_receive → ec2_time: When EC2 received the message
# - ns_publish → meta_time: When NS published the message to the cloud
# ---------------------------------------------
df_ns.rename(columns={"ec2_receive": "ec2_time", "ns_publish": "meta_time"}, inplace=True)

# ---------------------------------------------
# Parse the raw_json column and filter only 'uplink' messages
# - raw_json contains nested fields such as rx_time, device ID, packet hash, etc.
# ---------------------------------------------
parsed_json = df_ns['raw_json'].dropna().apply(json.loads)
uplink_mask = parsed_json.apply(lambda p: p.get('type') == 'uplink')

# Apply the mask to keep only uplink messages
df_uplink = df_ns[uplink_mask].copy().reset_index(drop=True)
parsed_uplink = parsed_json[uplink_mask].reset_index(drop=True)

# ---------------------------------------------
# Extract relevant fields from each JSON object
# These fields are necessary for joining, identifying packets, and latency computation
# ---------------------------------------------
df_uplink['payload']            = parsed_uplink.map(lambda p: p.get('params', {}).get('payload'))
df_uplink['rx_time']            = parsed_uplink.map(lambda p: p.get('params', {}).get('rx_time'))
df_uplink['encrypted_payload']  = parsed_uplink.map(lambda p: p.get('params', {}).get('encrypted_payload'))
df_uplink['packet_hash']        = parsed_uplink.map(lambda p: p.get('meta', {}).get('packet_hash'))
df_uplink['device']             = parsed_uplink.map(lambda p: p.get('meta', {}).get('device'))
df_uplink['packet_id']          = parsed_uplink.map(lambda p: p.get('meta', {}).get('packet_id'))
df_uplink['meta_time']          = parsed_uplink.map(lambda p: p.get('meta', {}).get('time'))

# ---------------------------------------------
# Drop duplicated packets based on unique packet hash
# Ensures that each packet is analyzed only once
# ---------------------------------------------
df_uplink = df_uplink.drop_duplicates(subset='packet_hash', keep='first').reset_index(drop=True)

# ---------------------------------------------
# Trim both dataframes (uplink + tx logs) to match in length
# This assumes row-to-row correspondence after sorting/cleanup
# ---------------------------------------------
min_len = min(len(df_uplink), len(df_tx))
df_uplink_trimmed = df_uplink.iloc[:min_len].copy()
df_tx_trimmed = df_tx.iloc[:min_len].copy()

# ---------------------------------------------
# Add the original 'Send_Started' time from transmission log
# Used to compute total end-device to gateway latency
# ---------------------------------------------
df_uplink_trimmed['send_started'] = df_tx_trimmed['Send_Started'].values

# ---------------------------------------------
# Compute latency values (in milliseconds)
# - ed_gateway_latency: time from sending to gateway receive
# - gateway_ns_latency: time from gateway to NS publish
# - ns_as_latency: time from NS publish to EC2 receive
# ---------------------------------------------
df_uplink_trimmed['gateway_ns_latency'] = abs(df_uplink_trimmed['meta_time'] - df_uplink_trimmed['rx_time']) * 1000
df_uplink_trimmed['ns_as_latency'] = abs(df_uplink_trimmed['ec2_time'] - df_uplink_trimmed['meta_time']) * 1000
df_uplink_trimmed['ed_gateway_latency'] = abs(df_uplink_trimmed['rx_time'] - df_uplink_trimmed['send_started']) * 1000

# ---------------------------------------------
# Reorder and select final columns for output
# Includes metadata, payloads, timestamps, and all latency measurements
# ---------------------------------------------
final_df = df_uplink_trimmed[[ 
    'device', 'packet_id', 'packet_hash',
    'payload', 'encrypted_payload',
    'send_started', 'rx_time', 'meta_time', 'ec2_time',
    'ed_gateway_latency', 'gateway_ns_latency', 'ns_as_latency'
]]

# ---------------------------------------------
# Export the cleaned and enhanced latency log to CSV
# ---------------------------------------------
final_df.to_csv(output_path, index=False)

# ---------------------------------------------
# Print confirmation message with output path
# ---------------------------------------------
print(f"✅ Enhanced latency log saved to:\n{output_path}")
