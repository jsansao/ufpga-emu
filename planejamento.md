# Plano de Implementação — uFPGA-Emu

## Projeto: Emulador de Hardware Baseado em Microcontroladores de 32-bits
**Versão:** 1.0  
**Data:** 27 de Junho de 2026  
**Plataformas Alvo:** Espressif ESP32 & Raspberry Pi Pico (RP2040)  
**Linguagens de Entrada:** Verilog / SystemVerilog  
**Ferramenta PC:** Python 3.10+  
**Firmware:** C ANSI (ESP-IDF / Pico SDK)

---

## Fase 1 — ✅ Concluída (HAL + Runtime + Parser/Codegen)

### Estrutura do Projeto

```
fpga_emu/
├── firmware/                            # Firmware do microcontrolador
│   ├── lib/
│   │   ├── hal/include/                 # HAL headers
│   │   │   ├── hal_gpio.h              # GPIO: init, set_mode, read, write
│   │   │   ├── hal_timer.h             # Timer: init, get_us, delay_us
│   │   │   ├── hal_serial.h            # Serial: init, send, receive
│   │   │   └── hal_mutex.h             # Mutex: init, lock, unlock
│   │   ├── hal/src/
│   │   │   ├── hal_gpio_esp32.c
│   │   │   ├── hal_gpio_rp2040.c
│   │   │   ├── hal_timer_esp32.c
│   │   │   ├── hal_timer_rp2040.c
│   │   │   ├── hal_serial_esp32.c
│   │   │   ├── hal_serial_rp2040.c
│   │   │   ├── hal_mutex_esp32.c
│   │   │   └── hal_mutex_rp2040.c
│   │   └── runtime/                     # Motor de execução compartilhado
│   │       ├── include/
│   │       │   ├── model.h             # model_state_t (inputs, outputs, regs, wires)
│   │       │   ├── pin_map.h           # pin_map_t, pin_binding_t
│   │       │   ├── emulator.h          # emulator_config_t, init, step, run_core1
│   │       │   └── telemetry.h         # ringbuf_t, init, send, receive, run_core0
│   │       ├── src/
│   │       │   ├── pin_map.c           # Parser JSON para mapeamento de pinos
│   │       │   ├── emulator.c          # Lê GPIOs → avalia → escreve GPIOs
│   │       │   └── telemetry.c         # Envio periódico de estado + comandos
│   │       └── templates/
│   │           └── circuit_template.c  # Template para codegen
│   ├── src/
│   │   ├── main_esp32.c                # Entry point ESP32 (dual-core)
│   │   ├── main_rp2040.c               # Entry point RP2040 (dual-core)
│   │   └── circuit_blinky.c            # Exemplo manual de circuito
│   └── projects/blinky/
├── pc_tool/                             # Ferramenta PC (Python)
│   ├── cli.py                          # CLI: pc_tool.cli input.v -o output.c
│   ├── parser/
│   │   ├── lexer.py                    # Tokenizer
│   │   ├── parser.py                   # Parser recursivo descendente
│   │   └── ast.py                      # AST (Module, Port, Signal, AlwaysBlock...)
│   ├── codegen/
│   │   └── c_generator.py              # Gera circuit_init() + circuit_eval()
│   └── config/
├── examples/                            # HDL examples
│   ├── blinky.v                        # Blinky com contador de 50k ciclos
│   ├── counter.v                       # Contador de 4 bits
│   └── blinky_pinmap.json              # Mapeamento de pinos
├── generated/                           # C gerado pelo pc_tool
│   ├── blinky.c
│   └── counter.c
└── platformio.ini                       # Build: [env:esp32] + [env:rp2040]
```

### Funcionalidades Implementadas

#### HAL
- **GPIO:** init, set_mode (input/output), read, write
- **Timer:** init, get_us (microsegundos), delay_us (busy-wait)
- **Serial:** init (baud rate), send_byte, send_buffer, receive_byte
- **Mutex:** init, lock, unlock (FreeRTOS semaphore no ESP32, spin_lock no RP2040)

