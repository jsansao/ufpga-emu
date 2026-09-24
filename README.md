# uFPGA-Emu

Emulador de hardware descrito em Verilog executado em microcontroladores de 32 bits (ESP32, RP2040, Raspberry Pi 3 B+, Arduino Due e ESP8266). Um toolchain Python traduz Verilog sintetizável para C, que é compilado e executado no firmware com clock virtual, telemetria e comandos via serial. A alocação de pinos vive em JSON por plataforma (`firmware/pinmaps/`), não nos mains.

## Pré-requisitos

- Python 3.10+
- PlatformIO 6.0+ — `pip install -r requirements.txt` (recomendado) ou `pip install platformio`.
  Garanta `pio` no `PATH` (`export PATH=$HOME/.local/bin:$PATH` se usou `--break-system-packages`).
- ESP32: toolchain ESP-IDF (instalado pelo PlatformIO)
- Linux (para VCD writer e `hal_stimulus`)

## Estrutura

```
firmware/
  pinmaps/                       # Fonte de verdade: <plat>.json (esp32, rp2040, due, esp8266, rpi)
  lib/
    hal/                         # HAL: GPIO, timer, serial, mutex
    runtime/                     # Emulator core, pin_map, telemetry, vcd_writer
  src/
    circuit_*.c                  # Gerados pelo pc_tool.cli
    stim_test_*.c                # Gerados pelo testbench_generator
    pinmap_*.h                   # Gerados pelo pinmap_gen (NÃO EDITAR)
    main_esp32.c                 # Mains genéricos — nenhum é editado p/ novo circuito
    main_rp2040.cpp
    main_due.cpp
    main_esp8266.cpp
    main_rpi.c
    main_pc.c                    # Entry point PC
    examples/                    # C source + main para compilação PC (test_compile_all_examples)
pc_tool/
  cli.py                         # Verilog → C
  parser/
    lexer.py, parser.py, ast.py, registry.py, inliner.py
  codegen/
    c_generator.py               # Geração de C com edge detection, constant folding, etc
  pinmap_gen.py                  # pinmaps/*.json → pinmap_*.h (+ --template p/ circuito novo)
  testbench_generator.py         # CSV stimulus → C testbench
examples/
  *.v                            # Circuitos Verilog de exemplo
  stim_*.csv                     # Estímulo CSV com auto-assertions
tests/
  test_parser.py                 # 75 testes: parser, codegen, generate, multi-file, task/function
  test_testbenches.py            # 27 testes: testbenches + stim + compile + VCD
  test_pinmaps.py                # 7 testes: schema, staleness, template, loader C
platformio.ini                   # 134 envs (26 ESP32, 27 RP2040, 27 Due, 27 ESP8266, 27 PC)
```

## PC Toolchain

### CLI: Verilog → C

```bash
python3 -m pc_tool.cli examples/meu_circuito.v -o firmware/src/circuit_meu_circuito.c
```

Aceita múltiplos `.v` com `--top` para designs multi-módulo (instanciação com flatten).

### Testbench Generator: CSV → stim_test

```bash
python3 -m pc_tool.testbench_generator meu_circuito \
    --verilog examples/meu_circuito.v \
    --csv examples/stim_meu_circuito.csv \
    -o firmware/src/stim_test_meu_circuito.c
```

O CSV usa o formato `time_us,signal,value,expected` com `inputs` como sinal especial contendo o packed value. A quarta coluna (`expected`) ativa auto-assertions no stim_test gerado.

### Pinmap Generator: JSON → header

```bash
# 1. Emite a entrada do circuito novo (pins com "pin": null)
python3 -m pc_tool.pinmap_gen --template -v examples/meu_circuito.v -p esp32

# 2. Cole a entrada em firmware/pinmaps/esp32.json, preencha os "pin" e regenere
python3 -m pc_tool.pinmap_gen
```

