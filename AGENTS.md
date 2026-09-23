# Anchored Summary — uFPGA-Emu

## Goal
Compilar e testar o projeto uFPGA-Emu em hardware real (ESP32, RP2040, Raspberry Pi 3 B+, Arduino Due, ESP8266) e criar testbenches automatizados para validação dos circuitos gerados pelo pc_tool.

## Constraints & Preferences
- **ESP32:** CH340 USB-UART, `/dev/ttyUSB0`. GPIOs 6-11 são SPI flash — não usar.
- **RP2040:** Arduino/mbed, board pico, 133 MHz, USB CDC (`/dev/ttyACM0`). BOOTSEL ID `2e8a:0003`, CDC ID `2e8a:00c0`.
- **Raspberry Pi 3 B+:** IP `192.168.15.28` (era `192.168.15.6`, depois `192.168.1.127`), hostname `ernesto1`, SSH `joao@`, key auth, aarch64, `/dev/gpiomem`, gpio group. Toolchain: `gcc`, `-lrt -lpthread`. Sync sem rsync local: `tar czf - firmware/ | ssh joao@IP 'mkdir -p ~/ufpga-emu && tar xzf - -C ~/ufpga-emu'`.
- **Arduino Due:** SAM3X8E ARM Cortex-M3, 84 MHz, 96 KB RAM, 512 KB flash. USB CDC nativo (`SerialUSB`). Board PlatformIO: `dueUSB`. Sem pinos bloqueados (54 GPIOs).
- **ESP8266 (Wemos D1 Mini):** 80 MHz, UART CH340, GPIOs disponíveis: 2,4,5,12,13,14,15,16 (6-11 SPI flash, 1/3 TX/RX, 17+ inexistentes)
- PlatformIO em `~/.venvs/pio/bin/pio`.
- Virtual clock via firmware (`hal_gpio_read`), sem sinal externo.

