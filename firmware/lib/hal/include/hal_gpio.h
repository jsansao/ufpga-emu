#ifndef HAL_GPIO_H
#define HAL_GPIO_H

#include <stdint.h>

typedef enum {
    HAL_GPIO_INPUT,
    HAL_GPIO_OUTPUT
} hal_gpio_mode_t;

void     hal_gpio_init(void);
void     hal_gpio_set_mode(uint8_t pin, hal_gpio_mode_t mode);
uint8_t  hal_gpio_read(uint8_t pin);
void     hal_gpio_write(uint8_t pin, uint8_t value);

void     hal_gpio_set_clk(uint8_t pin, uint32_t freq_hz);
void     hal_gpio_set_virtual(uint8_t pin, uint8_t value);
void     hal_gpio_set_cached_now(uint64_t now_us);

#endif
