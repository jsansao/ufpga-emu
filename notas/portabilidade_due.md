# Portabilidade para Arduino Due (SAM3X8E)

> Consulta: como seria o port do uFPGA-Emu para Arduino Due?

---

## 1. Hardware

| Especificação | Arduino Due |
|---|---|
| MCU | Atmel SAM3X8E ARM Cortex-M3 |
| Clock | 84 MHz |
| RAM | 96 KB (64 + 32 KB, dois bancos) |
| Flash | 512 KB |
| GPIO digitais | 54 (0–53, todos bidirecionais) |
| PWM | 12 canais |
| USB | Nativo (OTG) + Programação (via ATmega16U2) |
| USB CDC nativo | ✅ SerialUSB |
| Cores | 1 (Cortex-M3, single-core) |
| Framework Arduino | ✅ C++ |

---

## 2. Comparação com plataformas existentes

| Item | Due (84 MHz) | RP2040 (133 MHz) | ESP32 (240 MHz) | ESP8266 (80 MHz) |
|---|---|---|---|---|
| Arquitetura | ARM M3 | ARM M0+ | Xtensa LX6 | Xtensa L106 |
| RAM | 96 KB | 264 KB | 520 KB | ~50 KB |
| Flash | 512 KB | 2 MB | 4 MB | 1–4 MB |
| GPIO livres | **54** | 30 | ~28 (flash pins bloqueados) | ~9 (flash pins bloqueados) |
| USB CDC nativo | ✅ (SerialUSB) | ✅ (Serial) | ❌ (UART + CH340) | ❌ (UART + CH340) |
| Cores | 1 | 2 | 2 | 1 |
| Virtual clock estimado | **20–40 kHz** | 15–53 kHz | ~95 kHz | 20–35 kHz |
| `pin_map_t` (2.5 KB) cabe? | ✅ | ✅ | ✅ | ✅ |

**Diferenciais do Due:**
- **54 GPIOs sem nenhum bloqueio** — ao contrário de ESP32/ESP8266 que perdem os GPIOs 6–11 para SPI flash. Os pinmaps podem ser mais generosos que no ESP32.
- **USB CDC nativo** — mesma experiência bidirecional do RP2040 (SerialUSB). Sem CH340 externa, sem deadlock de UART.
- **Cortex-M3** tem hardware multiply e divide single-cycle, ao contrário do M0+ no RP2040 (multi-cycle). Operaçőes aritméticas (alu, adder_n) rodam mais rápido.

---

## 3. HAL — implementação

### 3.1 hal_gpio.c — novo bloco `ARDUINO_ARCH_SAM`

```c
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

void hal_gpio_set_mode(uint8_t pin, hal_gpio_mode_t mode) {
    pinMode(pin, (mode == HAL_GPIO_INPUT) ? INPUT_PULLUP : OUTPUT);
}

uint8_t hal_gpio_read(uint8_t pin) {
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

void hal_gpio_write(uint8_t pin, uint8_t value) {
    digitalWrite(pin, value ? HIGH : LOW);
}
```

Dificuldade: **fácil** (API Arduino padrão). Se necessário desempenho extra, pode-se usar registros PIO diretos (PIOA, PIOB, PIOC, PIOD).

### 3.2 hal_serial.c — novo bloco `ARDUINO_ARCH_SAM`

```c
#elif defined(ARDUINO_ARCH_SAM)

// Usa a porta USB nativa (SerialUSB) em vez da Serial (programação via 16U2)
extern SerialUSB_ SerialUSB;

void hal_serial_init(uint32_t baud) {
    (void)baud;
    SerialUSB.begin(115200);
}

void hal_serial_send_buffer(const uint8_t *data, size_t len) {
    SerialUSB.write(data, len);
}

int hal_serial_receive_byte(uint8_t *data) {
    if (SerialUSB.available()) {
        *data = SerialUSB.read();
        return 0;
    }
    return -1;
}
```

Dificuldade: **fácil** (API SerialUSB idêntica ao `Serial` do RP2040).

