#include "hal_gpio.h"

#if defined(ESP_PLATFORM)

#include "driver/gpio.h"
#include "hal_timer.h"

#define HAL_GPIO_MAX_PINS 40

static struct {
    uint8_t  clk_pin;
    uint8_t  state;
    uint64_t last_us;
    uint32_t half_period_us;
    uint8_t  initialized;
} mcu_clk;

static int8_t virtual_values[HAL_GPIO_MAX_PINS];

static uint64_t hal_cached_now = 0;

void hal_gpio_set_cached_now(uint64_t now_us)
{
    hal_cached_now = now_us;
}

void hal_gpio_init(void)
{
    mcu_clk.initialized = 0;
    for (int i = 0; i < HAL_GPIO_MAX_PINS; i++)
        virtual_values[i] = -1;
}

void hal_gpio_set_virtual(uint8_t pin, uint8_t value)
{
    if (pin < HAL_GPIO_MAX_PINS)
        virtual_values[pin] = value ? 1 : 0;
}

void hal_gpio_set_clk(uint8_t pin, uint32_t freq_hz)
{
    mcu_clk.clk_pin = pin;
    mcu_clk.state = 0;
    mcu_clk.last_us = hal_timer_get_us();
    mcu_clk.half_period_us = (freq_hz > 0) ? (500000u / freq_hz) : 0;
    mcu_clk.initialized = 1;
}

void hal_gpio_set_mode(uint8_t pin, hal_gpio_mode_t mode)
{
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << pin),
        .mode = (mode == HAL_GPIO_INPUT) ? GPIO_MODE_INPUT : GPIO_MODE_OUTPUT,
        .pull_up_en = (mode == HAL_GPIO_INPUT) ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&cfg);
}

uint8_t hal_gpio_read(uint8_t pin)
{
    if (pin < HAL_GPIO_MAX_PINS && virtual_values[pin] >= 0)
        return (uint8_t)virtual_values[pin];

    if (mcu_clk.initialized && pin == mcu_clk.clk_pin) {
        uint64_t now = hal_cached_now ? hal_cached_now : hal_timer_get_us();
        if (mcu_clk.half_period_us > 0 &&
            (now - mcu_clk.last_us) >= mcu_clk.half_period_us) {
            mcu_clk.state ^= 1;
            mcu_clk.last_us = now;
        }
        return mcu_clk.state;
    }
    return (uint8_t)gpio_get_level(pin);
}

void hal_gpio_write(uint8_t pin, uint8_t value)
{
    gpio_set_level(pin, value);
}

#elif defined(ARDUINO_ARCH_RP2040)

#include "hardware/gpio.h"
#include "hal_timer.h"

#define HAL_GPIO_MAX_PINS 30

static struct {
    uint8_t  clk_pin;
    uint8_t  state;
    uint64_t last_us;
    uint32_t half_period_us;
    uint8_t  initialized;
} rp_clk;

static int8_t virtual_values[HAL_GPIO_MAX_PINS];

static uint64_t hal_cached_now = 0;

void hal_gpio_set_cached_now(uint64_t now_us)
{
    hal_cached_now = now_us;
}

void hal_gpio_init(void)
{
    rp_clk.initialized = 0;
    for (int i = 0; i < HAL_GPIO_MAX_PINS; i++)
        virtual_values[i] = -1;
}

void hal_gpio_set_clk(uint8_t pin, uint32_t freq_hz)
{
    rp_clk.clk_pin = pin;
    rp_clk.state = 0;
    rp_clk.last_us = hal_timer_get_us();
    rp_clk.half_period_us = (freq_hz > 0) ? (500000u / freq_hz) : 0;
    rp_clk.initialized = 1;
}

void hal_gpio_set_virtual(uint8_t pin, uint8_t value)
{
    if (pin < HAL_GPIO_MAX_PINS)
        virtual_values[pin] = value ? 1 : 0;
}

void hal_gpio_set_mode(uint8_t pin, hal_gpio_mode_t mode)
{
    gpio_set_function(pin, GPIO_FUNC_SIO);
    gpio_set_dir(pin, mode == HAL_GPIO_OUTPUT);
    gpio_set_pulls(pin, mode == HAL_GPIO_INPUT, false);
}