#### Runtime
- **model.h:** `model_state_t` com inputs (32 bits), outputs (32 bits), regs (64 × uint32_t), wires (64 × uint32_t), clock_count
- **pin_map:** parsing de JSON para ligar nomes de sinais a pinos GPIO físicos + posições de bit
- **emulator:**
  - `emulator_init()` — init do modelo + configuração dos GPIOs
  - `emulator_step()` — leitura física → avaliação lógica → escrita física
  - `emulator_run_core1()` — loop infinito com periodização por frequência alvo (ex: 100 kHz)
- **telemetry:**
  - `telemetry_run_core0()` — laço no Core 0 enviando estado a cada 1s via serial
  - Comandos: `reset` (reinicia modelo), `status` (envia estado imediato)

#### pc_tool (Parser + Codegen)
- **Parser de Verilog** (subconjunto educacional):
  - Módulos com portas estilo ANSI
  - Declarações: `input`, `output`, `inout`, `wire`, `reg`
  - `always @(posedge/negedge sig or posedge/negedge sig)`
  - Atribuições bloqueantes (`=`) e não-bloqueantes (`<=`)
  - `if/else`, `case/endcase`
  - Operadores: `+ - ~ & | ^ << >> ! && || == !=`
  - Números: binário (`'b`), decimal (`'d`), hexadecimal (`'h`)
- **Codegen C ANSI:**
  - `circuit_init()` — zera todos os registros
  - `circuit_eval()` — extrai entradas do word de 32 bits, detecção de borda, reset assíncrono, lógica síncrona, montagem da saída
  - Compatível com `model.h` do runtime

---

## Fase 2 — Validação e Robustez 🔴🔴🟡

### 2.1 Compilar e corrigir (🔴 Alta)

**Objetivo:** Verificar se o firmware compila para ambos os targets.

**Tarefas:**
- [ ] Instalar dependências: ESP-IDF, Pico SDK, PlatformIO
- [ ] Executar `pio run -e esp32` e corrigir erros de compilação
- [ ] Executar `pio run -e rp2040` e corrigir erros de compilação
- [ ] Ajustar includes para compatibilidade com a estrutura PlatformIO
- [ ] Verificar se `circuit_blinky.c` referencia as funções corretas (`circuit_init`, `circuit_eval`)

### 2.2 Mascaramento de largura (🔴 Alta)

**Objetivo:** Respeitar a largura de bits declarada no HDL.

**Problema:** Registros de largura menor que 32 bits (ex: `reg [3:0] counter`) não são mascarados, podendo acumular valores fora da faixa.

**Solução no codegen:**
- [ ] Associar cada registrador à sua largura original
- [ ] Em `circuit_eval()`, aplicar máscara `& ((1 << W) - 1)` em toda atribuição a registro
- [ ] Exemplo: `counter <= counter + 1` → `state->regs[N] = (state->regs[N] + 1) & 0xF;`

### 2.3 Scripts de conveniência (🟡 Média)

**Objetivo:** Automatizar o fluxo de trabalho.

- [ ] Criar `scripts/generate.sh` — `python3 -m pc_tool.cli $1 -o generated/$1.c`
- [ ] Criar `scripts/build.sh` — `cd firmware && pio run -e $1`
- [ ] Criar `scripts/test_parse.sh` — testa parser em todos os `examples/*.v`

### 2.4 README.md (🟡 Média)

**Objetivo:** Documentar o projeto.

- [ ] Instalação de dependências
- [ ] Fluxo de uso: escrever HDL → gerar C → compilar → gravar
- [ ] Exemplos práticos (blinky, counter)
- [ ] Mapeamento de pinos (JSON)
- [ ] Comandos de telemetria serial

### 2.5 Ampliar parser (🟢 Baixa)

