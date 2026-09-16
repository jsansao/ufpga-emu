# Portabilidade para Raspberry Pi (Zero W / Linux com GPIO)

> Consulta: como rodar o uFPGA-Emu em uma Raspberry Pi, com acesso a GPIO real?

---

## 1. Estado atual

O firmware já compila e roda em qualquer Linux com `__linux__` + `main_pc.c`. A HAL atual
(`hal_gpio.c` linhas 158–237) trata GPIO físico como **no-op**:

```c
void hal_gpio_set_mode(...) { (void)pin; (void)mode; }
void hal_gpio_write(...)    { (void)pin; (void)value; }
uint8_t hal_gpio_read(...)  { ... return 0; }  // só virtual + clock
```

Tudo funciona: virtual_values, clock virtual, telemetria, VCD.
Mas **nenhum pino físico toggla**.

---

## 2. Adicionar GPIO real via `/dev/gpiomem`

O BCM2835 (Pi Zero W) expõe os registros GPIO via `/dev/gpiomem` — sem root, sem daemon,
sem bibliotecas externas. Basta `open` + `mmap`.

### hal_gpio.c — novo bloco `__linux__ && RPI_GPIO`

```c
#elif defined(__linux__) && defined(RPI_GPIO)

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

#define HAL_GPIO_MAX_PINS 28   // BCM 0-27 (26 úteis)

static volatile uint32_t *gpio_regs = NULL;
static int gpiomem_fd = -1;

// Offsets em words (não bytes)
#define GPFSEL0   0   // 0x00 / 4
#define GPSET0    7   // 0x1C / 4
#define GPCLR0   10   // 0x28 / 4
#define GPLEV0   13   // 0x34 / 4
#define GPPUD    37   // 0x94 / 4
#define GPPUDCLK 38   // 0x98 / 4

void hal_gpio_init(void) {
    // ... inicializa virtual_values = -1 ...
    gpiomem_fd = open("/dev/gpiomem", O_RDWR | O_SYNC);
    if (gpiomem_fd < 0) return;  // fallback virtual
    gpio_regs = (volatile uint32_t *)mmap(
        NULL, 0x1000,
        PROT_READ | PROT_WRITE, MAP_SHARED,
        gpiomem_fd, 0);
}

void hal_gpio_set_mode(uint8_t pin, hal_gpio_mode_t mode) {
    if (!gpio_regs) return;
    int reg = pin / 10;
    int bit = (pin % 10) * 3;
    uint32_t v = gpio_regs[GPFSEL0 + reg];
    v &= ~(7u << bit);
    v |= ((mode == HAL_GPIO_OUTPUT ? 1u : 0u) << bit);
    gpio_regs[GPFSEL0 + reg] = v;
}

void hal_gpio_write(uint8_t pin, uint8_t value) {
    if (!gpio_regs) return;
    if (value) gpio_regs[GPSET0] = (1u << pin);
    else       gpio_regs[GPCLR0] = (1u << pin);
    virtual_values[pin] = value ? 1 : 0;
}

uint8_t hal_gpio_read(uint8_t pin) {
    if (pin < HAL_GPIO_MAX_PINS && virtual_values[pin] >= 0)
        return (uint8_t)virtual_values[pin];
    // clock virtual... (mesma lógica das outras plataformas)
    if (!gpio_regs) return 0;
    return (gpio_regs[GPLEV0] >> pin) & 1u;
}
```

**Vantagens:**
- zero dependências externas
- acesso direto a registros (mais rápido que `sysfs` ou `libgpiod`)
- mesmo código em Pi Zero, 3, 4, 5 (`/dev/gpiomem` isola o layout do hardware)

### Fallback

Se `/dev/gpiomem` não existir (compilou sem Pi, ou sem permissão), `open()` falha,
`gpio_regs` fica NULL, e todo GPIO opera via virtual_values — o firmware roda igual.

---

## 3. main_rpi.c

Reaproveita `main_pc.c` com uma diferença: o loop pode usar `clock_nanosleep` com
`TIMER_ABSTIME` para clock virtual mais preciso que busy-wait.

