from pyftdi.serialext import serial_for_url
import time
import serial

ADDRESS = 0x17  # Engine ECU
BIT_DURATION = 0.20  # 200 ms = 5 baud

def parity_odd(byte):
    """Calculate parity bit for 7 data bits (odd parity)."""
    data = byte & 0x7F  # 7-bit
    ones = bin(data).count('1')
    return 0 if ones % 2 else 1  # Add parity bit to make total number of 1s odd

def framed_bits_7O1(byte):
    """Generate framed bit sequence: start(0) + 7 data bits + parity + stop(1)."""
    bits = [0]  # Start bit
    bits += [(byte >> i) & 1 for i in range(7)]  # LSB first
    bits.append(parity_odd(byte))  # Parity bit
    bits.append(1)  # Stop bit
    return bits

def send_5baud_7O1(ser, byte):
    bits = framed_bits_7O1(byte)
    print(f"[*] Sending 5Bd 7O1 framed byte 0x{byte:02X}: {bits}")
    for i, bit in enumerate(bits):
        ser.break_condition = (bit == 0)
        time.sleep(BIT_DURATION)
    ser.break_condition = False  # Idle state
    #    print("[+] Init sequence complete.")
    # ser.break_condition = False
    time.sleep(0.5)  # let line return to idle
    #ser.flushInput()

def read_response(ser):
    #time.sleep(0.3)
    response = ser.read(64)
    print(f"[+] Raw ECU response: {response.hex()}")
    return response

def read_ecu_response(serial_ser):
    print("[*] Reading ECU sync and key bytes...")
    response = serial_ser.read(64)
    print(f"[+] Raw ECU response: {response.hex()}")

    try:
        idx = response.index(0x55)
        if idx + 2 < len(response):
            key1 = response[idx + 1]
            key2 = response[idx + 2]
            print(f"[✓] Found sync at byte {idx}: key1=0x{key1:02X}, key2=0x{key2:02X}")

            answer = 0xff - key2
            print(f"[+] ECU key: 0x{key2:02X}, sending response: 0x{answer:02X}")
            serial_ser.write(bytes([answer]))
            time.sleep(0.5)
            ident = serial_ser.read(1)
            for i in range(1, 100):
                ident = serial_ser.read(1)
                if ident is None:
                    time.sleep(0.3)
                    continue
                answer = 0xff - ident[0]

                print(f" {ident[0]:02x} answer: 0x{answer:02X}")
                serial_ser.write(bytes([answer]))

            # print("[+] ECU Ident:", ident.decode("ascii", errors="ignore").strip())
            print("done")
            return key1
        else:
            print("[-] Not enough bytes after sync for key bytes.")
            return None
    except ValueError:
        print("[-] Sync byte 0x55 not found in response.")
        return None

def xor_handshake(ser, response):
    if not response or response[0] != 0x55:
        print(f"[-] Sync byte missing or invalid.")
        return False
    if len(response) < 3:
        print("[-] Not enough bytes for key.")
        return False
    key = response[1]
    answer = key ^ 0x03
    print(f"[+] ECU key: 0x{key:02X}, sending response: 0x{answer:02X}")
    ser.write(bytes([answer]))
    time.sleep(0.5)
    ident = ser.read(128)
    for i in ident:
        print(f" {i.hex()}")

    print("[+] ECU Ident:", ident.decode("ascii", errors="ignore").strip())
    return True

def main():
    try:


        ser = serial_for_url('ftdi:///1', baudrate=10400, timeout=0.4)
        #ser = serial_for_url('ftdi:///1', baudrate=9600, timeout=0.4)

        ser.flush()
        send_5baud_7O1(ser, ADDRESS)
        # ser.close()
        # time.sleep(0.01)
        resp = read_ecu_response(ser)
        #resp = read_response(ser)
        xor_handshake(ser, resp)
        ser.close()
    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    main()
