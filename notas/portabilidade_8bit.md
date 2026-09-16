# Portabilidade para 8-bit (ATmega328P / Arduino Uno)

> Consulta: se fosse incluir uma plataforma de 8 bits como Arduino Uno, quais seriam
> as limitações da emulação e se poderia fazer uma versão *light* do emulador.

---

## 1. Gargalo: RAM

| Componente | Bytes | Problema? |
|---|---|---|
| `pin_map_t` (64 bindings × 40 B) | 2568 | ❌ sozinho estoura 2 KB |
| `model_state_t` (32 regs + 32 wires + inputs/outputs/count) | 268 | ⚠️ redutível |
| `cmd_line[128]` | 128 | redutível |
| `watch_cfg` | 36 | redutível |
| `virtual_values[N]` | N (14-30) | ✅ |
| `hal_clk` | 16 | ✅ |
| Pilha/outros | ~250 | ✅ |
| **Total atual (RP2040)** | **~3300 B** | |

O `pin_map_t` (2568 bytes) sozinho excede os 2 KB disponíveis no ATmega328P.

---

## 2. O que cortar para uma versão *lite*

### 2.1 `pin_map_t` — o bloqueador

Cada `pin_binding_t` tem:
- `physical_pin` (1 B)
- `bit_pos` (1 B)
- `direction` (4 B, enum = int)
- `name[32]` (32 B)
- padding (~2 B)
- **Total: 40 B por binding**

64 bindings × 40 B = 2560 B + count + padding = 2568 B.

**Corte proposto:**
| Parâmetro | Atual | Lite | Ganho |
|---|---|---|---|
| `MAX_PIN_BINDINGS` | 64 | 8–12 | −2080 a −2240 B |
| `pin_binding_t.name` | `char[32]` → `const char *` (flash) | −32 B/binding | −256 a −384 B |

Com 12 bindings + name em flash: `pin_map_t` cai de 2568 B para ~504 B.

Circuito típico (blinky, counter, mux) usa 4–12 pinos de I/O — 12 bindings é suficiente para a maioria.

### 2.2 `model_state_t`

| Parâmetro | Atual | Lite | Ganho |
|---|---|---|---|
| `MAX_REGS` | 32 × 4 B = 128 B | 8–16 | −64 a −96 B |
| `MAX_WIRES` | 32 × 4 B = 128 B | 8–16 | −64 a −96 B |

`model_state_t` cai de 268 B para ~140–204 B.

**Limitação:** circuitos com muitos registros (tiny_cpu com 16 regs) usariam 16 slots — ainda caberia se `MAX_REGS` for mantido em 16.

### 2.3 Buffers de I/O

| Buffer | Atual | Lite |
|---|---|---|
| `cmd_line[128]` | 128 B | 64 B (processa byte a byte se estourar) |
| `watch_cfg.name[32]` | 32 B | 16 B (ou nome curto fixo) |

### 2.4 HAL — remoção de dependências

| Componente atual | Substituição AVR |
|---|---|
| `hal_mutex` (spinlock ou FreeRTOS) | `no-op` (single-core sem ISR concorrente) |
| `hal_timer` (`time_us_64()` hw) | `micros()` Arduino (res 4 µs) |
| `hal_gpio` (`gpio_set_function`) | `PORTx / DDRx / PINx` direto |
| `hal_serial` (USB CDC nativo) | `Serial.read() / write()` (CH340 UART) |

### 2.5 Estimativa final de RAM (lite)

| Componente | Bytes |
|---|---|
| `pin_map_t` (12 bindings, name em flash) | ~504 |
| `model_state_t` (16 regs + 16 wires) | 204 |
| `virtual_values[14]` | 14 |
| `hal_clk` | 16 |
| `hal_cached_now` | 8 |
| `watch_cfg` | 8 (só `active`, nome em flash) |
| `emulator_paused` | 4 |
| `cmd_line[64]` | 64 |
| variáveis de loop | ~24 |
| pilha | ~200 |
| **Total** | **~1046 B** |

Folga: ~978 B (47% dos 2 KB).

---

## 3. Limitações da emulação

| Aspecto | ATmega328P (16 MHz) | RP2040 (133 MHz) | Causa |
|---|---|---|---|
| Clock virtual | **2–5 kHz** | 15–53 kHz | CPU 8× mais lenta + overhead da emulação em 8-bit |
| Pinos suportados | 14 digitais + 6 analógicos (A0-A5) | 30 | Hardware limitado |
| Circuitos comportados | só pequenos (mux, decoder, counter, fsm101, shift_register) | todos (inclusive tiny_cpu) | RAM e flash |
| Telemetria | só `read` / `status` (sem VCD) | VCD + streaming | RAM e banda serial |
| Comandos | `vset` / `read` / `status` / `reset` | completo + telemetria | RAM |
| Multitarefa | single-core, sem preempção | core0 I/O + core1 emulador | Hardware (1 core vs 2) |
| Frequência máxima de toggle em pino real | ~200–500 Hz* | ~5–15 kHz | Velocidade do loop de emulação |

> * O pino real toggla à medida que o `circuit_eval()` atualiza `virtual_values[]` e o HAL aplica na porta física. Com clock virtual de 2–5 kHz e 1–2 ciclos de máquina por avaliação, o toggle real fica numa fração disso.

---

## 4. Flash (32 KB)

| Componente | Bytes (estimado) |
|---|---|
| HAL AVR (gpio, serial, timer) | ~2–4 KB |
| Runtime (emulator, pin_map, telemetry simplificada) | ~4–6 KB |
| Circuito gerado (blinky) | ~0.5–1 KB |
| main / loop / comandos | ~3–5 KB |
| Framework Arduino core | ~8–10 KB |
| **Total** | **~18–26 KB** |

Folga: ~6–14 KB (19–44% de 32 KB).

---

## 5. Resumo

| Item | Viabilidade |
|---|---|
| Rodar firmware atual sem modificações | ❌ — `pin_map_t` sozinho estoura RAM |
| Versão *lite* (10–12 circuitos pequenos) | ✅ — com cortes nas constantes de compilação |
| Clock virtual | 2–5 kHz (útil para ensino, não para periféricos rápidos) |
| Telemetria | só comandos síncronos (`read` / `status`), sem VCD |
| HAL | nova implementação AVR (~300 linhas) |
| Arduino Mega (ATmega2560, 8 KB RAM) | ✅✅ — cabe sem cortes drásticos |

### Recomendação

Se o objetivo é suporte a 8-bit, **o Arduino Mega (ATmega2560, 8 KB SRAM, 256 KB flash)** é o alvo mais natural:

- 8 KB SRAM → cabe o firmware atual com reduções mínimas
- 256 KB flash → folga enorme
- 54 pinos digitais → mais próximo do mapeamento RP2040/ESP32
- Mesma arquitetura AVR → HAL compatível

Para manter no Uno, seria necessário:

1. Criar `build_flags` no `platformio.ini` para `MAX_PIN_BINDINGS=12`, `MAX_REGS=16`, `MAX_WIRES=16`
2. Implementar `hal_gpio_avr.c`, `hal_serial_avr.c`, `hal_timer_avr.c`, `hal_mutex_avr.c`
3. Remover ou #ifdef a telemetria contínua (só comandos síncronos)
4. Testar com os circuitos menores da suíte (blinky, counter, fsm101, mux, decoder — ~10 circuitos)
