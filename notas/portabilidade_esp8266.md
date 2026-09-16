# Portabilidade para ESP8266 (Arduino Uno)

> Consulta: se fosse incluir uma plataforma ESP8266, esse port seria mais fácil
> que o ATmega328P?

---

## 1. Comparação com ATmega328P

| Item | ATmega328P | ESP8266 |
|---|---|---|
| Arquitetura | 8-bit (uint32_t operações emuladas em software) | 32-bit Xtensa L106 (igual ESP32) |
| RAM disponível | 2 KB | **~50 KB** |
| Flash | 32 KB | 1–4 MB |
| `pin_map_t` (2568 B) | ❌ estoura 2 KB | ✅ 5% da RAM |
| SDK | Arduino AVR | Arduino core ESP8266 |

O bloqueador principal do ATmega328P — o `pin_map_t` com 2568 bytes — **não existe** no ESP8266. A RAM é da mesma ordem que o RP2040 (264 KB) para o firmware: ambos têm folga suficiente.

---

## 2. Esforço de port

### 2.1 HALs — padrão já estabelecido

Cada HAL já usa `#ifdef` por plataforma (`ESP_PLATFORM`, `ARDUINO_ARCH_RP2040`, `__linux__`).
O ESP8266 entraria como mais um `#elif`.

#### hal_gpio.c — novo bloco `ARDUINO_ARCH_ESP8266`

```c
#elif defined(ARDUINO_ARCH_ESP8266)

#include <Arduino.h>
#include "hal_timer.h"

#define HAL_GPIO_MAX_PINS 17

static struct {
    uint8_t  clk_pin;
    uint8_t  state;
    uint64_t last_us;
    uint32_t half_period_us;
    uint8_t  initialized;
} esp8266_clk;

static int8_t virtual_values[HAL_GPIO_MAX_PINS];
static uint64_t hal_cached_now = 0;

void hal_gpio_set_mode(uint8_t pin, hal_gpio_mode_t mode) {
    pinMode(pin, (mode == HAL_GPIO_INPUT) ? INPUT_PULLUP : OUTPUT);
}

uint8_t hal_gpio_read(uint8_t pin) {
    if (pin < HAL_GPIO_MAX_PINS && virtual_values[pin] >= 0)
        return (uint8_t)virtual_values[pin];
    if (esp8266_clk.initialized && pin == esp8266_clk.clk_pin) { ... }
    return (uint8_t)digitalRead(pin);
}

void hal_gpio_write(uint8_t pin, uint8_t value) {
    digitalWrite(pin, value ? HIGH : LOW);
}
```

Dificuldade: **fácil** (APIs conhecidas do Arduino, sem peculiaridades do SDK).

#### hal_serial.c — novo bloco `ARDUINO_ARCH_ESP8266`

```c
#elif defined(ARDUINO_ARCH_ESP8266)

void hal_serial_init(uint32_t baud) {
    Serial.begin(baud);
}

void hal_serial_send_buffer(const uint8_t *data, size_t len) {
    Serial.write(data, len);
}

int hal_serial_receive_byte(uint8_t *data) {
    if (Serial.available()) {
        *data = Serial.read();
        return 0;
    }
    return -1;
}
```

Dificuldade: **fácil** (idêntico ao RP2040, mas sem guard `if (!Serial)` porque UART não tem CDC disconnect).

#### hal_timer.c — novo bloco `ARDUINO_ARCH_ESP8266`

```c
#elif defined(ARDUINO_ARCH_ESP8266)

#include <Arduino.h>

void hal_timer_init(void) {}

uint64_t hal_timer_get_us(void) {
    return micros();
}

void hal_timer_delay_us(uint32_t us) {
    delayMicroseconds(us);
}

void hal_timer_yield(void) {
    optimistic_yield(us);
}
```

Dificuldade: **fácil** (Arduino API padrão, `optimistic_yield()` é específico ESP8266 mas bem documentado).

#### hal_mutex.c — novo bloco `ARDUINO_ARCH_ESP8266`

```c
#elif defined(ARDUINO_ARCH_ESP8266)

// Single-core, sem ISR concorrente — no-op
void hal_mutex_init(hal_mutex_t *mutex) { (void)mutex; }
void hal_mutex_lock(hal_mutex_t *mutex)   { (void)mutex; }
void hal_mutex_unlock(hal_mutex_t *mutex) { (void)mutex; }
```

Dificuldade: **trivial** (mesmo approach do AVR).

### 2.2 main_esp8266.c — novo arquivo

Padrão: `setup()` + `loop()` estilo Arduino (similar ao RP2040, mas sem multicore).

```c
#include <Arduino.h>
#include "hal_gpio.h"
#include "hal_timer.h"
#include "emulator.h"
#include "telemetry.h"

// #include "circuit_*.c" + pinmap_json (igual ao main_esp32.c)

static emulator_config_t emu_cfg;

void setup() {
    hal_gpio_init();
    hal_timer_init();
    telemetry_init(115200);

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
    telemetry_receive_cmd(&emu_cfg);
    // delay(1) implícito no emulator_run
}
```

Diferença principal do ESP32: **sem `xTaskCreatePinnedToCore`** — o emulador roda inline no `loop()`, intercalado com telemetria e comandos.

Dificuldade: **médio** (copiar a estrutura do `main_rp2040.cpp`, adaptar para C).

### 2.3 platformio.ini — novas envs

