from pyftdi.serialext import serial_for_url
import time
import queue
import serial
import threading

ADDRESS = 0x46  # Engine ECU
BIT_DURATION = 0.20  # 200 ms = 5 baud
SOURCE = 0xF1

class OBD:
    def __init__(self):
        if ADDRESS == 0x46:
            self.ser = serial_for_url('ftdi:///1', baudrate=9600, timeout=0.01)
        else:
            self.ser = serial_for_url('ftdi:///1', baudrate=10400, timeout=0.01)
        self.ser.flush()
        self.debug = True
        self.init_complete = False
        self.q = queue.Queue()

        self.rx_thread = threading.Thread(target=self.read_loop, args=())
        self.rx_thread.start()

    def parity_odd(self, byte):
        """Calculate parity bit for 7 data bits (odd parity)."""
        data = byte & 0x7F  # 7-bit
        ones = bin(data).count('1')
        return 0 if ones % 2 else 1  # Add parity bit to make total number of 1s odd

    def framed_bits_7O1(self, byte):
        """Generate framed bit sequence: start(0) + 7 data bits + parity + stop(1)."""
        bits = [0]  # Start bit
        bits += [(byte >> i) & 1 for i in range(7)]  # LSB first
        bits.append(self.parity_odd(byte))  # Parity bit
        bits.append(1)  # Stop bit
        return bits

    def send_5baud_7O1(self, byte):
        bits = self.framed_bits_7O1(byte)
        print(f"[*] Sending 5Bd 7O1 framed byte 0x{byte:02X}: {bits}")
        for i, bit in enumerate(bits):
            self.ser.break_condition = (bit == 0)
            time.sleep(BIT_DURATION)
        self.ser.break_condition = False  # Idle state
        #    print("[+] Init sequence complete.")
        # ser.break_condition = False
        # time.sleep(0.3)  # let line return to idle
        #ser.flushInput()

    def read_loop(self, debug=False):
        echo = -1
        while True:
            a = self.ser.read(64)
            if len(a) > 0:
                for c in a:
                    if c == echo:
                        # skip echo
                        echo = -1
                        continue

                    self.q.put(c)
                    if debug:
                        print(f"> 0x{c:02X}")
                    if self.init_complete:
                        answer = (~c) & 0xFF
                        print(f"\t\t\t 0x{c:02X} => 0x{answer:02X}")
                        time.sleep(0.005)
                        self.ser.write(bytes([answer]))
                        echo = answer
            else:
                time.sleep(0.01)

    def read_byte(self, wait=True):
        while True:
            try:
                first = self.q.get(timeout=1)
                if self.debug:
                    print(f"rx> 0x{first:02x}")
                return first
            except queue.Empty:
                print("buffer empty")
            if wait:
                continue
            else:
                break
        return None

    def wait_byte(self, byte, timeout=1):
        t = 0
        while True:
            b = self.read_byte()
            if b == byte:
                return True
            else:
                print(f"ignore {b:02X}")
            t += 1
            if t > timeout:
                return False

    def send_bytes(self, data_bytes, echo=True):
        for b in data_bytes:
            self.ser.write(bytes([b]))
            # echo
            e = self.wait_byte(b, timeout=1)
            if not e:
                return False
        return True

    def send_acknowledge(self, byte):
        # answer = 0xff - byte
        answer = (~byte) & 0xFF
        if self.debug:
            print(f"ackn> 0x{answer:02x}")
        return self.send_bytes(bytes([answer]))

    def read_sequence(self):
        self.wait_byte(0x55)
        key1 = self.read_byte()
        key2 = self.read_byte()
        v = self.read_byte()
        print(f"value {key1:02X} {key2:02X} {v}")
        self.send_acknowledge(v)

    def print_hex_bytes(self, bytes, prefix=""):
        print(f"{prefix}>", end="")
        for byte in bytes:
            print(f"0x{byte:02X} ", end="")
        print("")

    def print_ascii_bytes(self, bytes, prefix=""):
        print(f"{prefix}>", end="")
        for byte in bytes:
            print(f"{chr(byte)}", end="")
        print("")

    def cs_xor(self, data):
        c = 0
        for b in data:
            c ^= b
        return c & 0xFF

    def send_id_request(self):

        for sub in range(90, 0xa0):
            b = bytearray([0x3, ADDRESS, SOURCE, 0x1a, sub ])
            b.append(self.cs_xor(b))

            self.ser.write(b)
            if self.debug:
                self.print_hex_bytes(b, "request")
            buf = []
            for i in range(1,255):
                v = self.read_byte(wait=False)
                if v is None:
                    break
                buf.append(v)

            print(f"received {len(buf)} bytes")

            self.print_hex_bytes(buf, "hex")
            self.print_ascii_bytes(buf, "ascii")



    def initialize_ecu(self):

        # read start byte
        self.wait_byte(0x55, timeout=10)

        while True:
            key1 = self.read_byte()
            key2 = self.read_byte()
            print(f"key2 {key2:02x}")

            answer = (~key2) & 0xFF
            self.ser.write(bytes([answer]))
            print(f"answer 0x{answer:02X}")
            v = self.read_byte(wait=False)
            if v == answer:
                break
            else:
                continue

        self.init_complete = True

        # self.send_id_request()

        l = []
        while True:
           time.sleep(1)


def main():
    try:

        obd = OBD()


        obd.send_5baud_7O1(ADDRESS)

        obd.initialize_ecu()


        # rx_thread.join(timeout=2)
        # ser.close()

    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    main()
