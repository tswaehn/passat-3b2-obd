cmake_minimum_required(VERSION 3.10)
project(passat_3b2_obd CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBFTDI1 REQUIRED libftdi)
pkg_check_modules(LIBUSB REQUIRED libusb-1.0)

add_executable(${PROJECT_NAME}
        main.cpp
        FtdiUart.cpp
)

target_include_directories(${PROJECT_NAME} PRIVATE
        ${LIBFTDI1_INCLUDE_DIRS}
        ${LIBUSB_INCLUDE_DIRS}
)

target_link_libraries(${PROJECT_NAME}
        ${LIBFTDI1_LIBRARIES}
        ${LIBUSB_LIBRARIES}
)

# Ensure pkg-config paths are added for runtime
target_link_directories(${PROJECT_NAME} PRIVATE
        ${LIBFTDI1_LIBRARY_DIRS}
        ${LIBUSB_LIBRARY_DIRS}
)