**Importante:** usar `SerialUSB` (porta USB nativa) e não `Serial` (porta de programação via 16U2). A placa PlatformIO correta é `dueUSB`.

### 3.3 hal_timer.c — novo bloco `ARDUINO_ARCH_SAM`

```c
#elif defined(ARDUINO_ARCH_SAM)

#include <Arduino.h>

void hal_timer_init(void) {}

uint64_t hal_timer_get_us(void) {
    return micros();
}

void hal_timer_delay_us(uint32_t us) {
    delayMicroseconds(us);
}

void hal_timer_yield(void) {
    // single-core, sem preempção — no-op
}
```

Dificuldade: **fácil** (idêntico ao ESP8266, sem necessidade de `optimistic_yield()`).

### 3.4 hal_mutex.c — novo bloco `ARDUINO_ARCH_SAM`

```c
#elif defined(ARDUINO_ARCH_SAM)

// single-core, sem ISR concorrente — no-op
void hal_mutex_init(hal_mutex_t *mutex) { (void)mutex; }
void hal_mutex_lock(hal_mutex_t *mutex)   { (void)mutex; }
void hal_mutex_unlock(hal_mutex_t *mutex) { (void)mutex; }
```

Dificuldade: **trivial**.

---

## 4. main_due.cpp — estrutura

O RP2040 usa `multicore_launch_core1()` para rodar o emulador em paralelo. O Due é single-core, então o padrão é intercalar no `loop()` (mesma abordagem do ESP8266).

```cpp
#include <Arduino.h>
extern "C" {
#include "hal_gpio.h"
#include "hal_timer.h"
#include "hal_serial.h"
#include "emulator.h"
#include "telemetry.h"
}

// ---#include "circuit_*.c" + pinmap_json (igual ao main_esp32.c)

static emulator_config_t emu_cfg;
static char cmd_line[128];
static size_t cmd_line_len = 0;

void setup() {
    hal_gpio_init();
    hal_timer_init();
    telemetry_init(115200);

    telemetry_send_string("uFPGA-Emu v1.0 - Arduino Due (CIRCUIT_NAME)\n");

    pin_map_load(&emu_cfg.pin_map, pinmap_json);
    emu_cfg.init_fn  = circuit_init;
    emu_cfg.eval_fn  = circuit_eval;
    emu_cfg.target_freq_hz = 100000;

    emulator_init(&emu_cfg);
    hal_gpio_set_clk(4, 100000);
    // ... hal_gpio_set_virtual(...)
}

void loop() {
    emulator_run(&emu_cfg);

    // Processa comandos (buffer de linha persistente)
    uint8_t c;
    while (hal_serial_receive_byte(&c) == 0) {
        if (c == '\n' || cmd_line_len >= 127) {
            cmd_line[cmd_line_len] = '\0';
            telemetry_handle_command(&emu_cfg, cmd_line);
            cmd_line_len = 0;
        } else if (c != '\r') {
            cmd_line[cmd_line_len++] = (char)c;
        }
    }

    // Telemetria periódica (~1 Hz)
    static uint32_t last_report = 0;
    uint32_t now = (uint32_t)(hal_timer_get_us() / 1000000);
    if (now - last_report >= 1) {
        telemetry_send_state(&emu_cfg);
        last_report = now;
    }
}
```

Dificuldade: **médio** (adaptar `main_rp2040.cpp` removendo `pico/multicore.h` e `multicore_launch_core1()`, usando `SerialUSB`).

---

## 5. Pinagem — sem restrições

O Due não tem pinos de flash bloqueados (ao contrário de ESP32/ESP8266). Os pinmaps podem ser mais flexíveis que no ESP32.

