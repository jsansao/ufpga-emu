#ifndef HAL_TIMER_H
#define HAL_TIMER_H

#include <stdint.h>

void     hal_timer_init(void);
uint64_t hal_timer_get_us(void);
void     hal_timer_delay_us(uint32_t us);
void     hal_timer_yield(void);

#endif