## Progress
### Done
- ✅ **Todos os 26 circuitos RP2040 validados no hardware Pico.**
- ✅ **Firmware RP2040:** USB CDC fix (`gpio_set_function` substitui `gpio_init`), loop com comandos `vset`/`status`/`read`/`reset`, multicore.
- ✅ **Porta RPi GPIO implementada e validada no hardware Pi 3 B+:** 25/25 circuitos compilam e rodam com GPIO real via `/dev/gpiomem`. `main_rpi.c` com todos os 26 pinmaps adaptados (BCM 0-27).
- ✅ **Medição de clock no Pi adicionada:** `target_freq_hz=0` (sem delay artificial), `telemetry_set_freq()` chamada após 1s de medição.
- ✅ **Clock máximo estimado no Pi:** **1,0 MHz (tiny_cpu) a 3,0 MHz (blinky)** — ~10-30× ESP32, ~20-60× RP2040.
- ✅ **Testbenches PC corrigidos (27/27 passando):** `main_rpi.c` faltava `-<main_rpi*>` no `build_src_filter` de 26 envs `pc-*` em `platformio.ini`, causando linker errors. Fix: adicionado exclusor em todos os envs + template `testbench_generator.py` + check de retorno em `test_testbenches.py`.
- ✅ **Paper ijcae2026.tex:** Tabela de escalabilidade (`tab:escalabilidade`) agora inclui coluna `Pi 3 B+ kHz` com valores medidos. Texto de discussão atualizado. PDF recompilado (9 páginas, 516 KB).
- ✅ **Paper revisado para incluir RP2040:** Abstracts, introdução, contribuições, tabelas, HAL, resultados, conclusão. Submissão pronta (checklist + nota de submissão).
- ✅ **Análises de portabilidade salvas:** `notas/portabilidade_*.md` para ATmega328P, ESP8266, Arduino Due, RPi.
- ✅ **Porta Arduino Due implementada:** HALs (gpio, serial, timer, mutex) com blocos `ARDUINO_ARCH_SAM`, `main_due.cpp` com 26 circuitos (single-core, SerialUSB, comandos vset/read/status/reset), `platformio.ini` com `due_base` + 26 envs. **26/26 envs compilam e 26/26 validados no hardware Due.**
- ✅ **102/102 testes passando** (60 parser/codegen + 16 testbenches PC + 26 testbenches integração).
- ✅ **Porta ESP8266 implementada:** HALs (gpio/serial/timer/mutex) com blocos `ARDUINO_ARCH_ESP8266`, `main_esp8266.cpp` com 26 circuitos (single-core, UART Serial, comandos vset/read/status/reset), `platformio.ini` com `esp8266_base` + 27 envs. **27/27 envs compilam** e **26/26 circuitos validados no hardware Wemos D1 Mini.**
- ✅ **Medição de clock no ESP8266 adicionada:** `target_freq_hz=0` (sem delay artificial), `send_snapshot()` já calcula freq via `(clock_delta * 1000000) / elapsed_us`. Clock real sem nanossleep.
- ✅ **Clock máximo medido no ESP8266:** **25,6 kHz (tiny_cpu) a 64,8 kHz (not_keyword)**
- ✅ **`generate case` com nested generates (parser fix):** `_skip_generate_item` trata `ALWAYS`; `_skip_to_semicolon` rastreia `begin/end`. 4 testes novos.
- ✅ **Artigo atualizado:** `ijcae2026.tex` com ESP8266, Due, 102 testes, coluna ESP8266 na escalabilidade, pinagens Due/ESP8266, 5 plataformas. PDF 10 pág, 521 KB.
- ✅ **102/102 testes pytest passam** (parser/codegen + testbenches)
- ✅ **Testbenches CSV automáticos (gerador + envs + pytest):** `pc_tool/testbench_generator.py` gera `stim_test_<circuit>.c` a partir de CSV+Verilog (modo `inputs` direto ou sinais individuais, auto-asserts da 4ª coluna do CSV, `check_fn` especial para `tiny_cpu`). Adicionados 19 envs `pc-stim-*` (total `platformio.ini`: 106 → **134**). `tests/test_testbenches.py` ganhou `STIM_CSV_MAP` + `test_stim` parametrizado por `_discover_stim_envs()`. **102/102 coletados** (75 parser + 27 testbenches: 4 `test_tb` + 19 `test_stim` + 2 `test_vcd` + 1 `compile_all` + 1 `load_port`).
- ✅ **Pinmaps externalizados em JSON:** `firmware/pinmaps/{esp32,rp2040,due,esp8266,rpi}.json` são a fonte de verdade (schema `{"circuito":{"pins":[{name,pin,bit,dir}],"virtual_init":{}}}`). `pc_tool/pinmap_gen.py` gera `firmware/src/pinmap_<plat>.h` (cadeia `#if` de `#include "circuit_X.c"` + `CIRCUIT_NAME` + JSON embutido como `PINMAP_JSON`); modo `--template -v <file.v> -p <plat>` emite entrada com name/bit/dir do Verilog e `"pin": null`. `pin_map_load_circuit()` (pin_map.c) seleciona o circuito por chave e devolve `virtual_init` (por nome de sinal, resolvido via `pin_map_get_physical`). **Os 5 mains ficaram genéricos (~2900 → 761 linhas): nenhum main é editado para adicionar circuito.** clk/rst agora por lookup de nome; exceções de init (tiny_cpu `run=1` em esp32/due/esp8266) viraram `virtual_init` no JSON. **109/109 testes** (102 + 7 novos em `tests/test_pinmaps.py`: schema, staleness de headers, JSON embutido == arquivo, template, loader C nativo; subsets por plataforma permitidos — só `validate()` + header da própria plataforma importam). Compilado: esp32-counter/tinycpu/decoder, rp2040-counter/tiny_cpu, due-counter/tinycpu, esp8266-counter/tinycpu (9 envs PIO OK) + `main_rpi.c` syntax-check (Pi offline). Extração provada lossless (130/130 pinmaps idênticos ao git HEAD). Fluxo validado de ponta a ponta com circuito fictício `zz_demo` (template → JSON → regen → `pio run -e esp32-zzdemo` OK, depois revertido). **ESP32 validado no hardware (`/dev/ttyUSB0`):** counter (banner + CLK + `read count[0]`/`clk` resolvem nomes do JSON), tiny_cpu (`read run` → 1, CPU executando — `virtual_init` OK), decoder (truth table 4/4 via `vset`+`read y[n]` — caminho sem `set_clk` seguro). **Pi validada no hardware (`192.168.15.28`, sync via tar+ssh, `~/ufpga-emu/firmware/`):** `build_rpi.sh counter` + `tiny_cpu` compilam (só warning pré-existente do cast); counter roda a 2,6 MHz medidos, tiny_cpu stepping normal (run sem init, igual ao main original). **Due validada no hardware (porta nativa `/dev/ttyACM1`, upload via programming `/dev/ttyACM0`):** counter (`read 13`/`read 4` por pino + `vset` OK — notar: `read` da Due recebe número de pino, não nome de sinal como no ESP32), tiny_cpu (`read 34` → 1, `virtual_init` OK, OUT multi-bit confirma que não caiu no fallback blinky), decoder (truth table 4/4 via `vset 25/26` + `read 13/14/16/17`). **RP2040 validada no hardware (CDC `/dev/ttyACM0`, upload com auto-reboot p/ BOOTSEL):** counter (`read 12`/`read 2` por pino, ~99,6 kHz), tiny_cpu (`read 4` → 1 via pull-up do HAL — sem `virtual_init` no JSON, igual ao main original — CPU executando a 45 kHz), decoder (truth table 4/4 via `vset 4/5` + `read 25/12/13/14`; `read` também por número de pino). **ESP8266 validada no hardware (Wemos `/dev/ttyUSB0`):** counter (~48 kHz, `read` por pino + `vset` OK), tiny_cpu (`read 34` → 1, `virtual_init` OK, CPU a 25,6 kHz — igual ao clock histórico), decoder (truth table 4/4 via palavras packed do `status`: IN 0x00→OUT 0x01, 0x01→0x02, 0x02→0x04, 0x03→0x08 — pinos 25/26/17 do pinmap original são virtuais no 8266, dirigidos por `vset`). **5/5 plataformas validadas no hardware com o firmware JSON.**