uint8_t hal_gpio_read(uint8_t pin)
{
    if (pin < HAL_GPIO_MAX_PINS && virtual_values[pin] >= 0)
        return (uint8_t)virtual_values[pin];

    if (rp_clk.initialized && pin == rp_clk.clk_pin) {
        uint64_t now = hal_cached_now ? hal_cached_now : hal_timer_get_us();
        if (rp_clk.half_period_us > 0 &&
            (now - rp_clk.last_us) >= rp_clk.half_period_us) {
            rp_clk.state ^= 1;
            rp_clk.last_us = now;
        }
        return rp_clk.state;
    }
    return gpio_get(pin) ? 1 : 0;
}

void hal_gpio_write(uint8_t pin, uint8_t value)
{
    gpio_put(pin, value ? 1 : 0);
}

#elif defined(ARDUINO_ARCH_ESP8266)

#include <Arduino.h>
#include "hal_timer.h"

/* MAX_PINS=40 to match pinmaps (virtual pins up to 39).
   Physical GPIOs: 0-5,12-16 (11 pins). Pins >=17 are virtual only. */
#define HAL_GPIO_MAX_PINS 40
#define HAL_GPIO_PHYSICAL_PINS 17

static struct {
    uint8_t  clk_pin;
    uint8_t  state;
    uint64_t last_us;
    uint32_t half_period_us;
    uint8_t  initialized;
} esp8266_clk;

static int8_t virtual_values[HAL_GPIO_MAX_PINS];

static uint64_t hal_cached_now = 0;

void hal_gpio_set_cached_now(uint64_t now_us)
{
    hal_cached_now = now_us;
}

void hal_gpio_init(void)
{
    esp8266_clk.initialized = 0;
    for (int i = 0; i < HAL_GPIO_MAX_PINS; i++)
        virtual_values[i] = -1;
}

void hal_gpio_set_clk(uint8_t pin, uint32_t freq_hz)
{
    esp8266_clk.clk_pin = pin;
    esp8266_clk.state = 0;
    esp8266_clk.last_us = hal_timer_get_us();
    esp8266_clk.half_period_us = (freq_hz > 0) ? (500000u / freq_hz) : 0;
    esp8266_clk.initialized = 1;
}

void hal_gpio_set_virtual(uint8_t pin, uint8_t value)
{
    if (pin < HAL_GPIO_MAX_PINS)
        virtual_values[pin] = value ? 1 : 0;
}

void hal_gpio_set_mode(uint8_t pin, hal_gpio_mode_t mode)
{
    if (pin >= HAL_GPIO_PHYSICAL_PINS) return;
    pinMode(pin, (mode == HAL_GPIO_INPUT) ? INPUT_PULLUP : OUTPUT);
}

uint8_t hal_gpio_read(uint8_t pin)
{
    if (pin < HAL_GPIO_MAX_PINS && virtual_values[pin] >= 0)
        return (uint8_t)virtual_values[pin];

    if (esp8266_clk.initialized && pin == esp8266_clk.clk_pin) {
        uint64_t now = hal_cached_now ? hal_cached_now : hal_timer_get_us();
        if (esp8266_clk.half_period_us > 0 &&
            (now - esp8266_clk.last_us) >= esp8266_clk.half_period_us) {
            esp8266_clk.state ^= 1;
            esp8266_clk.last_us = now;
        }
        return esp8266_clk.state;
    }
    if (pin >= HAL_GPIO_PHYSICAL_PINS) return 0;
    return (uint8_t)digitalRead(pin);
}

void hal_gpio_write(uint8_t pin, uint8_t value)
{
    if (pin >= HAL_GPIO_PHYSICAL_PINS) return;
    digitalWrite(pin, value ? HIGH : LOW);
}

#elif defined(ARDUINO_ARCH_SAM)

#include <Arduino.h>
#include "hal_timer.h"

#define HAL_GPIO_MAX_PINS 54

static struct {
    uint8_t  clk_pin;
    uint8_t  state;
    uint64_t last_us;
    uint32_t half_period_us;
    uint8_t  initialized;
} due_clk;

