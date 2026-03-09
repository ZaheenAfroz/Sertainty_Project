import pandas as pd
import json

# === File Paths ===
# Path to cleaned Network Server (NS) latency log
ns_latency_file = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\ns_latency_cleaned_uxp.csv"

# Path to chunk transmission log (contains Send_Start times)
chunk_transmission_file = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\chunk_transmission_log.csv"

# === Load CSV Files ===
df_ns = pd.read_csv(ns_latency_file)        # Load cleaned NS latency log
df_tx = pd.read_csv(chunk_transmission_file)  # Load transmission log with Send_Start

# === Extract rx_time from raw_json column in NS data ===
# The raw_json column contains nested JSON; we extract 'rx_time' from it
df_ns['rx_time'] = df_ns['raw_json'].dropna().apply(
    lambda x: json.loads(x).get('params', {}).get('rx_time', None)
)

# === Convert timestamp-related columns to numeric ===
# This ensures mathematical operations can be performed safely
df_ns['rx_time'] = pd.to_numeric(df_ns['rx_time'], errors='coerce')
df_ns['ns_publish'] = pd.to_numeric(df_ns['ns_publish'], errors='coerce')
df_ns['ec2_receive'] = pd.to_numeric(df_ns['ec2_receive'], errors='coerce')
df_tx['Send_Start'] = pd.to_numeric(df_tx['Send_Start'], errors='coerce')

# === Align both dataframes to the same length ===
# This prevents index mismatches during pairwise latency calculations
min_len = min(len(df_ns), len(df_tx))
df_ns_trimmed = df_ns.iloc[:min_len].copy()
df_tx_trimmed = df_tx.iloc[:min_len].copy()

# === Calculate Latency Metrics ===
# Time differences in milliseconds between key events
df_ns_trimmed['ed_gateway_latency'] = abs(df_ns_trimmed['rx_time'] - df_tx_trimmed['Send_Start']) * 1000  # Device to Gateway
df_ns_trimmed['gateway_ns_latency'] = abs(df_ns_trimmed['ns_publish'] - df_ns_trimmed['rx_time']) * 1000  # Gateway to NS
df_ns_trimmed['ns_as_latency'] = abs(df_ns_trimmed['ec2_receive'] - df_ns_trimmed['ns_publish']) * 1000    # NS to App Server

# === Create Final Latency DataFrame ===
latency_df = df_ns_trimmed[['packet_id', 'packet_hash', 'rx_time', 'ns_publish', 'ec2_receive',
                            'ed_gateway_latency', 'gateway_ns_latency', 'ns_as_latency']].copy()

# Add 'Send_Start' column from transmission log
latency_df['send_start'] = df_tx_trimmed['Send_Start'].values

# === Reorder Columns for Clarity ===
latency_df = latency_df[['packet_id', 'packet_hash', 'send_start', 'rx_time', 'ns_publish',
                         'ec2_receive', 'ed_gateway_latency', 'gateway_ns_latency', 'ns_as_latency']]

# === Save Output to Excel ===
output_file = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\latency_output.xlsx"
latency_df.to_excel(output_file, index=False)

print(f"✅ Latency metrics saved to {output_file}")
