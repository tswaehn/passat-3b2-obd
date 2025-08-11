//
// Created by tswaehn on 8/11/25.
//

#include <iostream>
#include <iomanip>

#include <thread>
#include <chrono>
#include <stdexcept>

#include "FtdiUart.h"

FtdiUart::FtdiUart(uint16_t vid, uint16_t pid) // FT232R default VID/PID
    : vid_(vid), pid_(pid) {
    ctx_ = ftdi_new();
    if (!ctx_) {
        throw std::runtime_error("ftdi_new failed");
    }

}

FtdiUart::~FtdiUart() {
    close();
}

void FtdiUart::open(int baudrate, int timeout_ms) {

    if (ftdi_usb_open(ctx_, vid_, pid_) < 0) {
        throw std::runtime_error(err("Unable to open FTDI device"));
    }
    is_open = true;

    if (ftdi_usb_reset(ctx_) != 0) {
        throw std::runtime_error("Unable to reset device");
    }

    if (ftdi_set_baudrate(ctx_, baudrate) != 0) {
        throw std::runtime_error("Unable to set baudrate");
    }

    // Default to 8N1 for normal UART I/O
    if (ftdi_set_line_property(ctx_, BITS_8, STOP_BIT_1, NONE) != 0) {
        throw std::runtime_error("Unable to set line properties (8N1)");
    }

    ctx_->usb_read_timeout = timeout_ms;
    ctx_->usb_write_timeout = timeout_ms;
}

void FtdiUart::close() {
    if (ctx_) {
        // Try to restore sane UART settings before closing
        ftdi_set_line_property(ctx_, BITS_8, STOP_BIT_1, NONE);
        if (is_open) {
            ftdi_usb_close(ctx_);
        }
        ftdi_free(ctx_);
    }

    ctx_ = nullptr;
    is_open = false;
}

int FtdiUart::writeData(const std::vector<unsigned char> &data) {
    int n = ftdi_write_data(ctx_, const_cast<unsigned char *>(data.data()), data.size());
    if (n < 0) throw std::runtime_error(err("Write failed"));
    return n;
}

int FtdiUart::readData(std::vector<unsigned char> &buffer) {
    int n = ftdi_read_data(ctx_, buffer.data(), buffer.size());
    if (n < 0) throw std::runtime_error(err("Read failed"));
    return n;
}

// ----- 5-baud init: 7 data bits, Odd parity, 1 stop bit (7O1) -----
// We emulate bits by forcing TX low (BREAK) for '0' and releasing BREAK for '1'.
// BIT duration = 1 / 5 s = 200 ms.
void FtdiUart::send5Baud7O1(uint8_t byte) {
    // Build framed bit sequence: start(0) + 7 data (LSB first) + parity(odd) + stop(1)
    auto bits = framedBits7O1(byte);

    std::cout << "[*] Sending 5Bd 7O1 framed byte 0x"
            << std::hex << std::uppercase << std::setw(2) << std::setfill('0')
            << int(byte) << ": [";
    for (size_t i = 0; i < bits.size(); ++i) {
        std::cout << bits[i] << (i + 1 < bits.size() ? " " : "");
    }
    std::cout << "]\n" << std::dec;

    // Ensure UART is configured for 7O1 while we toggle BREAK (not strictly required,
    // but mirrors the intent and avoids surprising line-state side effects)
    if (ftdi_set_line_property(ctx_, BITS_7, STOP_BIT_1, ODD) != 0)
        throw std::runtime_error("Unable to set line properties (7O1)");

    const auto bit_duration = std::chrono::milliseconds(200); // 5 baud

    for (int b: bits) {
        setBreak(b == 0); // 0 -> BREAK (line low), 1 -> release BREAK (idle high)
        std::this_thread::sleep_for(bit_duration);
    }

    // Return to idle high
    setBreak(false);

    // Restore normal 8N1 UART settings for regular I/O afterwards
    if (ftdi_set_line_property(ctx_, BITS_8, STOP_BIT_1, NONE) != 0)
        throw std::runtime_error("Unable to restore line properties (8N1)");
}


// Toggle BREAK by using line_property2 with BREAK_ON/OFF.
void FtdiUart::setBreak(bool enable) {
    // Keep 7O1 while we’re in this phase (values don’t matter for BREAK_ON,
    // but consistent is nice).
    int rc = ftdi_set_line_property2(ctx_, BITS_7, STOP_BIT_1, ODD, enable ? BREAK_ON : BREAK_OFF);
    if (rc != 0) throw std::runtime_error(err(enable ? "BREAK_ON failed" : "BREAK_OFF failed"));
}

int FtdiUart::parityOdd(uint8_t byte) {
    uint8_t data7 = byte & 0x7F;
    int ones = __builtin_popcount(static_cast<unsigned>(data7));
    // Return parity bit such that total ones (data + parity) is odd.
    return (ones % 2 == 0) ? 1 : 0;
}

std::vector<int> FtdiUart::framedBits7O1(uint8_t byte) {
    std::vector<int> bits;
    bits.reserve(1 + 7 + 1 + 1);
    bits.push_back(0); // start
    for (int i = 0; i < 7; ++i) bits.push_back((byte >> i) & 0x01); // LSB first
    bits.push_back(parityOdd(byte)); // odd parity bit
    bits.push_back(1); // stop
    return bits;
}

std::string FtdiUart::err(const char *prefix) {
    return std::string(prefix) + ": " + ftdi_get_error_string(ctx_);
}
