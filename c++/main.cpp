//
// Created by tswaehn on 8/11/25.
//

#include <iostream>

#include "FtdiUart.h"

int main() {
    try {
        FtdiUart uart;
        uart.open(115200, 500); // normal UART settings for read/write

        // Write example
        std::string msg = "Hello FTDI\n";
        std::vector<unsigned char> out(msg.begin(), msg.end());
        uart.writeData(out);

        // Read example
        std::vector<unsigned char> in(256);
        int n = uart.readData(in);
        if (n > 0) {
            std::cout << "Received: " << std::string(in.begin(), in.begin() + n) << "\n";
        } else {
            std::cout << "No data (timeout)\n";
        }

        // 5-baud init example: send address 0x33 (or any byte you need)
        uart.send5Baud7O1(0x33);

        uart.close();

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