O modo default valida todos os JSONs e regenera `firmware/src/pinmap_*.h` (cadeia `#if` de circuitos + JSON embutido). Detalhes do schema em [Pinmaps por Plataforma (JSON)](#pinmaps-por-plataforma-json).

## GUI didática (`tools/gui/`)

App desktop Tkinter para uso em laboratório (sem terminal): aba **Exemplos**
(26 circuitos, fonte + simulação PC) e aba **Novo circuito** (editar →
verificar → mapear → programar o ESP32 → monitorar com toggles).

```bash
python3 tools/gui/app.py
```

Ver intenção em `docs/intent/gui-didatica.md`, spec em
`docs/spec/gui-didatica.md` e setup do laboratório em
`docs/gui-lab-setup.md`.

## Workflow: Adicionar um Novo Circuito

### 1. Verilog

Crie `examples/meu_circuito.v`:

```verilog
module meu_circuito(
    input clk,
    input [3:0] in,
    output reg [3:0] out
);
    always @(posedge clk) out <= in;
endmodule
```

### 2. Gerar C

```bash
python3 -m pc_tool.cli examples/meu_circuito.v \
    -o firmware/src/circuit_meu_circuito.c
```

### 3. CSV de estímulo

Crie `examples/stim_meu_circuito.csv`:

```csv
time_us,signal,value,expected
0,inputs,0,0
5,inputs,5,5
10,inputs,0,5
15,inputs,10,10
```

O `inputs` empacota todos os sinais de entrada na ordem de declaração (bits 0..N). Consulte o `.c` gerado para confirmar o packing.

### 4. Stim test

```bash
python3 -m pc_tool.testbench_generator meu_circuito \
    --verilog examples/meu_circuito.v \
    --csv examples/stim_meu_circuito.csv \
    -o firmware/src/stim_test_meu_circuito.c
```

### 5. Main PC

Copie `firmware/src/examples/circuito_existente_main.c` e ajuste `pinmap_json` e `VCD_REG_COUNT`.

```bash
cp firmware/src/examples/meu_circuito_main.c firmware/src/examples/meu_circuito_main.c
```

Também copie o `.c` gerado:

```bash
cp firmware/src/circuit_meu_circuito.c firmware/src/examples/meu_circuito.c
```

### 6. Pinmap da plataforma alvo

Nenhum `main_*.c` é editado. A alocação de pinos vive em `firmware/pinmaps/<plat>.json`:

```bash
# Gera a entrada com name/bit/dir extraídos do Verilog (pin = null)
python3 -m pc_tool.pinmap_gen --template -v examples/meu_circuito.v -p esp32
```

Cole a entrada no JSON da plataforma, preencha os `"pin"` físicos e regenere os headers:

```bash
python3 -m pc_tool.pinmap_gen
```

`clk`/`rst` são resolvidos por nome no firmware; exceções de init (ex.: `run=1` do tiny_cpu) vão em `virtual_init`. Ver [Pinmaps por Plataforma (JSON)](#pinmaps-por-plataforma-json).

### 7. PlatformIO

Adicione dois envs em `platformio.ini`:

```ini
[env:esp32-meucircuito]
platform = espressif32
board = esp32dev
framework = espidf
build_src_filter = +<*> -<*rp2040*> -<stim_test_*> -<examples/>
board_build.f_cpu = 240000000L
monitor_speed = 115200
build_flags =
    -I${PROJECT_DIR}/firmware/lib/hal/include
    -I${PROJECT_DIR}/firmware/lib/runtime/include
    -DEMU_CIRCUIT_MEU_CIRCUITO

[env:pc-stim-meucircuito]
platform = native
build_flags =
    -I${PROJECT_DIR}/firmware/lib/hal/include
    -I${PROJECT_DIR}/firmware/lib/runtime/include
build_src_filter = +<*> -<*esp32*> -<*rp2040*> -<circuit_*> -<main_pc*> -<testbench_*> -<stim_test_*> -<examples/> +<circuit_meu_circuito*> +<stim_test_meu_circuito*>
```

### 8. Registrar nos testes

Em `tests/test_testbenches.py`:

- Adicione `'pc-stim-meucircuito': 'stim_meu_circuito.csv'` no `STIM_CSV_MAP`
- Adicione `'meu_circuito'` na lista `test_compile_all_examples`

### 9. Testar

```bash
# PC
pytest tests/ -v
# ESP32
pio run -e esp32-meucircuito -t upload
# Monitor (tecla Ctrl+C para sair)
pio run -e esp32-meucircuito -t monitor
```

Use o comando `vset` para alterar inputs em tempo real via serial:

```
vset 34 1    # pin 34 = 1
vset 35 0    # pin 35 = 0
```

## Executar Testes

```bash
# Instalar dependências (uma vez)
pip install -r requirements.txt  # instala pytest, platformio, pyserial; garante pio no PATH

# Suite completa (109 testes) — requer PlatformIO + gcc
python3 -m pytest tests/ -v

# Sem PlatformIO (só parser/codegen, 75 testes)
python3 -m pytest tests/test_parser.py -v
# Integração PC (27 testes, compila via pio run -e pc-* — requer gcc)
python3 -m pytest tests/test_testbenches.py -v
# Pinmaps JSON (7 testes: schema, staleness, template, loader C)
python3 -m pytest tests/test_pinmaps.py -v

# Compilar todos os envs (opcional)
pio run
```

> Nota: `tests/test_testbenches.py` chama `pio run -e pc-test-*`/`pc-stim-*` e falha com `FileNotFoundError` se `pio` não estiver no `PATH`. Na primeira execução o PlatformIO baixa `native@1.2.1` e `tool-scons`.

**109 testes** (75 parser/codegen + 27 testbenches/stim/VCD/compile + 7 pinmaps).

## Construtos Verilog Suportados

| Construto | Status |
|---|---|
| `module`/`endmodule` | ✅ |
| `input`/`output`/`wire`/`reg` | ✅ |
| `assign` (continuous) | ✅ |
| `always @(posedge/negedge clk)` | ✅ |
| `always @(posedge clk or posedge rst)` | ✅ (edge detection multi-sinal) |
| `if`/`else` | ✅ |
| `case`/`endcase` | ✅ |
| `for` loop (sintetizável) | ✅ |
| `repeat` loop (não-sintetizável) | ✅ |
| `begin`/`end` | ✅ |
| Blocking (`=`) / Non-blocking (`<=`) | ✅ |
| `===`/`!==` (case equality) | ✅ |
| Reduction operators (`^`, `&`, `\|`) | ✅ |
| Ternary `?:` | ✅ |
| `not` keyword | ✅ |
| `{N{expr}}` repeat | ✅ |
| Bit-select (`sig[i]`) | ✅ |
| Part-select (`sig[msb:lsb]`) | ✅ (LHS e RHS) |
| Concatenação `{a, b}` | ✅ (multi-bit) |
| `parameter` | ✅ |
| `localparam` | ✅ (não-overridable) |
| `generate`/`endgenerate` | ✅ (if/for/case, nested) |
| `genvar` | ✅ |
| Module instantiation | ✅ (flatten via `ModuleRegistry`) |
| `task`/`endtask` | ✅ (com output ports, locals, nested calls) |
| `function`/`endfunction` | ✅ (com `return`, locals, nested calls) |
| `integer` | ✅ (como local C) |

## Codegen Optimizations

- **Literal masks for GET_BITS:** `((inputs >> N) & 0xMMu)` em vez de macro genérica
- **`<< 0` suppression:** shifts zero suprimidos no packing de outputs
- **Constant folding:** `(0) & 0xF` → `0`, `(N) & MASK` → foldado
- **Dead register elimination:** regs nunca lidos removidos de `state->regs[]`
- **Edge detection global:** antes de todos os always blocks, todos os sinais combinados com `||`

## ESP32: GPIO Constraints

**Pinos PROIBIDOS (SPI flash):** GPIO 6, 7, 8, 9, 10, 11

**Pinos disponíveis:**
- Bidirecionais: 12-19, 21-23, 25-27, 32-33
- Input-only: 34-39

**Pinagem típica:**
- `clk` virtual: GPIO 4
- `rst`: GPIO 5
- Inputs virtuais (com `hal_gpio_set_virtual`): GPIOs 34-39, 12-13
- LED/GPIO de saída: GPIO 2
- Outputs: GPIOs 14-19, 21-23, 25-27

O mapeamento é definido em `firmware/pinmaps/esp32.json` (ver seção abaixo) e embutido no firmware via `pinmap_esp32.h` gerado.

## Pinmaps por Plataforma (JSON)

Cada plataforma tem um arquivo em `firmware/pinmaps/<plat>.json` (`esp32`, `rp2040`, `due`, `esp8266`, `rpi`) com todos os seus circuitos:

```json
{
  "counter": {
    "pins": [
      {"name": "clk", "pin": 4, "bit": 0, "dir": "input"},
      {"name": "count[0]", "pin": 13, "bit": 0, "dir": "output"}
    ],
    "virtual_init": {}
  },
  "tiny_cpu": {
    "pins": [ "..." ],
    "virtual_init": {"run": 1}
  }
}
```

Regras:
- `bit` é o índice sequencial **por direção** na palavra packed de inputs/outputs.
- `"pin": null` só existe no template (`--template`); no JSON commitado todo `pin` é um número — o `pinmap_gen` rejeita `null`.
- `virtual_init` liga valores iniciais por **nome de sinal** (resolvido via `pin_map_get_physical`); use para exceções como `run=1`. `clk`/`rst` são resolvidos por nome no main, sem config extra.
- Os headers `firmware/src/pinmap_*.h` são **commitados** (MCUs não têm filesystem) e o teste `test_headers_up_to_date` quebra se você editar o JSON e esquecer de rodar `python3 -m pc_tool.pinmap_gen`.
- Subsets por plataforma são permitidos: um circuito pode existir só no JSON do seu alvo.

## Comandos via Serial

| Comando | Descrição |
|---|---|
| `vset <pin> <val>` | Altera valor virtual de um pino de entrada (0 ou 1) |
| Telemetria | Output automático: `CLK= N IN=0x... OUT=0x... REG0=0x...` |

## Firmware Architecture

### Clock Virtual

O clock não usa sinal externo. `hal_gpio_set_clk(pin, freq_hz)` configura um timer interno. A cada leitura do pino de clock, a HAL verifica se meio-período passou e alterna o estado. O timer é cacheado via `hal_gpio_set_cached_now()` para eliminar chamadas repetidas a `esp_timer_get_time()` dentro de um mesmo step.

### Emulator Step

```c
emulator_step(config):
    lock(mutex)
    inputs = 0
    for each pin_map binding:
        if input: inputs |= hal_gpio_read(pin) << bit_pos
    config.eval_fn(&state, inputs, &outputs)
    for each pin_map binding:
        if output: hal_gpio_write(pin, (outputs >> bit_pos) & 1)
    state.clock_count++
    se VCD ativo: vcd_record(...)
    unlock(mutex)
```

### Testbench Determinístico

Testbenches C (stim_test) rodam sem HAL — chamam `circuit_eval()` diretamente com inputs packed, sem tempo real. Edge detection é feito dentro do `circuit_eval()` gerado.

## Limitações

- **Clock ESP32:** ~84 kHz (target 100 kHz). Gap devido ao overhead de eval + pin map iteration.
- **Flash size:** Placa de 2MB, config padrão `esp32dev` assume 4MB (bootloader avisa, mas funciona).
- **VCD writer:** apenas Linux (`__linux__`).
- **`hal_stimulus`:** apenas Linux (não disponível no ESP32).
