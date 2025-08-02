import serial
import time

PORT = "/dev/ttyUSB0"  # or COMx on Windows
BAUD = 10400

ECU_ADDR = 0x10  # Engine ECU address
TESTER_ADDR = 0xF1  # Our address (tester)

# 3-byte header: [target, source, length] + payload + checksum
def fast_init(ser):
    print("[*] Sending ISO14230 fast init with proper header...")
    time.sleep(0.3)
    ser.setRTS(True)
    time.sleep(0.25)
    ser.setRTS(False)
    time.sleep(0.025)

    # Request diagnostic session (service 0x10), payload: [0x81]
    payload = [0x10, 0x81]
    header = [ECU_ADDR, TESTER_ADDR, len(payload)]
    checksum = (sum(header) + sum(payload)) & 0xFF
    msg = bytes(header + payload + [checksum])

    ser.write(msg)
    time.sleep(0.1)
    return ser.read(64)

def send_kwp2000(ser, payload, service_id=None):
    # Build KWP2000 header manually
    length = len(payload)
    header = bytes([ECU_ADDR, TESTER_ADDR, length])
    data = bytes(payload)
    checksum = (sum(header) + sum(data)) & 0xFF
    msg = header + data + bytes([checksum])
    ser.write(msg)
    time.sleep(0.1)
    return ser.read(64)


def read_dtc(ser):
    print("[*] Requesting DTCs...")
    response = send_kwp2000(ser, [0x03])
    print("[+] DTCs response:", response.hex())

def read_readiness(ser):
    print("[*] Reading readiness via PID 01 01...")
    response = send_kwp2000(ser, [0x01, 0x01])
    print("[+] Readiness:", response.hex())

def read_block(ser, block):
    print(f"[*] Reading 4-byte block {block:02d}...")
    response = send_kwp2000(ser, [0x21, block])
    print(f"[+] Block {block:02d}:", response.hex())

def scan_all_blocks(ser):
    print("[*] Scanning all measuring blocks (0x01–0xFF)...")
    for block in range(1, 256):
        response = send_kwp2000(ser, [0x21, block])
        if response.startswith(b'\x82\x21') and len(response) > 4:
            print(f"[+] Block {block:02X}: {response.hex()} -> Data: {list(response[3:])}")

def main():
    ser = serial.Serial(PORT, baudrate=BAUD, timeout=1)
    fast_init(ser)

    read_dtc(ser)
    read_readiness(ser)

    # scan_all_blocks(ser)

    for b in [1, 2, 3]:
        read_block(ser, b)

    ser.close()

if __name__ == "__main__":
    main()
