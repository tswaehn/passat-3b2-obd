//
// Created by tswaehn on 8/11/25.
//

#ifndef PASSAT_3B2_OBD_FTDIUART_H
#define PASSAT_3B2_OBD_FTDIUART_H

#include <ftdi.h>
#include <string>
#include <vector>


class FtdiUart {
public:
    FtdiUart(uint16_t vid = 0x0403, uint16_t pid = 0x6001);

    ~FtdiUart();

    void open(int baudrate, int timeout_ms);
    void close();

    int writeData(const std::vector<unsigned char>& data);

    int readData(std::vector<unsigned char>& buffer);

    // ----- 5-baud init: 7 data bits, Odd parity, 1 stop bit (7O1) -----
    // We emulate bits by forcing TX low (BREAK) for '0' and releasing BREAK for '1'.
    // BIT duration = 1 / 5 s = 200 ms.
    void send5Baud7O1(uint8_t byte);

private:

    struct ftdi_context* ctx_ = nullptr;
    uint16_t vid_, pid_;
    bool is_open = false;

    // Toggle BREAK by using line_property2 with BREAK_ON/OFF.
    void setBreak(bool enable);

    static int parityOdd(uint8_t byte);

    static std::vector<int> framedBits7O1(uint8_t byte);

    std::string err(const char* prefix);

};


#endif //PASSAT_3B2_OBD_FTDIUART_H