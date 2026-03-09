import serial
import time

# Configuration
PORT = "COM4"  # Replace with your LoRa-E5's COM port
BAUDRATE = 9600  # Default baud rate for LoRa-E5

def send_at_command(serial_conn, command, delay=1):
    """
    Sends an AT command to the LoRa-E5 and reads the response.
    """
    print(f"\nTx: {command}")
    serial_conn.write((command + '\r\n').encode())
    time.sleep(delay)

    response = []
    while serial_conn.in_waiting:
        line = serial_conn.readline()
        decoded_line = line.decode('utf-8', errors="ignore").strip()
        if decoded_line:
            response.append(decoded_line)

    print("Rx:")
    for line in response:
        print("  ", line)
    return response

def join_lorawan(serial_conn):
    """
    Attempts to join the LoRaWAN network and exits when NetID and DevAddr are received.
    """
    print("\nJoining the LoRaWAN network...")
    send_at_command(serial_conn, "AT+JOIN", delay=1)

    got_joined = False
    got_netid = False
    got_done = False

    timeout = time.time() + 30  # 30-second timeout
    while time.time() < timeout:
        if serial_conn.in_waiting:
            line = serial_conn.readline().decode('utf-8', errors="ignore").strip()
            if line:
                print(f"> {line}")
                if "+JOIN: Network joined" in line:
                    got_joined = True
                if "+JOIN: NetID" in line:
                    got_netid = True
                if "+JOIN: Done" in line:
                    got_done = True
                if got_joined and got_netid and got_done:
                    return True
        time.sleep(0.1)
    return False

def main():
    try:
        with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
            print(f"Connected to {PORT} at {BAUDRATE} baud.")

            # Step 1: Configure LoRa-E5
            print("\nConfiguring LoRa-E5...")
            send_at_command(ser, 'AT+LOG=DEBUG')
            send_at_command(ser, 'AT+KEY=APPKEY,"ccf01b79f0ed4d9d834d659cb88d49a3"')
            send_at_command(ser, "AT+DR=DR3")
            send_at_command(ser, "AT+CH=NUM,8-15")
            send_at_command(ser, "AT+MODE=LWOTAA")

            # Step 2: Join
            if join_lorawan(ser):
                print("\nSuccessfully joined the network. Exiting.")
            else:
                print("\nFailed to join the network within timeout.")

    except KeyboardInterrupt:
        print("\nExiting program.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
