#include "hal_timer.h"

#if defined(ESP_PLATFORM)

#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void hal_timer_init(void)
{
}

uint64_t hal_timer_get_us(void)
{
    return (uint64_t)esp_timer_get_time();
}

void hal_timer_delay_us(uint32_t us)
{
    if (us >= 10000) {
        vTaskDelay(us / 1000 / portTICK_PERIOD_MS);
    } else {
        uint64_t start = hal_timer_get_us();
        while ((hal_timer_get_us() - start) < us) { }
    }
}

void hal_timer_yield(void)
{
    vTaskDelay(1);
}

#elif defined(ARDUINO_ARCH_RP2040)

#include "hardware/timer.h"
#include "hardware/sync.h"

void hal_timer_init(void)
{
}

uint64_t hal_timer_get_us(void)
{
    return time_us_64();
}

void hal_timer_delay_us(uint32_t us)
{
    busy_wait_us(us);
}

void hal_timer_yield(void)
{
    tight_loop_contents();
}

#elif defined(ARDUINO_ARCH_ESP8266)

#include <Arduino.h>

void hal_timer_init(void)
{
}

uint64_t hal_timer_get_us(void)
{
    return micros();
}

void hal_timer_delay_us(uint32_t us)
{
    delayMicroseconds(us);
}

void hal_timer_yield(void)
{
    optimistic_yield(0);
}

#elif defined(ARDUINO_ARCH_SAM)

#include <Arduino.h>

void hal_timer_init(void)
{
}

uint64_t hal_timer_get_us(void)
{
    return micros();
}

void hal_timer_delay_us(uint32_t us)
{
    delayMicroseconds(us);
}

void hal_timer_yield(void)
{
}

#elif defined(__linux__)

#include <time.h>
#include <sched.h>

void hal_timer_init(void)
{
}

uint64_t hal_timer_get_us(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000ULL + (uint64_t)ts.tv_nsec / 1000;
}

void hal_timer_delay_us(uint32_t us)
{
    struct timespec ts = {
        .tv_sec = (time_t)(us / 1000000),
        .tv_nsec = (long)((us % 1000000) * 1000)
    };
    nanosleep(&ts, NULL);
}

void hal_timer_yield(void)
{
    sched_yield();
}

#else
#error "hal_timer.c: no platform defined (expected ESP_PLATFORM, ARDUINO_ARCH_RP2040, ARDUINO_ARCH_ESP8266, ARDUINO_ARCH_SAM, or __linux__)"
#endif
