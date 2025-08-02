import serial
import time

PORT = "/dev/ttyUSB0"  # change to COMx on Windows
BAUD = 9600            # 9600 for VAG KWP1281
TIMEOUT = 1.0

def kwp_send(ser, data):
    ser.write(bytes(data))
    ser.flush()
    time.sleep(0.1)
    return ser.read(256)

def kwp_init(ser):
    print("[*] Sending wakeup 0x01 to engine ECU")
    ser.write(b'\x01')
    time.sleep(1.0)

    echo = ser.read(1)
    if echo != b'\x55':
        print("[-] Failed to init. Expected 0x55, got:", echo.hex())
        return False

    key_bytes = ser.read(2)
    if len(key_bytes) != 2:
        print("[-] ECU did not respond correctly.")
        return False

    key = key_bytes[0]
    response = 0x03 ^ key
    print(f"[+] ECU Key: {key:02X}, sending response: {response:02X}")
    ser.write(bytes([response]))

    ident = ser.read(100)
    print("[+] ECU Ident:", ident.decode(errors='ignore').strip())
    return True

def read_dtc(ser):
    print("[*] Reading DTCs...")
    kwp_send(ser, [0x07])
    time.sleep(0.2)
    dtc_data = ser.read(100)
    print("[+] DTC raw data:", dtc_data.hex())
    print("[!] (Decoding DTCs not implemented here)")

def read_readiness(ser):
    print("[*] Reading readiness (block 15)...")
    kwp_send(ser, [0x60, 0x0F])
    time.sleep(0.1)
    result = ser.read(20)
    print("[+] Readiness response:", result.hex())

def read_measuring_block(ser, block_id):
    print(f"[*] Reading block {block_id:02d}...")
    kwp_send(ser, [0x60, block_id])
    time.sleep(0.2)
    result = ser.read(20)
    print(f"[+] Block {block_id:02d} data: {result.hex()}")

def main():
    ser = serial.Serial(PORT, baudrate=BAUD, timeout=TIMEOUT)
    ser.flushInput()

    if not kwp_init(ser):
        print("[-] Could not initialize communication.")
        ser.close()
        return

    # Read DTCs, readiness and measuring blocks
    read_dtc(ser)
    read_readiness(ser)
    for block in [1, 2, 3]:
        read_measuring_block(ser, block)

    ser.close()

if __name__ == "__main__":
    main()
