#include "hal_mutex.h"

#if defined(ESP_PLATFORM)

void hal_mutex_init(hal_mutex_t *mutex)
{
    mutex->lock = 0;
}

void hal_mutex_lock(hal_mutex_t *mutex)
{
    while (__sync_lock_test_and_set(&mutex->lock, 1)) {
        /* spin */
    }
}

void hal_mutex_unlock(hal_mutex_t *mutex)
{
    __sync_lock_release(&mutex->lock);
}

#elif defined(ARDUINO_ARCH_RP2040)

void hal_mutex_init(hal_mutex_t *mutex)
{
    mutex->lock = spin_lock_init(PICO_SPINLOCK_ID_EMU);
}

void hal_mutex_lock(hal_mutex_t *mutex)
{
    mutex->saved = spin_lock_blocking(mutex->lock);
}

void hal_mutex_unlock(hal_mutex_t *mutex)
{
    spin_unlock(mutex->lock, mutex->saved);
}

#elif defined(ARDUINO_ARCH_ESP8266)

void hal_mutex_init(hal_mutex_t *mutex)
{
    (void)mutex;
}

void hal_mutex_lock(hal_mutex_t *mutex)
{
    (void)mutex;
}

void hal_mutex_unlock(hal_mutex_t *mutex)
{
    (void)mutex;
}

#elif defined(ARDUINO_ARCH_SAM)

void hal_mutex_init(hal_mutex_t *mutex)
{
    (void)mutex;
}

void hal_mutex_lock(hal_mutex_t *mutex)
{
    (void)mutex;
}

void hal_mutex_unlock(hal_mutex_t *mutex)
{
    (void)mutex;
}

#elif defined(__linux__)

void hal_mutex_init(hal_mutex_t *mutex)
{
    pthread_mutex_init(&mutex->lock, NULL);
}

void hal_mutex_lock(hal_mutex_t *mutex)
{
    pthread_mutex_lock(&mutex->lock);
}

void hal_mutex_unlock(hal_mutex_t *mutex)
{
    pthread_mutex_unlock(&mutex->lock);
}

#else
#error "hal_mutex.c: no platform defined (expected ESP_PLATFORM, ARDUINO_ARCH_RP2040, ARDUINO_ARCH_ESP8266, ARDUINO_ARCH_SAM, or __linux__)"
#endif