### Blocked
- **Hardware pendente p/ pinmaps JSON:** ESP32 **validado** (counter/tiny_cpu/decoder no hardware — ver abaixo). Pi `192.168.15.6` **offline**: respondeu 1× via SSH (sem repo em `~`, só `ls`) e caiu em seguida (`No route to host`, WiFi/sleep?).

## Next Steps
- *(opcional, adiado por decisão do usuário)* Limpeza de órfãos: 15 `stim_test_*.c` sem underscore não referenciados no `platformio.ini` (ex.: `stim_test_addern.c`, `stim_test_fsm101.c`) e `main_rp2040.cpp.bak`/`.full`.
- *(aguardar novas definições)*

## Key Decisions
- **`gpio_set_function` em vez de `gpio_init` em `hal_gpio_set_mode`:** `gpio_init` corrompe USB CDC no RP2040.
- **Buffer de linha persistente em `loop()`:** bytes perdidos entre frames USB CDC — buffer `cmd_line[128]` acumula até `\n`.
- **`if (!Serial) return;` em hal_serial_rp2040_send_buffer:** Previne deadlock USB.
- **`target_freq_hz=0` no Pi:** mede clock real sem nanossleep, que tem latência alta no Linux.
- **`-<main_rpi*>` adicionado a todos `pc-*` envs:** `main_rpi.c` não era excluído por `-<*rp2040*>` nem `-<main_pc*>`.
- **`-<*main_due*>` adicionado a todos `pc-*` envs:** mesmo problema do main_rpi.c.
- **`-<*main_esp8266*>` adicionado a todos `pc-*` envs:** mesmo padrão dos demais mains.
- **`hal_serial_due.h` com wrappers `extern "C"`:** `SerialUSB` é objeto C++ do framework Arduino SAM, inacessível diretamente de `hal_serial.c` (compilado como C).
- **`hal_serial_esp8266.h` com wrappers `extern "C"`:** `Serial` é objeto C++ do core Arduino ESP8266, mesmo padrão do Due.
- **ESP8266 HAL_GPIO_MAX_PINS=40:** aumentado de 17 para 40 para suportar pinmaps com pins virtuais até 39. `HAL_GPIO_PHYSICAL_PINS=17` limita `pinMode`/`digitalRead`/`digitalWrite` aos GPIOs físicos existentes (0-5,12-16).
- **Estimulação CSV isolada em `hal_stimulus.{c,h}`:** `main_pc.c` lê `STIMULUS_CSV` e carrega estímulos via `hal_stimulus_load`; `hal_gpio.c` (`__linux__`) delega leituras de pino a `hal_stimulus_get` antes do clock virtual.
- **Gerador de testbench imprime bloco `[env:pc-stim-*]` pronto:** `testbench_generator.py -o ...` emite as linhas `build_src_filter` com `-<circuit_*/> -<testbench_*/> -<stim_test_*/> -<examples/> +<circuit_X*/> +<stim_test_X*/>` para colar no `platformio.ini`.
- **Headers de pinmap são commitados e testados p/ staleness:** o JSON é fonte de verdade, mas MCUs não têm filesystem — `pinmap_<plat>.h` (commitado, `static const char PINMAP_JSON[]`) embute o JSON. `tests/test_pinmaps.py::test_headers_up_to_date` regenera e compara; esquecer de rodar `pinmap_gen` quebra o teste, não o hardware.
- **`find_circuit` do pin_map.c exige `{` após a chave:** impede falso-match quando um pino ou chave de `virtual_init` tem o mesmo nome de um circuito (`"counter"` como valor/`{"counter":1}` não têm `{` depois de `:`).
- **Mains resolvem clk/rst por nome (`pin_map_get_physical`), não por número:** RP2040 usa clk=2/rst=3, demais 4/5 — o lookup cobre ambos; `hal_gpio_set_clk` só é chamado se o circuito tem binding `clk` (decoder não tem — `hal_gpio_read` já guarda com `mcu_clk.initialized`).

