#ifndef HAL_SERIAL_H
#define HAL_SERIAL_H

#include <stdint.h>
#include <stddef.h>

void     hal_serial_init(uint32_t baud);
void     hal_serial_send_byte(uint8_t data);
void     hal_serial_send_buffer(const uint8_t *data, size_t len);
int      hal_serial_receive_byte(uint8_t *data);

#endif
