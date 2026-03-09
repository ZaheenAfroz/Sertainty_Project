from docx import Document
import pandas as pd
import re
from datetime import datetime

# === Step 1: Load document (do NOT reverse) ===
doc_path = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\dataset\June 17\test8_200m_1510\ns_signal.docx"  # ⬅️ Update this with your real path
doc = Document(doc_path)
paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

# === Step 2: Define matching patterns ===
pattern_time = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}[a-f0-9]{4}[a-f0-9]+$", re.IGNORECASE)
pattern_trend = re.compile(r"^trending_up\d+$", re.IGNORECASE)
pattern_wifi = re.compile(r"^wifi90[\d\.]+MHz$", re.IGNORECASE)
pattern_signal = re.compile(r"^signal_cellular_alt[\d\.-]+dB/-?\d+dBm$", re.IGNORECASE)

# === Step 3: Extract data from 4-line blocks ===
entries = []
i = 0
while i < len(paragraphs) - 3:
    if (pattern_time.match(paragraphs[i]) and
        pattern_trend.match(paragraphs[i + 1]) and
        pattern_wifi.match(paragraphs[i + 2]) and
        pattern_signal.match(paragraphs[i + 3])):

        time_payload = paragraphs[i]
        time_str = time_payload[:12]  # First 12 chars = HH:MM:SS.sss
        packet_hash = time_payload[12:16]  # Next 4 chars = packet hash

        try:
            # Convert to Unix time
            unix_time = datetime.strptime("2025-06-14 " + time_str, "%Y-%m-%d %H:%M:%S.%f").timestamp()

            # Extract SNR and RSSI
            signal_line = paragraphs[i + 3]
            snr = float(re.search(r"signal_cellular_alt([\d\.-]+)dB", signal_line).group(1))
            rssi = int(re.search(r"/(-?\d+)dBm", signal_line).group(1))

            entries.append({
                "time_payload": time_payload,
                "time": time_str,
                "unix_time": unix_time,
                "packet_hash": packet_hash,
                "trending": paragraphs[i + 1],
                "wifi": paragraphs[i + 2],
                "SNR (dB)": snr,
                "RSSI (dBm)": rssi
            })
        except Exception:
            pass

        i += 4
    else:
        i += 1

# === Step 4: Create DataFrame, filter unique hashes, sort by time ===
df = pd.DataFrame(entries)
df = df.drop_duplicates(subset="packet_hash", keep="first")
df = df.sort_values(by="unix_time").reset_index(drop=True)

# === Step 5: Save to Excel ===
output_path = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\dataset\June 17\test8_200m_1510\signal_data_cleaned.xlsx"  # ⬅️ Update this as needed
df.to_excel(output_path, index=False)
print(f"✅ File saved to: {output_path}")


#doc_path = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\dataset\June 14\Test 1\Signal_raw.docx"
#output_path = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\dataset\June 14\Test 1\signal_data_cleaned.xlsx"