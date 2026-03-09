#!/usr/bin/env python3
"""
ns_to_ec2_latency.py

Subscribe to Mosquitto on EC2, capture each uplink JSON as it arrives,
timestamp locally, extract the NS's meta.time, compute latency, and log
everything to a CSV file that matches your cleaned schema.
"""

import time
import json
import csv
import os
import paho.mqtt.client as mqtt

# ─── CONFIGURE & TRUNCATE LOG ─────────────────────────────────────────────────
LOG_PATH = os.path.expanduser("~/ns_latency_log.csv")

# Always overwrite on start so you only get the current session
with open(LOG_PATH, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "topic",
        "ec2_receive",     # when EC2 got it
        "ns_publish",      # packet.meta.time from NS
        "packet_hash",     # first-4 chars of the hash
        "latency_as_ns",   # EC2 receive minus NS publish
        "payload",         # raw payload string
        "packet_id",       # unique ID
        "raw_json"         # full JSON blob (minified)
    ])

# ─── MQTT + AUTH SETTINGS ──────────────────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT = 1883
MQTT_USER   = "Simin"
MQTT_PASS   = "Simin"
TOPIC       = "#"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[INFO] Connected to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")
        client.subscribe(TOPIC)
        print(f"[INFO] Subscribed to topic '{TOPIC}'")
    else:
        print(f"[ERROR] Connection failed (rc={rc})")

def on_message(client, userdata, msg):
    # 1) timestamp when we get it
    ec2_receive = time.time()
    raw = msg.payload.decode("utf-8", errors="ignore").strip()

    # 2) parse JSON
    try:
        packet = json.loads(raw)
    except json.JSONDecodeError:
        print("[WARN] Non-JSON payload on", msg.topic)
        return
    # 🔥 Filter: Process only uplink messages
    if packet.get("type") != "uplink":
        return

    # 3) pull out NS publish time
    ns_publish = packet.get("meta", {}).get("time")
    if ns_publish is None:
        print("[WARN] Missing meta.time; skipping")
        return

    # 4) extract the 4-char hash prefix
    packet_hash = packet.get("meta", {}).get("packet_hash", "")[:4]
    payload     = packet.get("params", {}).get("payload", "")
    packet_id   = packet.get("meta", {}).get("packet_id", "")

    # 5) compute latency
    latency_as_ns = ec2_receive - ns_publish

    # 6) append one new row
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            msg.topic,
            f"{ec2_receive:.6f}",
            f"{ns_publish:.6f}",
            packet_hash,
            f"{latency_as_ns:.6f}",
            payload,
            packet_id,
            json.dumps(packet, separators=(",", ":"))
        ])
        f.flush()

    # 7) console feedback
    print("─" * 60)
    print(f"Topic        : {msg.topic}")
    print(f"EC2 receive  : {ec2_receive:.6f}")
    print(f"NS publish   : {ns_publish:.6f}")
    print(f"Latency (s)  : {latency_as_ns:.6f}")
    print(f"Packet hash  : {packet_hash}")
    print(f"Payload      : {payload}")
    print(f"Packet ID    : {packet_id}")
    print("Raw JSON     :")
    print(json.dumps(packet, indent=2))
    print("─" * 60 + "\n")

def main():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT)

    try:
        print("[INFO] Starting MQTT loop. Waiting for uplinks…")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user; exiting.")
        client.disconnect()

if __name__ == "__main__":
    main()
