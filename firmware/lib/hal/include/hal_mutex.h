#ifndef HAL_MUTEX_H
#define HAL_MUTEX_H

#include <stdint.h>

#if defined(ESP_PLATFORM)

struct hal_mutex {
    volatile int lock;
};

#elif defined(ARDUINO_ARCH_RP2040)

#include "hardware/sync.h"

struct hal_mutex {
    spin_lock_t *lock;
    uint32_t saved;
};

#elif defined(ARDUINO_ARCH_ESP8266)

struct hal_mutex {
    int _unused;
};

#elif defined(ARDUINO_ARCH_SAM)

struct hal_mutex {
    int _unused;
};

#elif defined(__linux__)

#include <pthread.h>

struct hal_mutex {
    pthread_mutex_t lock;
};

#else

struct hal_mutex {
    int _unused;
};

#endif

typedef struct hal_mutex hal_mutex_t;

void     hal_mutex_init(hal_mutex_t *mutex);
void     hal_mutex_lock(hal_mutex_t *mutex);
void     hal_mutex_unlock(hal_mutex_t *mutex);

#endif