static int8_t virtual_values[HAL_GPIO_MAX_PINS];

static uint64_t hal_cached_now = 0;

void hal_gpio_set_cached_now(uint64_t now_us)
{
    hal_cached_now = now_us;
}

void hal_gpio_init(void)
{
    due_clk.initialized = 0;
    for (int i = 0; i < HAL_GPIO_MAX_PINS; i++)
        virtual_values[i] = -1;
}

void hal_gpio_set_clk(uint8_t pin, uint32_t freq_hz)
{
    due_clk.clk_pin = pin;
    due_clk.state = 0;
    due_clk.last_us = hal_timer_get_us();
    due_clk.half_period_us = (freq_hz > 0) ? (500000u / freq_hz) : 0;
    due_clk.initialized = 1;
}

void hal_gpio_set_virtual(uint8_t pin, uint8_t value)
{
    if (pin < HAL_GPIO_MAX_PINS)
        virtual_values[pin] = value ? 1 : 0;
}

void hal_gpio_set_mode(uint8_t pin, hal_gpio_mode_t mode)
{
    pinMode(pin, (mode == HAL_GPIO_INPUT) ? INPUT_PULLUP : OUTPUT);
}

uint8_t hal_gpio_read(uint8_t pin)
{
    if (pin < HAL_GPIO_MAX_PINS && virtual_values[pin] >= 0)
        return (uint8_t)virtual_values[pin];

    if (due_clk.initialized && pin == due_clk.clk_pin) {
        uint64_t now = hal_cached_now ? hal_cached_now : hal_timer_get_us();
        if (due_clk.half_period_us > 0 &&
            (now - due_clk.last_us) >= due_clk.half_period_us) {
            due_clk.state ^= 1;
            due_clk.last_us = now;
        }
        return due_clk.state;
    }
    return (uint8_t)digitalRead(pin);
}

void hal_gpio_write(uint8_t pin, uint8_t value)
{
    digitalWrite(pin, value ? HIGH : LOW);
}

#elif defined(__linux__) && defined(RPI_GPIO)

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include "hal_timer.h"

#define HAL_GPIO_MAX_PINS 28

static struct {
    uint8_t  clk_pin;
    uint8_t  state;
    uint64_t last_us;
    uint32_t half_period_us;
    uint8_t  initialized;
} rpi_clk;

static int8_t virtual_values[HAL_GPIO_MAX_PINS];
static uint64_t hal_cached_now = 0;

static volatile uint32_t *gpio_regs = NULL;
static int gpiomem_fd = -1;

#define GPFSEL0   0
#define GPSET0    7
#define GPCLR0   10
#define GPLEV0   13

void hal_gpio_set_cached_now(uint64_t now_us)
{
    hal_cached_now = now_us;
}

void hal_gpio_init(void)
{
    rpi_clk.initialized = 0;
    for (int i = 0; i < HAL_GPIO_MAX_PINS; i++)
        virtual_values[i] = -1;

    gpiomem_fd = open("/dev/gpiomem", O_RDWR | O_SYNC);
    if (gpiomem_fd < 0)
        return;
    gpio_regs = (volatile uint32_t *)mmap(
        NULL, 0x1000,
        PROT_READ | PROT_WRITE, MAP_SHARED,
        gpiomem_fd, 0);
    if (gpio_regs == MAP_FAILED) {
        gpio_regs = NULL;
        close(gpiomem_fd);
        gpiomem_fd = -1;
    }
}

void hal_gpio_set_clk(uint8_t pin, uint32_t freq_hz)
{
    rpi_clk.clk_pin = pin;
    rpi_clk.state = 0;
    rpi_clk.last_us = hal_timer_get_us();
    rpi_clk.half_period_us = (freq_hz > 0) ? (500000u / freq_hz) : 0;
    rpi_clk.initialized = 1;
}

void hal_gpio_set_virtual(uint8_t pin, uint8_t value)
{
    if (pin < HAL_GPIO_MAX_PINS)
        virtual_values[pin] = value ? 1 : 0;
}