```ini
[env:esp8266]
platform = espressif8266
board = nodemcuv2
framework = arduino
build_src_filter = +<*> -<*rp2040*> -<stim_test_*> -<examples/> -<main_esp32*> -<main_pc*>
board_build.f_cpu = 80000000L
monitor_speed = 115200
build_flags =
    -I${PROJECT_DIR}/firmware/lib/hal/include
    -I${PROJECT_DIR}/firmware/lib/runtime/include

[env:esp8266-blinky]
extends = esp8266
build_flags = ${env:esp8266.build_flags} -DEMU_CIRCUIT_BLINKY
```

~15 entradas (1 base + 14 circuitos).

### 2.4 Ajuste dos pinmaps

O ESP32 usa GPIOs 34-39 (input-only) extensivamente. O ESP8266 tem:

| Pinos ESP8266 | Função | Usável como GPIO? |
|---|---|---|
| 0 | Boot flag (HIGH para boot normal) | ✅ com cuidado |
| 1 | TX (UART0) | ❌ durante Serial |
| 2 | Boot flag (HIGH), LED onboard | ✅ com cuidado |
| 3 | RX (UART0) | ❌ durante Serial |
| 4 | GPIO livre | ✅ |
| 5 | GPIO livre | ✅ |
| 6-11 | SPI flash | ❌ (igual ESP32) |
| 12 | GPIO livre (HSPI MISO) | ✅ |
| 13 | GPIO livre (HSPI MOSI) | ✅ |
| 14 | GPIO livre (HSPI SCLK) | ✅ |
| 15 | Boot flag (LOW), HSPI CS | ✅ com cuidado |
| 16 | GPIO, wake from deep sleep | ✅ |

**Utilizáveis sem restrição:** 4, 5, 12, 13, 14 = 5 pinos.
**Com restrições:** 0, 2, 15, 16 = +4 pinos. Total ~9.

Circuitos com muitos pinos de I/O (shift_register, alu, tiny_cpu) precisariam de pinmaps condensados ou multiplexados.

---

## 3. Limitações

| Aspecto | ESP8266 (80 MHz) | ESP32 (240 MHz) | RP2040 (133 MHz) |
|---|---|---|---|
| Clock virtual estimado | **20–35 kHz** | ~95 kHz | 15–53 kHz |
| Pinos GPIO utilizáveis | ~8–12 | ~28 | 30 |
| Telemetria contínua | ✅ | ✅ | ✅ |
| VCD | ❌ sem arquivo local | ❌ | ❌ |
| Circuitos grandes | ✅ (tiny_cpu cabe) | ✅ | ✅ |
| Multitarefa | ❌ single-core | ✅ dual-core | ✅ dual-core |
| USB CDC nativo | ❌ UART via CH340 | ❌ UART via CH340 | ✅ nativo |
| WiFi | ✅ embutido | ✅ embutido | ❌ |

### 3.1 Single-core — impacto na emulação

No ESP32 e RP2040, o emulador roda em um core dedicado:
- ESP32: `xTaskCreatePinnedToCore(emulator_run_core1, ..., 1)` — core1
- RP2040: `multicore_launch_core1(emulator_run_core1)` — core1

No ESP8266, `loop()` precisa intercalar:
```
loop() {
    emulator_run(&emu_cfg);   // avalia M ciclos
    telemetry_receive_cmd();  // processa comando serial
    telemetry_send_state();   // envia status periódico
    // repete
}
```

Isso significa:
- Toda vez que um comando serial chega (`vset`, `read`, `status`), a emulação pausa
- O `delay(1)` no loop cria jitter no clock virtual
- Clock virtual tende ao **fim inferior da faixa** (20–25 kHz) com telemetria ativa

### 3.2 Pinagem reduzida

Circuitos do `main_esp32.c` como `pwm`, `uart_tx`, `tiny_cpu` usam GPIOs 34-39 (6 pinos input-only) que **não existem** no ESP8266. Seria necessário:

1. Redistribuir para GPIOs disponíveis (4, 5, 12, 13, 14)
2. Ou aceitar que alguns circuitos complexos (tiny_cpu com 6 entradas + 5 saídas) excedem o número de pinos livres e usar `virtual_values` sem mapeamento físico (simulação pura via serial)

---

## 4. Resumo

| Item | Viabilidade |
|---|---|
| Port direto (HALs + main) | ✅ **Fácil** — 4 HALs (~150 linhas) + 1 main (~100 linhas) |
| Mesmos 26 circuitos | ✅ RAM cabe, flash cabe |
| Pinmaps existentes | ⚠️ precisa re-mapear GPIOs 34-39 |
| Clock virtual | 20–35 kHz (útil para ensino) |
| Single-core | ⚠️ jitter maior que ESP32/RP2040 |
| PlatformIO | ✅ suporte nativo (`espressif8266` + `arduino`) |

### Estimativa de esforço

| Tarefa | Linhas | Tempo estimado |
|---|---|---|
| HALs (4 arquivos, novos `#elif`) | ~150 | 1–2 h |
| `main_esp8266.c` (adaptar de `main_rp2040.cpp`) | ~100 | 1 h |
| `platformio.ini` (15 envs) | ~60 | 30 min |
| Pinmaps ajustados (14 circuitos) | ~200 | 2–3 h |
| Teste em hardware | — | 1–2 h |
| **Total** | **~510** | **~5–8 h** |

Muito mais rápido que ATmega328P (que exigiria redesenho das constantes de compilação e cortes de RAM).
