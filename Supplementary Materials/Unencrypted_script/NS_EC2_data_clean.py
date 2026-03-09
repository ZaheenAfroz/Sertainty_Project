import pandas as pd
import json

# Define csv path
csv_path = r'C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\dataset\June 18\ns_latency_log.csv'

# Load csv file
df = pd.read_csv(csv_path)

# Rename columns based on actual headers
df.rename(columns={
    "ec2_receive": "ec2_time",
    "ns_publish": "meta_time",
    # raw_json already correctly named
}, inplace=True)

# Parse raw JSON and filter only 'uplink' type messages
parsed_json = df['raw_json'].dropna().apply(json.loads)
uplink_mask = parsed_json.apply(lambda p: p.get('type') == 'uplink')

df_uplink = df[uplink_mask].copy().reset_index(drop=True)
parsed_uplink = parsed_json[uplink_mask].reset_index(drop=True)

# Extract fields from JSON
df_uplink['payload']            = parsed_uplink.map(lambda p: p.get('params', {}).get('payload'))
df_uplink['rx_time']            = parsed_uplink.map(lambda p: p.get('params', {}).get('rx_time'))
df_uplink['encrypted_payload']  = parsed_uplink.map(lambda p: p.get('params', {}).get('encrypted_payload'))
df_uplink['packet_hash']        = parsed_uplink.map(lambda p: p.get('meta', {}).get('packet_hash'))
df_uplink['device']             = parsed_uplink.map(lambda p: p.get('meta', {}).get('device'))
df_uplink['packet_id']          = parsed_uplink.map(lambda p: p.get('meta', {}).get('packet_id'))
df_uplink['meta_time']          = parsed_uplink.map(lambda p: p.get('meta', {}).get('time'))

# Drop duplicate packet_hash entries
df_uplink = df_uplink.drop_duplicates(subset='packet_hash', keep='first').reset_index(drop=True)

# Compute latency
df_uplink['gateway_ns_latency'] = df_uplink['meta_time'] - df_uplink['rx_time']
df_uplink['ns_as_latency']      = df_uplink['ec2_time'] - df_uplink['meta_time']

# Select final columns
output_df = df_uplink[[ 
    'device', 'packet_id', 'packet_hash',
    'payload', 'encrypted_payload',
    'rx_time', 'meta_time', 'ec2_time',
    'gateway_ns_latency', 'ns_as_latency'
]]

# Save the updated cleaned file
output_path = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\dataset\June 18\ns_latency_cleaned.csv"
output_df.to_csv(output_path, index=False, float_format='%.6f')

output_path


