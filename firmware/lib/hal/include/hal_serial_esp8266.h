#ifndef HAL_SERIAL_ESP8266_H
#define HAL_SERIAL_ESP8266_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

void hal_serial_esp8266_init(uint32_t baud);
void hal_serial_esp8266_send_byte(uint8_t data);
void hal_serial_esp8266_send_buffer(const uint8_t *data, size_t len);
int  hal_serial_esp8266_receive_byte(uint8_t *data);

#ifdef __cplusplus
}
#endif

#endif
