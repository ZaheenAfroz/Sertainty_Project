# Import required libraries
import serial  # Used for serial communication with LoRa-E5
import time    # Used for adding delays and timeouts

# Configuration
PORT = "COM4"       # COM port where the LoRa-E5 is connected
BAUDRATE = 9600     # Baud rate for communication; 9600 is the default for LoRa-E5

def send_at_command(serial_conn, command, delay=1):
    """
    Sends an AT command to the LoRa-E5 device and reads the response.
    
    Parameters:
        serial_conn: Active serial connection object
        command: AT command to send (as a string)
        delay: Optional wait time after sending the command (default 1 second)
    
    Returns:
        A list of strings containing lines received in response
    """
    print(f"\nTx: {command}")  # Print command being sent
    serial_conn.write((command + '\r\n').encode())  # Send command with newline
    time.sleep(delay)  # Wait to allow device to process the command

    response = []  # List to collect response lines
    while serial_conn.in_waiting:  # While there is data to be read
        line = serial_conn.readline()  # Read one line
        decoded_line = line.decode('utf-8', errors="ignore").strip()  # Decode and clean line
        if decoded_line:  # If the line is not empty
            response.append(decoded_line)  # Add it to the response

    print("Rx:")  # Indicate start of received response
    for line in response:
        print("  ", line)  # Print each line of response
    return response  # Return the full list of responses

def join_lorawan(serial_conn):
    """
    Attempts to join the LoRaWAN network using OTAA mode.
    Waits for key response strings to confirm successful join.
    
    Parameters:
        serial_conn: Active serial connection object
    
    Returns:
        True if joined successfully within timeout, else False
    """
    print("\nJoining the LoRaWAN network...")
    send_at_command(serial_conn, "AT+JOIN", delay=1)  # Send join command

    # Flags to check for various join confirmations
    got_joined = False
    got_netid = False
    got_done = False

    timeout = time.time() + 30  # Timeout in 30 seconds
    while time.time() < timeout:
        if serial_conn.in_waiting:  # If there’s data to read
            line = serial_conn.readline().decode('utf-8', errors="ignore").strip()  # Read and clean line
            if line:
                print(f"> {line}")  # Print the incoming message
                # Set flags based on received strings
                if "+JOIN: Network joined" in line:
                    got_joined = True
                if "+JOIN: NetID" in line:
                    got_netid = True
                if "+JOIN: Done" in line:
                    got_done = True
                # If all conditions met, return success
                if got_joined and got_netid and got_done:
                    return True
        time.sleep(0.1)  # Brief delay to avoid CPU overuse
    return False  # Timeout occurred before complete join

def main():
    """
    Main function to open the serial connection, configure the LoRa-E5,
    and attempt to join the LoRaWAN network.
    """
    try:
        # Open serial port using context manager for safe closing
        with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:        #Connect LoRa-E5 board
            print(f"Connected to {PORT} at {BAUDRATE} baud.")

            # Step 1: Configure LoRa-E5 for OTAA join
            print("\nConfiguring LoRa-E5...")
            send_at_command(ser, 'AT+LOG=DEBUG')  # Enable debug logging
            send_at_command(ser, 'AT+KEY=APPKEY,"ccf01b79f0ed4d9d834d659cb88d49a3"')  # Set AppKey for OTAA
            send_at_command(ser, "AT+DR=DR3")  # Set data rate (DR3 usually corresponds to SF7)
            send_at_command(ser, "AT+CH=NUM,8-15")  # Set active channels (channels 8 to 15)
            send_at_command(ser, "AT+MODE=LWOTAA")  # Set mode to LoRaWAN OTAA

            # Step 2: Attempt to join the network
            if join_lorawan(ser):
                print("\nSuccessfully joined the network. Exiting.")
            else:
                print("\nFailed to join the network within timeout.")

    except KeyboardInterrupt:
        print("\nExiting program.")  # Gracefully handle Ctrl+C interruption
    except Exception as e:
        print(f"Error: {e}")  # Print any unexpected errors

# Entry point check
if __name__ == "__main__":
    main()
