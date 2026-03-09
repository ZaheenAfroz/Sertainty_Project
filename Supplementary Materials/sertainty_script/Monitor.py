import os
import time
import csv
import mimetypes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import threading

# === Folder Paths ===
# Update these paths to your system configuration
PROTECT_FOLDER = r"C:\Users\zahee\OneDrive\Desktop\May_test\Protect"
PROTECTED_FOLDER = r"C:\Users\zahee\OneDrive\Desktop\May_test\Protected"
SPLIT_FOLDER = r"C:\Users\zahee\OneDrive\Desktop\May_test\Split"
SPLITTED_FOLDER = r"C:\Users\zahee\OneDrive\Desktop\May_test\Split2"
JOINED_FOLDER = r"C:\Users\zahee\OneDrive\Desktop\May_test\Joined"
UNPROTECT_FOLDER = r"C:\Users\zahee\OneDrive\Desktop\May_test\Unprotect"

# === Log File Path ===
LOG_FILE = r"C:\Users\zahee\OneDrive - Texas State University\Documents\Sertainty project\code_2025\scripts\June scripts\sertainty_scriptfolder_monitor_log.csv"

# === Timestamp Dictionary ===
# Used to calculate latencies between stages
timestamps = {
    'original_file': None,
    'encrypted_file': None,
    'first_chunk_file': None,
    'last_chunk_file': None,
    'splitted_meta': None,
    'joined_uxp': None,
    'decrypted_file': None
}

# === Logging Helper Functions ===

# Log to terminal
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# Log to CSV file
def write_to_csv(event, latency):
    with open(LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        if isinstance(latency, (int, float)):
            latency_str = f"{latency:.6f}"
        elif isinstance(latency, str):
            latency_str = latency
        else:
            latency_str = "N/A"
        writer.writerow([f"{time.time():.6f}", event, latency_str])

# === Initialize log file with header if missing ===
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Unix_Timestamp", "Event", "Latency (s)"])

# === Folder Event Handlers ===

# 1. Monitor when a file is dropped in the Protect folder
class ProtectHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:    #Ensures the handler only responds to files, not folder creation.
            timestamps['original_file'] = time.time()
            file_path = event.src_path
            mime_type, _ = mimetypes.guess_type(file_path)
            log(f"File dropped into Protect folder: {file_path}")
            log(f"Detected original file type: {mime_type if mime_type else 'Unknown'}")
            write_to_csv("Original file dropped", None)
            write_to_csv("Original file MIME type", mime_type if mime_type else "Unknown")

# 2. Monitor encrypted UXP file creation/modification
class ProtectedHandler(FileSystemEventHandler):
    def process_event(self, file_path):
        if file_path.endswith('.uxp'):
            if timestamps['encrypted_file'] is None:
                timestamps['encrypted_file'] = time.time()
                log(f"Encrypted .uxp file created or modified: {file_path}")
                if timestamps['original_file']:
                    latency = timestamps['encrypted_file'] - timestamps['original_file']
                    log(f"Encryption latency: {latency:.6f} seconds")
                    write_to_csv("Encrypted file created", latency)
                else:
                    write_to_csv("Encrypted file created", None)

    def on_created(self, event):
        if not event.is_directory:
            self.process_event(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.process_event(event.src_path)

# 3. Monitor split chunk file creation
class SplitHandler(FileSystemEventHandler):
    last_activity_time = None
    first_activity_recorded = False

    def on_created(self, event):
        if not event.is_directory:
            now = time.time()
            SplitHandler.last_activity_time = now
            if not SplitHandler.first_activity_recorded:
                timestamps['first_chunk_file'] = now
                SplitHandler.first_activity_recorded = True
                if timestamps['encrypted_file']:
                    latency = timestamps['first_chunk_file'] - timestamps['encrypted_file']
                    log(f"First split file detected. Latency from encryption: {latency:.6f} seconds")
                    write_to_csv("First split file created", latency)
                else:
                    log("First split file detected but encrypted timestamp is missing.")
                    write_to_csv("First split file created", None)

            log(f"Split file created: {event.src_path}")

# 4. Monitor when the .meta file is created during splitting
class SplittedHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('.meta'):
            timestamps['splitted_meta'] = time.time()
            log(f"Splitted .meta file detected: {event.src_path}")
            write_to_csv("Splitted meta file detected", None)

# 5. Monitor when a joined UXP file is created
class JoinedHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('.uxp'):
            timestamps['joined_uxp'] = time.time()
            log(f"Joined .uxp file detected: {event.src_path}")
            if timestamps['splitted_meta']:
                latency = timestamps['joined_uxp'] - timestamps['splitted_meta']
                log(f"Join latency from splitted meta: {latency:.6f} seconds")
                write_to_csv("Joined file created", latency)
            else:
                write_to_csv("Joined file created", None)

# 6. Monitor when decrypted file appears in Unprotect folder
class UnprotectHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            timestamps['decrypted_file'] = time.time()
            file_path = event.src_path
            mime_type, _ = mimetypes.guess_type(file_path)

            log(f"Decrypted file detected in Unprotect folder: {file_path}")
            log(f"Detected decrypted file type: {mime_type if mime_type else 'Unknown'}")
            write_to_csv("Decrypted file detected", None)
            write_to_csv("Decrypted file MIME type", mime_type if mime_type else "Unknown")

            if timestamps['joined_uxp']:
                latency = timestamps['decrypted_file'] - timestamps['joined_uxp']
                log(f"Decryption latency from joined .uxp: {latency:.6f} seconds")
                write_to_csv("Decryption latency from joined .uxp", latency)
            else:
                log("Joined .uxp timestamp missing — skipping decryption latency")
                write_to_csv("Decryption latency from joined .uxp", None)

# === Split Completion Watch Thread ===
def monitor_split_completion():
    idle_time = 5  # No new split files for 5 seconds → split assumed complete
    while True:
        if SplitHandler.last_activity_time and time.time() - SplitHandler.last_activity_time > idle_time:
            timestamps['last_chunk_file'] = SplitHandler.last_activity_time
            if timestamps['first_chunk_file']:
                total_split_time = timestamps['last_chunk_file'] - timestamps['first_chunk_file']
                log(f"Split process complete. Total split time: {total_split_time:.6f} seconds")
                write_to_csv("Split process completed", total_split_time)
            else:
                log("Split process complete, but first_chunk_file timestamp is missing.")
                write_to_csv("Split process completed", None)
            observer.unschedule(split_watch)
            break
        time.sleep(1)

# === Watchdog Setup ===
observer = Observer()
observer.schedule(ProtectHandler(), PROTECT_FOLDER, recursive=False)
observer.schedule(ProtectedHandler(), PROTECTED_FOLDER, recursive=False)
split_watch = observer.schedule(SplitHandler(), SPLIT_FOLDER, recursive=False)
observer.schedule(SplittedHandler(), SPLITTED_FOLDER, recursive=False)
observer.schedule(JoinedHandler(), JOINED_FOLDER, recursive=False)
observer.schedule(UnprotectHandler(), UNPROTECT_FOLDER, recursive=False)

# === Start Monitoring ===
log("Monitoring started...")
observer.start()

try:
    # Start background thread to monitor for end of splitting
    split_thread = threading.Thread(target=monitor_split_completion)
    split_thread.start()

    # Keep main thread alive
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

observer.join()
log("Monitoring stopped.")