## Critical Context
- `platformio.ini`: 134 envs — 26 ESP32, 27 RP2040, 27 Due, 27 ESP8266, 27 PC (1 base + 3 `pc-*` + 4 `pc-test-*` + 19 `pc-stim-*`).
- Pi build: `gcc -DRPI_GPIO -DEMU_CIRCUIT_<name> $(ls lib/*/src/*.c) src/main_rpi.c -lpthread -lm -o ufpga_emu_<name>`.
- Test suite: `pytest tests/` = **109 coletados** (75 parser + 27 testbenches + 7 pinmaps); `test_stim` parametrizado via `STIM_CSV_MAP`/`_discover_stim_envs()` (19 CSVs em `examples/`).
- **Fluxo novo circuito → novo alvo (pinmaps JSON):** 1) `python3 -m pc_tool.cli novo.v -o firmware/src/circuit_novo.c` 2) `python3 -m pc_tool.pinmap_gen --template -v novo.v -p <plat>` → colar entrada em `firmware/pinmaps/<plat>.json` e preencher `"pin": null` 3) `python3 -m pc_tool.pinmap_gen` (regenera headers) 4) adicionar env no `platformio.ini`. Nenhum `main_*.c` é editado.
- Paper: `paper/ijcae2026.tex`, compilado via `pdflatex`.
- VCD writer: `$timescale 1 us`, timestamps = `clock_count`.
- `_skip_generate_item` (parser.py:469): novo handler para `ALWAYS` — avança `always @(posedge clk)` ou `always @(*)`, depois faz skip do corpo respeitando profundidade `begin`/`end`.
- `_skip_to_semicolon` (parser.py:510): tracking real de profundidade `begin`/`end`, evita corromper skip de branches inativos com `begin...end` sem `;` interno.

