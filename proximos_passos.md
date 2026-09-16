# Checklist Final — uFPGA-Emu

## Feito

- [x] Revisar `related work` com comparação mais objetiva e direta
- [x] Explicitar a metodologia de medição de `kHz` e tempo de compilação
- [x] Manter `abstract`, `conclusão` e `discussão` sem tom promocional
- [x] Separar com clareza validação técnica e impacto educacional
- [x] Destacar limitações logo após os resultados
- [x] Conferir se todas as listagens e referências cruzadas estão corretas
- [x] Fazer uma passada final de linguagem para remover frases promocionais
- [x] Verificar se as tabelas de comparação e resultados estão consistentes
- [x] Avaliar se vale incluir mais um trabalho próximo em `related work`

## Futuro

- [ ] Considerar estudo com alunos para uma versão futura do artigo

---

# Próximos Passos — uFPGA-Emu

**Data:** 28 de Junho de 2026
**Contexto:** Todos os 4 passos do roadmap inicial foram concluídos:
1. ✅ 4 circuitos testados no ESP32 (blinky, counter, fsm_101, shift_register)
2. ✅ Estimulação CSV + validação (stim_test_fsm_101, stim_test_shift_register)
3. ✅ Ordenação topológica no codegen (Kahn's algorithm)
4. ✅ 13 exemplos Verilog gerados e compilados para PC

**Status atual: 27 testes pytest passam (18 parser/codegen + 6 testbenches + 2 topo sort + 1 compile-all)**

---

## 🔧 P0 — Correções rápidas

### 0.1 — Fix RP2040 build filter

**Estimativa:** 5 min
**Dependência:** Nenhuma

O build do RP2040 falha com `main` duplicado porque `testbench_*.c` não é excluído no filtro do `platformio.ini`. Adicionar `-<testbench_*>` no `build_src_filter` do `env:rp2040`.

### 0.2 — VCD smoke test

**Estimativa:** 15 min
**Dependência:** Nenhuma

O VCD writer existe (`firmware/lib/runtime/src/vcd_writer.c`) e é ativado via env var `VCD_OUT`, mas nunca foi testado. Criar um teste que executa um exemplo PC com `VCD_OUT=test.vcd` e verifica que o arquivo gerado é um VCD válido (cabeçalho, signals, mudanças de estado, `$dumpvars`, `$end`).

---

## 🎯 P1 — Alta prioridade

### 1.1 — Circuitos complexos no ESP32

**Estimativa:** 2h
**Dependência:** ESP32 conectado (/dev/ttyUSB0)
**Hardware:** ✅ disponível

Testar `tiny_cpu`, `uart_tx`, `pwm`, `param_counter` em hardware real:

- Gerar C via `python -m pc_tool.cli`
- Criar envs no `platformio.ini` (ex: `esp32-tinycpu`, `esp32-uarttx`, `esp32-pwm`)
- Adaptar `main_esp32.c` ou gerar mains dedicados
- Flash e telemetria para cada um

**Valida:** Codegen de ponta a ponta em hardware real para circuitos complexos.

### 1.2 — VCD integration test

**Estimativa:** 1h
**Dependência:** Nenhuma

Criar teste pytest que:
1. Executa um exemplo PC com `VCD_OUT` setado
2. Lê o arquivo .vcd gerado
3. Verifica:
   - Cabeçalho (`$date`, `$timescale`, `$var`)
   - Declarações de sinais (inputs, outputs, regs)
   - Pelo menos uma mudança de valor (`$dumpvars` + transições)
   - `$end` no final

Pode usar ferramentas como pyvcd ou parsing manual do formato.

### 1.3 — CSV stimulus para mais circuitos

**Estimativa:** 2h
**Dependência:** Nenhuma

Atualmente só existem CSVs e testbenches para `fsm_101` e `shift_register`. Criar para os demais circuitos que têm comportamento determinístico:

- `counter` — CSV com rst, contagem, wrap 15→0, reset
- `blinky` — CSV com rst, clock, esperar N ciclos, verificar toggle do LED
- `alu` — CSV com operações aritméticas e comparações
- `pwm` — CSV com duty cycle, enable, verificar saída
- `tiny_cpu` — CSV com instruções simples (NOP, ADD, LOAD, STORE)

Cada CSV deve ter checkpoints de saída esperada.

---

## 🟡 P2 — Médio prazo

### 2.1 — Parser: features faltantes

**Estimativa:** 4h
**Dependência:** Nenhuma

Adicionar suporte no parser/codegen para:

- `for` loops dentro de always blocks
- Operador ternário `cond ? a : b`
- Operadores de redução: `&a`, `|a`, `^a`, `~&a`, `~|a`, `~^a`
- Case equality: `===` / `!==` (tratar como `==` / `!=` com warning)
- LHS part select: `sig[a:b] = val` no codegen (já parseado)
- Memória/arrays: `reg [7:0] mem [0:255]`

Cada feature deve ter testes pytest no parser e codegen.

### 2.2 — Gerador de testbenches automático

**Estimativa:** 3h
**Dependência:** 1.3 (CSVs existentes)

Script Python que:
1. Lê um módulo Verilog
2. Gera CSV de estímulos (entradas aleatórias ou sistemáticas)
3. Executa o circuito C gerado (subprocess)
4. Opcional: executa simulação Verilog com Icarus/Verilator para golden output
5. Compara saídas e reporta diferenças

### 2.3 — Testbench de CI completo

**Estimativa:** 2h
**Dependência:** 0.1, 1.2, 1.3, 2.1

Criar script CI que roda todos os testes automaticamente:
- pytest (parser, codegen, testbenches, compilação, VCD)
- Compilação PC de todos os 13 exemplos
- Compilação ESP32 (pio run) para verificar sem hardware
- Compilação RP2040 (após fix 0.1)

---

## 🔵 P3 — Futuro

### 3.1 — RP2040 hardware bringup

**Prioridade:** Baixa
**Dependência:** Hardware RP2040 (indisponível)

- Adaptar `main_rp2040.c` com clock virtual (mesma abordagem do ESP32)
- Testar telemetria via USB CDC
- Gravar e testar no hardware quando disponível

### 3.2 — Hierarquia de módulos

**Prioridade:** Baixa
**Esforço:** Alto

Suporte a instanciação de submódulos no Verilog:
- `parser.py`: parse de instâncias (`module_name #(...) instance_name(...)`)
- `ast.py`: classe `ModuleInstance`
- `c_generator.py`: inline das instâncias ou chamadas de função

### 3.3 — Otimização de performance

**Prioridade:** Baixa
**Esforço:** Médio

O emulador roda a ~77kHz no ESP32 (abaixo dos 100kHz alvo). Possíveis otimizações:
- Usar `GPIO.out_w1ts`/`out_w1tc` em vez de `gpio_set_level` no ESP32
- Reduzir overhead da telemetria (menos formatação de strings)
- Loop principal em assembly otimizado ou uso do ULP coprocessador

---

## Resumo

| # | Tarefa | Prioridade | Esforço | Hardware |
|---|--------|-----------|---------|----------|
| 0.1 | Fix RP2040 build filter | 🔧 P0 | 5 min | N/A |
| 0.2 | VCD smoke test | 🔧 P0 | 15 min | N/A |
| 1.1 | Circuitos complexos no ESP32 | 🎯 P1 | 2h | ESP32 |
| 1.2 | VCD integration test | 🎯 P1 | 1h | N/A |
| 1.3 | CSV stimulus para mais circuitos | 🎯 P1 | 2h | N/A |
| 2.1 | Parser: features faltantes | 🟡 P2 | 4h | N/A |
| 2.2 | Gerador de testbenches | 🟡 P2 | 3h | N/A |
| 2.3 | CI completo | 🟡 P2 | 2h | N/A |
| 3.1 | RP2040 bringup | 🔵 P3 | Médio | RP2040 |
| 3.2 | Hierarquia de módulos | 🔵 P3 | Alto | N/A |
| 3.3 | Otimização de performance | 🔵 P3 | Médio | N/A |