```c
#include "hal_gpio.h"
#include "hal_timer.h"
#include "emulator.h"
#include "telemetry.h"

// #include "circuit_*.c" + pinmap_json (igual ao main_esp32.c)

int main(void) {
    hal_gpio_init();
    hal_timer_init();
    telemetry_init(115200);
    // ... carrega circuito, pinmap ...

    struct timespec next;
    clock_gettime(CLOCK_MONOTONIC, &next);
    uint32_t period_ns = 1000000000 / emu_cfg.target_freq_hz;

    while (1) {
        emulator_run(&emu_cfg);
        telemetry_poll(&emu_cfg);          // stdin + comandos

        next.tv_nsec += period_ns;
        if (next.tv_nsec >= 1000000000) {
            next.tv_sec++;
            next.tv_nsec -= 1000000000;
        }
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL);
    }
}
```

---

## 4. Performance

| Plataforma | CPU | Virtual clock estimado |
|---|---|---|
| RP2040 | 133 MHz Cortex-M0+ | 15–53 kHz |
| ESP32 | 240 MHz Xtensa LX6 | ~95 kHz |
| Pi Zero W | 1 GHz ARMv6 | **100–500+ kHz** |
| Pi 4 | 1.8 GHz ARMv8 | **1–2 MHz+** |

O clock virtual na Pi Zero W pode ser **10× maior** que nos MCUs, graças ao CPU 1 GHz.
O jitter do scheduler Linux (especialmente single-core Zero W) é a contrapartida.

---

## 5. Build

### Opção A — nativo na Pi

```bash
sudo apt install gcc make
cd firmware
gcc -DRPI_GPIO \
    -Ilib/hal/include -Ilib/runtime/include \
    src/main_pc.c src/circuit_blinky.c \
    lib/hal/src/hal_gpio.c lib/hal/src/hal_timer.c \
    lib/hal/src/hal_serial.c lib/runtime/src/*.c \
    -o ufpga_emu -lm
```

### Opção B — PlatformIO (cross-compile)

```ini
[env:rpi_zero_w]
platform = native
build_flags =
    -DRPI_GPIO
    -I${PROJECT_DIR}/firmware/lib/hal/include
    -I${PROJECT_DIR}/firmware/lib/runtime/include
build_src_filter = +<*> -<*rp2040*> -<*esp32*> -<stim_test_*> -<examples/>
```

Compila no PC, copia binário para a Pi.

---

## 6. Vantagens sobre MCUs

| Funcionalidade | Pi (Linux) | RP2040 / ESP32 |
|---|---|---|
| VCD em arquivo real | ✅ grava no SD | ❌ (só RAM, limitado) |
| Depuração remota | ✅ SSH, GDB, logs | ❌ só serial |
| Rede / WiFi | ✅ nativo | ❌ (ESP32 tem WiFi) |
| Clock virtual | 100–500+ kHz | 15–95 kHz |
| GPIO 3.3V | ✅ (compatível) | ✅ |
| Tamanho / custo | ~US$ 15 (Zero W) | ~US$ 3–5 |

---

## 7. Limitações

| Aspecto | Impacto |
|---|---|
| Scheduler Linux | Jitter no clock virtual (especialmente Zero W single-core) |
| Permissão `/dev/gpiomem` | Usuário precisa estar no grupo `gpio` |
| GPIO 3.3V apenas | Mesmo do RP2040/Due |
| Sem tempo real | `clock_nanosleep` não é RTOS — pode atrasar sob carga |

---

## 8. Resumo

| Item | Viabilidade |
|---|---|
| Port | ✅ **Trivial** — ~50 linhas de HAL novo |
| GPIO real | ✅ via `/dev/gpiomem`, sem libs externas |
| Fallback sem Pi | ✅ automático (`open()` falha → virtual) |
| Reaproveita código | ✅ `main_pc.c`, runtime, telemetria, VCD |
| Virtual clock | 100–500+ kHz (Pi Zero W) |
| Esforço | ~1–2 h |

O port para Pi é o mais simples de todos: o firmware Linux já existe, o HAL novo
são 50 linhas, e o GPIO via `/dev/gpiomem` é direto ao registrador sem overhead.