void hal_gpio_set_mode(uint8_t pin, hal_gpio_mode_t mode)
{
    if (pin >= HAL_GPIO_MAX_PINS || !gpio_regs) return;
    int reg = pin / 10;
    int bit = (pin % 10) * 3;
    uint32_t v = gpio_regs[GPFSEL0 + reg];
    v &= ~(7u << bit);
    v |= ((mode == HAL_GPIO_OUTPUT ? 1u : 0u) << bit);
    gpio_regs[GPFSEL0 + reg] = v;
}

uint8_t hal_gpio_read(uint8_t pin)
{
    if (pin >= HAL_GPIO_MAX_PINS) return 0;

    if (virtual_values[pin] >= 0)
        return (uint8_t)virtual_values[pin];

    if (rpi_clk.initialized && pin == rpi_clk.clk_pin) {
        uint64_t now = hal_cached_now ? hal_cached_now : (uint64_t)hal_timer_get_us();
        if (rpi_clk.half_period_us > 0 &&
            (now - rpi_clk.last_us) >= rpi_clk.half_period_us) {
            rpi_clk.state ^= 1;
            rpi_clk.last_us = now;
        }
        return rpi_clk.state;
    }

    if (!gpio_regs) return 0;
    return (gpio_regs[GPLEV0] >> pin) & 1u;
}

void hal_gpio_write(uint8_t pin, uint8_t value)
{
    if (pin >= HAL_GPIO_MAX_PINS) return;
    virtual_values[pin] = value ? 1 : 0;
    if (!gpio_regs) return;
    if (value)
        gpio_regs[GPSET0] = (1u << pin);
    else
        gpio_regs[GPCLR0] = (1u << pin);
}

#elif defined(__linux__)

#include <stdint.h>
#include <string.h>
#include "hal_timer.h"
#include "hal_stimulus.h"

#define HAL_GPIO_MAX_PINS 64

static struct {
    uint8_t  clk_pin;
    uint8_t  state;
    uint64_t last_us;
    uint32_t half_period_us;
    uint8_t  initialized;
} pc_clk;

static int8_t virtual_values[HAL_GPIO_MAX_PINS];

static uint64_t hal_cached_now = 0;

void hal_gpio_set_cached_now(uint64_t now_us)
{
    hal_cached_now = now_us;
}

void hal_gpio_init(void)
{
    pc_clk.initialized = 0;
    memset(virtual_values, -1, sizeof(virtual_values));
}

void hal_gpio_set_clk(uint8_t pin, uint32_t freq_hz)
{
    pc_clk.clk_pin = pin;
    pc_clk.state = 0;
    pc_clk.last_us = hal_timer_get_us();
    pc_clk.half_period_us = (freq_hz > 0) ? (500000u / freq_hz) : 0;
    pc_clk.initialized = 1;
}

void hal_gpio_set_mode(uint8_t pin, hal_gpio_mode_t mode)
{
    (void)pin;
    (void)mode;
}

void hal_gpio_set_virtual(uint8_t pin, uint8_t value)
{
    if (pin < HAL_GPIO_MAX_PINS)
        virtual_values[pin] = value ? 1 : 0;
}

uint8_t hal_gpio_read(uint8_t pin)
{
    uint64_t now = hal_timer_get_us();

    if (pin < HAL_GPIO_MAX_PINS && virtual_values[pin] >= 0)
        return (uint8_t)virtual_values[pin];

    int stim = hal_stimulus_get(pin, now);
    if (stim >= 0) return (uint8_t)stim;

    if (pc_clk.initialized && pin == pc_clk.clk_pin) {
        if (pc_clk.half_period_us > 0 &&
            (now - pc_clk.last_us) >= pc_clk.half_period_us) {
            pc_clk.state ^= 1;
            pc_clk.last_us = now;
        }
        return pc_clk.state;
    }
    (void)now;
    return 0;
}

void hal_gpio_write(uint8_t pin, uint8_t value)
{
    (void)pin;
    (void)value;
}

#else
#error "hal_gpio.c: no platform defined (expected ESP_PLATFORM, ARDUINO_ARCH_RP2040, ARDUINO_ARCH_ESP8266, ARDUINO_ARCH_SAM, __linux__, or __linux__+RPI_GPIO)"
#endif
