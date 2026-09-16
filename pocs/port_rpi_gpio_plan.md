# Plano: Port Raspberry Pi GPIO

## Objetivo
Adicionar suporte a GPIO real via `/dev/gpiomem` no target Linux do uFPGA-Emu,
permitindo que a Raspberry Pi toggle pinos físicos como RP2040/ESP32.

## Duração estimada
~1–2 h

## Pré-requisitos

- Raspberry Pi (Zero W, 3, 4, ou 5)
- Raspberry Pi OS (bookworm ou bullseye)
- `gcc` e `make` instalados
- Usuário no grupo `gpio`:
  ```bash
  sudo usermod -a -G gpio $USER
  # re-login ou newgrp gpio
  ```
- Um LED + resistor 330 Ω no GPIO 2 (para teste blinky)

---

## Passo 1 — HAL GPIO: novo bloco `RPI_GPIO`

**Arquivo:** `firmware/lib/hal/src/hal_gpio.c`

Inserir novo `#elif` antes do `#else` final (linha 239).

```c
#elif defined(__linux__) && defined(RPI_GPIO)

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

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

// Offsets in words (not bytes)
#define GPFSEL0   0
#define GPSET0    7   // 0x1C / 4
#define GPCLR0   10   // 0x28 / 4
#define GPLEV0   13   // 0x34 / 4

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
        return;  // fallback: only virtual values work
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
        uint64_t now = hal_cached_now ? hal_cached_now : hal_timer_get_us();
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
```

**Verificação:** Compilar sem `-DRPI_GPIO` — o bloco `__linux__` antigo continua
sendo usado (nada muda para PC).

---

## Passo 2 — main_rpi.c

**Arquivo novo:** `firmware/src/main_rpi.c`

Reaproveita toda a estrutura do `main_esp32.c` com duas diferenças:

1. Entrada `main()` em vez de `app_main()`
2. Loop single-thread com `clock_nanosleep` para clock virtual preciso

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "hal_gpio.h"
#include "hal_timer.h"
#include "emulator.h"
#include "telemetry.h"

// --- #include "circuit_*.c" + pinmap_json ---
// (idêntico ao main_esp32.c, mantendo a cadeia de #elif EMU_CIRCUIT_*)

// Exemplo para blinky (default):
#if defined(EMU_CIRCUIT_BLINKY) || !defined(EMU_CIRCUIT_COUNTER) /* etc */
#include "circuit_blinky.c"
#define CIRCUIT_NAME "blinky"
static const char *pinmap_json =
    "["
    "  {\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},"
    "  {\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},"
    "  {\"name\":\"led\",\"pin\":2,\"bit\":0,\"dir\":\"output\"}"
    "]";
// ... demais #elif ...
#endif

static emulator_config_t emu_cfg;

int main(int argc, char **argv)
{
    (void)argc; (void)argv;

    hal_gpio_init();
    hal_timer_init();
    telemetry_init(115200);

    telemetry_send_string("uFPGA-Emu v1.0 - RPi GPIO (" CIRCUIT_NAME ")\n");

    pin_map_load(&emu_cfg.pin_map, pinmap_json);
    emu_cfg.init_fn  = circuit_init;
    emu_cfg.eval_fn  = circuit_eval;
    emu_cfg.target_freq_hz = 100000;

    emulator_init(&emu_cfg);

    hal_gpio_set_clk(4, 100000);
    hal_gpio_set_virtual(5, 0);  // rst=0

    // Loop com clock_nanosleep para clock virtual preciso
    struct timespec next;
    clock_gettime(CLOCK_MONOTONIC, &next);
    uint32_t period_ns = 1000000000 / emu_cfg.target_freq_hz;

    while (1) {
        emulator_run(&emu_cfg);
        telemetry_receive_cmd(&emu_cfg);
        telemetry_send_state(&emu_cfg);

        next.tv_nsec += period_ns;
        if (next.tv_nsec >= 1000000000) {
           next.tv_sec++;
           next.tv_nsec -= 1000000000;
        }
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL);
    }

    return 0;
}
```

---

## Passo 3 — Compilar e testar na Pi

```bash
# Copiar firmware para a Pi (via scp ou pendrive)
cd ~/ufpga_emu/firmware

# Compilar com RPI_GPIO
gcc -DRPI_GPIO -DEMU_CIRCUIT_BLINKY \
    -Ilib/hal/include -Ilib/runtime/include \
    src/main_rpi.c \
    lib/hal/src/hal_gpio.c lib/hal/src/hal_timer.c \
    lib/hal/src/hal_serial.c lib/runtime/src/*.c \
    -o ufpga_emu -lm

# Verificar grupo gpio
groups | grep gpio || echo "Usuário não está no grupo gpio"

# Conectar LED no GPIO 2 (físico pino 3) com resistor 330 Ω para GND

# Executar
./ufpga_emu
```

**Esperado:** LED piscando no GPIO 2, terminal mostra telemetria, comandos
`vset`/`status`/`read`/`reset` funcionam via stdin.

---

## Passo 4 — Testar sem `-DRPI_GPIO`

```bash
gcc -DEMU_CIRCUIT_BLINKY \
    -Ilib/hal/include -Ilib/runtime/include \
    src/main_rpi.c \
    lib/hal/src/hal_gpio.c lib/hal/src/hal_timer.c \
    lib/hal/src/hal_serial.c lib/runtime/src/*.c \
    -o ufpga_emu_virtual -lm

./ufpga_emu_virtual
```

**Esperado:** roda normal, mas sem togglar GPIO físico (falls back para virtual).

---

## Passo 5 — Verificar VCD

O VCD writer já funciona em Linux, mas usa `stdout` em vez de arquivo. Para gravar
em arquivo no SD, ajustar `vcd_writer.c` para receber um `FILE *`:

```c
// Em vez de write(STDOUT_FILENO, ...):
if (vcd->file)
    fwrite(buf, 1, len, vcd->file);
```

E no main:
```c
vcd_writer_t vcd;
vcd_writer_init(&vcd, &emu_cfg.pin_map);
vcd.file = fopen("trace.vcd", "w");
emu_cfg.vcd = &vcd;
```

---

## Passo 6 — Benchmark rápido

```bash
# Medir quantos ciclos de emulação em 10 segundos
# (adicionar contador no emulator_run e imprimir ao sair com Ctrl+C)
```

Virtual clock esperado: **100–500 kHz** no Pi Zero W, **1–2 MHz** no Pi 4.

---

## Entregáveis

- [ ] `hal_gpio.c`: novo bloco `RPI_GPIO` inserido
- [ ] `main_rpi.c`: novo arquivo com `main()` + pinmaps (+ ajuste de #elif)
- [ ] `firmware/Makefile` (ou script `build_rpi.sh`): comando de compilação
- [ ] Teste blinky: LED pisca no GPIO 2
- [ ] Teste counter: LEDs contam no GPIO 12-15
- [ ] Teste fallback: sem `-DRPI_GPIO` roda virtual