## Relevant Files
- `presentations/ufpga_emu_grupo.tex` — apresentação interna (Beamer/Metropolis, PT-BR, 12 slides); compilar com `pdflatex`; `lstlisting` quebra no beamer → usar `\lstinputlisting` (`snippets/`)
- `firmware/pinmaps/{esp32,rp2040,due,esp8266,rpi}.json` — fonte de verdade dos pinmaps (schema `{"circuito":{"pins":[...],"virtual_init":{}}}`)
- `firmware/src/pinmap_<plat>.h` — gerado (commitado): cadeia `#if` de circuitos + `CIRCUIT_NAME` + `PINMAP_JSON` embutido
- `pc_tool/pinmap_gen.py` — regenera headers de `firmware/pinmaps/`; `--template -v <file.v> -p <plat>` emite entrada JSON do Verilog (name/bit/dir, `pin` null)
- `firmware/lib/runtime/src/pin_map.c` — `pin_map_load_circuit()` (seleção por chave + `virtual_init`), `find_circuit`/`object_end`
- `tests/test_pinmaps.py` — 7 testes: schema, staleness, JSON embutido == arquivo, template, loader C nativo
- `firmware/lib/hal/src/hal_gpio.c` — `ARDUINO_ARCH_ESP8266` block (antes de `ARDUINO_ARCH_SAM`), `pinMode`/`digitalRead`/`digitalWrite`
- `firmware/src/main_esp8266.cpp` — ESP8266 main genérico (pinmap via header), single-core, UART Serial
- `firmware/src/main_due.cpp` — Due main genérico (pinmap via header), single-core loop
- `firmware/src/main_rpi.c` — Pi main genérico (pinmap via header), medição de freq
- `firmware/src/main_rp2040.cpp` — RP2040 firmware com USB CDC e multicore, pinmap via header
- `firmware/src/main_esp32.c` — ESP32 main genérico (58 linhas), pinmap via header
- `firmware/lib/hal/src/hal_serial.c` — `if (!Serial) return;`, `ARDUINO_ARCH_ESP8266` e `ARDUINO_ARCH_SAM` via wrappers C++
- `firmware/lib/hal/include/hal_serial_esp8266.h` — C-linkage wrappers para Serial
- `firmware/lib/hal/include/hal_serial_due.h` — C-linkage wrappers para SerialUSB
- `firmware/lib/runtime/src/telemetry.c` — `telemetry_set_freq()`, `telemetry_send_state()`
- `firmware/build_rpi.sh` — script de compilação para Pi
- `platformio.ini` — 134 envs, com `-<*main_esp8266*>` nos pc-*
- `tests/test_testbenches.py` — 27 testes integração (4 `test_tb` + 19 `test_stim` + 2 `test_vcd` + 1 `compile_all` + 1 `load_port`), `STIM_CSV_MAP` + `_discover_stim_envs()`
- `pc_tool/testbench_generator.py` — gera `stim_test_<circuit>.c` via `-v <m.v> -c <stim.csv> -o firmware/src/stim_test_X.c`; usa `models` direto vs `inputs`; imprime bloco `[env:pc-stim-*]`
- `firmware/lib/hal/src/hal_stimulus.c` / `include/hal_stimulus.h` — `hal_stimulus_load`/`hal_stimulus_get` p/ estímulo CSV no PC
- `firmware/src/main_pc.c` — lê `STIMULUS_CSV` (via `hal_stimulus_load`) antes do loop (pinmap próprio blinky, fora do sistema JSON)
