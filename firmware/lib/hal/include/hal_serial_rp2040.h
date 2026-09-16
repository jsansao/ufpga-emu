#ifndef HAL_SERIAL_RP2040_H
#define HAL_SERIAL_RP2040_H

#include <stdint.h>
#include <stddef.h>

void hal_serial_rp2040_init(uint32_t baud);
void hal_serial_rp2040_send_byte(uint8_t data);
void hal_serial_rp2040_send_buffer(const uint8_t *data, size_t len);
int  hal_serial_rp2040_receive_byte(uint8_t *data);

#endif