- [ ] Operadores: `*`, `/`, `%`, `<`, `>`
- [ ] Concatenação: `{a, b}`
- [ ] `assign` completo com parte-selecionada
- [ ] `always @(*)` (sensibilidade combinacional)

---

## Fase 3 — Teste e Depuração 🟡🟢

### 3.1 Modo simulação PC (🟡 Média)

**Objetivo:** Validar o código C gerado sem hardware.

- [ ] Criar testbench em C para PC: `testbench.c`
  - Inclui `model.h` + circuito gerado
  - Loop que chama `circuit_eval()` com entradas simuladas
  - Gera arquivo VCD (Value Change Dump) para visualização
- [ ] Comparar saída com simulador Verilog (Icarus Verilog)

### 3.2 Testes unitários do parser/codegen (🟡 Média)

**Objetivo:** Garantir que o pipeline Verilog → C produz código correto.

- [ ] pytest para `pc_tool/parser/` (tokenize, parse)
- [ ] pytest para `pc_tool/codegen/` (geração para blinky, counter, FSM)
- [ ] Testes de regressão para cada novo recurso do parser

### 3.3 Telemetria avançada (🟢 Baixa)

- [ ] Comando `read <nome_do_sinal>` — retorna valor atual
- [ ] Comando `write <nome_do_sinal> <valor>` — força valor
- [ ] Comando `step N` — executa N ciclos e reporta estado
- [ ] Comando `watch <sinal>` — streaming contínuo de um sinal

---

## Fase 4 — Performance e Completude 🟡🟢

### 4.1 Blocos PIO para RP2040 — RF07 (🟡 Média)

**Objetivo:** Usar PIO para amostragem ultra-rápida das entradas.

- [ ] Implementar programa PIO que captura estado de até 8 entradas simultaneamente
- [ ] FIFO PIO → Core 1 para processamento
- [ ] Reduz jitter de leitura para dezenas de nanossegundos

### 4.2 Medição de jitter — RNF02 (🟢 Baixa)

- [ ] Medir com osciloscópio: tempo entre leitura de entrada e escrita de saída
- [ ] Garantir jitter < 10% do período de clock emulado
- [ ] Documentar frequências máximas alcançadas por complexidade do circuito

### 4.3 Exemplos avançados (🟢 Baixa)

| Exemplo | Descrição |
|---|---|
| **FSM** | Máquina de estados (detector de sequência) |
| **Shift register** | Registrador de deslocamento de 8 bits |
| **PWM** | Gerador de PWM com duty cycle configurável |
| **UART virtual** | Transmissor UART 9600 baud implementado em lógica |

---

## Mapa de Requisitos x Implementação

| ID | Requisito | Status | Fase |
|---|---|---|---|
| RF01 | Suporte a HDL (Verilog) | ✅ Parcial | 2.5 |
| RF02 | Tradução para C/C++ | ✅ | 1 |
| RF03 | Mapeamento de pinos | ✅ | 1 |
| RF04 | Loop dual-core | ✅ | 1 |
| RF05 | Clock síncrono | ✅ | 1 |
| RF06 | Telemetria/debug | ✅ | 1 |
| RF07 | Blocos PIO (RP2040) | ⬜ Pendente | 4.1 |
| RNF01 | 100 kHz mínimo | ⬜ A verificar | 4.2 |
| RNF02 | Jitter < 10% | ⬜ A verificar | 4.2 |
| RNF03 | RAM ≤ 128 KB | ✅ (projetado) | 1 |
| RNF04 | Portabilidade C ANSI | ✅ | 1 |
| RNF05 | Concorrência segura | ✅ | 1 |

---

## Recomendação de Próximo Passo

**Iniciar pela tarefa 2.1 (Compilar e corrigir):**
1. Instalar dependências (ESP-IDF, Pico SDK, PlatformIO)
2. Executar `pio run -e esp32`
3. Corrigir erros de compilação
4. Executar `pio run -e rp2040`
5. Corrigir erros de compilação
