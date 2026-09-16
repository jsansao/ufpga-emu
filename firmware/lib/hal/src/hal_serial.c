#include "hal_serial.h"

#if defined(ESP_PLATFORM)

#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define UART_NUM UART_NUM_0
#define BUF_SIZE 256

static bool initialized = false;

void hal_serial_init(uint32_t baud)
{
    if (initialized) return;
    uart_config_t cfg = {
        .baud_rate = (int)baud,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE
    };
    uart_param_config(UART_NUM, &cfg);
    uart_set_pin(UART_NUM, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(UART_NUM, BUF_SIZE, 0, 0, NULL, 0);
    initialized = true;
}

void hal_serial_send_byte(uint8_t data)
{
    uart_write_bytes(UART_NUM, (const char *)&data, 1);
}

void hal_serial_send_buffer(const uint8_t *data, size_t len)
{
    uart_write_bytes(UART_NUM, (const char *)data, len);
}

int hal_serial_receive_byte(uint8_t *data)
{
    int len = uart_read_bytes(UART_NUM, data, 1, 0);
    return (len > 0) ? 0 : -1;
}

#elif defined(ARDUINO_ARCH_RP2040)

#include <stdbool.h>
#include "hal_serial_rp2040.h"

static bool initialized = false;

void hal_serial_init(uint32_t baud)
{
    if (initialized) return;
    hal_serial_rp2040_init(baud);
    initialized = true;
}

void hal_serial_send_byte(uint8_t data)
{
    hal_serial_rp2040_send_byte(data);
}

void hal_serial_send_buffer(const uint8_t *data, size_t len)
{
    hal_serial_rp2040_send_buffer(data, len);
}

int hal_serial_receive_byte(uint8_t *data)
{
    return hal_serial_rp2040_receive_byte(data);
}

#elif defined(ARDUINO_ARCH_ESP8266)

#include "hal_serial_esp8266.h"

void hal_serial_init(uint32_t baud)
{
    hal_serial_esp8266_init(baud);
}

void hal_serial_send_byte(uint8_t data)
{
    hal_serial_esp8266_send_byte(data);
}

void hal_serial_send_buffer(const uint8_t *data, size_t len)
{
    hal_serial_esp8266_send_buffer(data, len);
}

int hal_serial_receive_byte(uint8_t *data)
{
    return hal_serial_esp8266_receive_byte(data);
}

#elif defined(ARDUINO_ARCH_SAM)

#include "hal_serial_due.h"

void hal_serial_init(uint32_t baud)
{
    hal_serial_due_init(baud);
}

void hal_serial_send_byte(uint8_t data)
{
    hal_serial_due_send_byte(data);
}

void hal_serial_send_buffer(const uint8_t *data, size_t len)
{
    hal_serial_due_send_buffer(data, len);
}

int hal_serial_receive_byte(uint8_t *data)
{
    return hal_serial_due_receive_byte(data);
}

#elif defined(__linux__)

#include <unistd.h>
#include <termios.h>
#include <stdio.h>
#include <stdbool.h>

static struct termios old_tio;
static bool initialized = false;

void hal_serial_init(uint32_t baud)
{
    if (initialized) return;
    (void)baud;
    struct termios new_tio;
    tcgetattr(STDIN_FILENO, &old_tio);
    new_tio = old_tio;
    cfmakeraw(&new_tio);
    tcsetattr(STDIN_FILENO, TCSANOW, &new_tio);
    initialized = true;
}

void hal_serial_send_byte(uint8_t data)
{
    write(STDOUT_FILENO, &data, 1);
}

void hal_serial_send_buffer(const uint8_t *data, size_t len)
{
    write(STDOUT_FILENO, data, len);
}

int hal_serial_receive_byte(uint8_t *data)
{
    int ret = (int)read(STDIN_FILENO, data, 1);
    return (ret > 0) ? 0 : -1;
}

#else
#error "hal_serial.c: no platform defined (expected ESP_PLATFORM, ARDUINO_ARCH_RP2040, ARDUINO_ARCH_ESP8266, ARDUINO_ARCH_SAM, or __linux__)"
#endif