| Circuito | Pinos ESP32 | Pinos Due (sugestão) |
|---|---|---|
| Counter | clk=4, rst=5, count=13,14,15,16 | clk=4, rst=5, count=13,14,15,16 ✅ |
| Shift register | clk=4, rst=5, load=13, data=14, pl=15, dout=2,16-23 | clk=4, rst=5, load=13, data=14, pl=15, dout=2,6,7,8,9,10,11,12 |
| PWM | 34-39 (input-only), 12-23 | 34,35,36,37,38,39 não existem → usar A0-A5 (54-59) ou 24-29 |
| Tiny CPU | instr=34-39,12-23, pc=25,26,27,32,33 | instr em 24-39, pc em 6-10 |

**Importante:** o Due não tem pinos 34-39 (só vai até 53). Os circuitos que usam esses pinos no ESP32 precisam ser re-mapeados para pinos 24-29 ou 44-53. Como há 54 pinos disponíveis, há folga para redistribuir.

---

## 6. Limitações

| Aspecto | Due (84 MHz) | RP2040 (133 MHz) | ESP32 (240 MHz) |
|---|---|---|---|
| Virtual clock | **20–40 kHz** | 15–53 kHz | ~95 kHz |
| GPIO | 54 (todos livres) | 30 | ~28 (6 flash) |
| Telemetria contínua | ✅ | ✅ | ✅ |
| VCD | ❌ (sem arquivo local) | ❌ | ❌ |
| Circuitos grandes | ✅ cabe em 96 KB | ✅ | ✅ |
| Multitarefa | ❌ single-core (loop intercalado) | ✅ dual-core | ✅ dual-core |
| USB CDC nativo | ✅ (SerialUSB) | ✅ (Serial) | ❌ (UART+CH340) |
| WiFi | ❌ | ❌ | ✅ |

### Single-core

O emulador pausa quando `loop()` processa comandos seriais (mesmo cenário do ESP8266). O clock virtual tende ao fim inferior da faixa (~20-25 kHz) com telemetria ativa.

### Virtual clock vs RP2040

O Cortex-M3 é mais eficiente por MHz que o M0+ (hardware multiply/divide, melhor branch prediction), mas roda a 84 MHz vs 133 MHz. A compensação parcial faz com que o Due atinja virtual clock similar ao RP2040:

- RP2040 M0+ 133 MHz: 15–53 kHz
- Due M3 84 MHz: **20–40 kHz** (menos pico, mais piso)

O piso maior vem do hardware multiply — circuitos aritméticos (alu, adder_n) são significativamente mais rápidos que no M0+.

---

## 7. Esforço estimado

| Tarefa | Linhas | Tempo |
|---|---|---|
| HALs (4 arquivos, novos `#elif`) | ~150 | 1–2 h |
| `main_due.cpp` (adaptar de `main_rp2040.cpp`) | ~120 | 1 h |
| Pinmaps ajustados (14 circuitos, ESP32 → Due) | ~200 | 1–2 h |
| `platformio.ini` (15 envs, board `dueUSB`) | ~60 | 30 min |
| Teste em hardware | — | 1–2 h |
| **Total** | **~530** | **~4–7 h** |

---

## 8. Resumo

| Item | Viabilidade |
|---|---|
| Port direto (HALs + main) | ✅ **Fácil** — mesmas APIs Arduino do RP2040 |
| USB CDC | ✅ SerialUSB nativo (sem CH340) |
| GPIO | ✅ 54 pinos, sem restrições |
| Mesmos 26 circuitos | ✅ cabe em RAM e flash |
| Pinmaps existentes | ⚠️ precisa re-mapear GPIOS 34-39 (inexistentes) |
| Virtual clock | 20–40 kHz (útil para ensino) |
| Single-core | ⚠️ jitter maior que RP2040/ESP32 |
| Custo da placa | ~US$ 25–35 (mais caro que ESP32) |

O Arduino Due é o alvo mais confortável entre os não-suportados: RAM farta, USB CDC nativo, 54 GPIOs livres, arquitetura ARM 32-bit. A única desvantagem real é single-core, que impacta o jitter do clock virtual. Para laboratório de ensino com demonstrações ao vivo, o comportamento é aceitável; para medições precisas de frequência, o RP2040 ou ESP32 são superiores.
