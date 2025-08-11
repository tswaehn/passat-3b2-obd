from pyftdi.serialext import serial_for_url
import time
import queue
import serial
import threading

#ADDRESS = 0x1  # Engine ECU
ADDRESS = 0x17  # instruments
BIT_DURATION = 0.20  # 200 ms = 5 baud

BLOCK_END = 0x03

CMD_ACK = 0x09
CMD_READ_GROUP = 0x29

class OBD:
    def __init__(self):
        if ADDRESS == 0x46:
            self.ser = serial_for_url('ftdi:///1', baudrate=9600, timeout=0.01)
        else:
            self.ser = serial_for_url('ftdi:///1', baudrate=10400, timeout=0.01)
        self.ser.flush()
        self.low_level_debug = False
        self.block_counter = 0
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
        while True:
            a = self.ser.read(64)
            if len(a) > 0:
                for c in a:
                    self.q.put(c)
                    if self.low_level_debug:
                        print(f"> 0x{c:02X}")
            else:
                time.sleep(0.01)

    def read_byte(self, wait=True):
        while True:
            try:
                first = self.q.get(timeout=1)
                if self.low_level_debug:
                    print(f"rx> 0x{first:02x}")
                return first
            except queue.Empty:
                print("buffer empty")
            if wait:
                continue
            else:
                break
        return None

    def write_byte(self, data_byte):
        if self.low_level_debug:
            print(f"tx> 0x{data_byte:02X}")
        self.ser.write(bytes([data_byte]))

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

    def read_ecu_block(self):

        buffer = bytearray()

        block_length = self.read_byte()
        answer = (~block_length) & 0xFF
        self.write_byte(answer)
        echo = self.read_byte()
        if echo != answer:
            return None

        print(f"reading response len {block_length}")
        for i in range(1, block_length):
            d = self.read_byte()

            # decide what to do
            if i == 1:
                self.block_counter = d
            elif i == 2:
                block_type = d

            buffer.append(d)

            # send ackn
            answer = (~d) & 0xFF
            self.write_byte(answer)
            echo = self.read_byte()
            if echo != answer:
                return None

        # last byte should be BLOCK_END
        b = self.read_byte()
        if b != BLOCK_END:
            return None

        self.print_hex_bytes(buffer, "hex")
        self.print_ascii_bytes(buffer, "ascii")
        return buffer

    def write_raw_block(self, block):
        self.print_hex_bytes(block, "write CMD")
        for b in block:
            self.write_byte(b)
            echo = self.read_byte()
            if b != echo:
                return False
            answer = self.read_byte()
            expected_answer = (~b) & 0xFF
            if answer != expected_answer:
                return False
        # EOF
        self.write_byte(BLOCK_END)
        echo = self.read_byte()
        if echo != BLOCK_END:
            return False
        return True

    def write_ecu_block(self, cmd, data=None):

        block = []
        if data is None:
            data = []

        length = 3 + len(data)

        # length
        block.append(length)

        # block counter
        self.block_counter += 1
        if self.block_counter > 255:
            self.block_counter = 0

        block.append(self.block_counter)

        # cmd
        block.append(cmd)

        # optional data
        for b in data:
            block.append(b)

        # EOF block
        return self.write_raw_block(block)


    def initialize_ecu(self):
        complete = False

        while not complete:

            # weak up ecu
            self.send_5baud_7O1(ADDRESS)

            # read start byte
            self.wait_byte(0x55, timeout=10)

            while True:
                key1 = self.read_byte(wait=False)
                key2 = self.read_byte(wait=False)
                print(f"key2 {key2:02x}")

                answer = 0xff - key2
                print(f"answer 0x{answer:02X}")
                self.ser.write(bytes([answer]))

                v = self.read_byte(wait=False)
                if v == answer:
                    # echo from ecu
                    complete = True
                    break
                elif v == 0x55:
                    # restarted communication
                    continue
                else:
                    # timeout
                    break

        # after connection, we start reading blocks
        res = self.read_ecu_block()
        if res is None:
            return False
        else:
            return True

    def endless_block_reading_loop(self):
        while True:
            for i in range(1, 256):
                print(f"reading group {i}")
                if not self.write_ecu_block(CMD_READ_GROUP, data=[i]):
                    print(f"Failed to write ECU block {CMD_READ_GROUP}")
                    break
                if self.read_ecu_block() is None:
                    print(f"Failed to read ECU block {CMD_READ_GROUP}")
                    break

            if not self.write_ecu_block(CMD_ACK):
                print("Failed to write ECU block")
                break
            if self.read_ecu_block() is None:
                print("Failed to read ECU block")
                break

        return


def main():
    try:

        obd = OBD()


        if not obd.initialize_ecu():
            print("init failed")
            return

        print("init complete")

        obd.endless_block_reading_loop()

        # rx_thread.join(timeout=2)
        # ser.close()

    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    main()
