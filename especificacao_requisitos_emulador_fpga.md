# Documento de Especificação de Requisitos do Sistema (SRS)

## Projeto: Emulador de Hardware Baseado em Microcontroladores de 32-bits (uFPGA-Emu)
**Versão:** 1.0  
**Data:** 27 de Junho de 2026  
**Plataformas Alvo:** Espressif ESP32 & Raspberry Pi Pico (RP2040)  
**Linguagens de Entrada:** Verilog / SystemVerilog / VHDL  

---

## 1. Introdução

### 1.1 Objetivo do Documento
Este documento define as especificações de requisitos funcionais, não funcionais e arquiteturais para o desenvolvimento de um ecossistema capaz de simular/emular o comportamento de circuitos digitais descritos em linguagens de descrição de hardware (HDLs) utilizando microcontroladores comerciais de alto desempenho (ESP32 e RP2040).

### 1.2 Escopo do Projeto
O sistema consiste em um fluxo de trabalho em duas etapas:
1. **Ferramenta de PC (Frente de Compilação):** Responsável por receber o código RTL (VHDL/Verilog), realizar a síntese ou tradução lógica e gerar um modelo executável otimizado em código C/C++.
2. **Firmware do Microcontrolador (Motor de Execução):** Código estruturado para rodar de forma determinística e em tempo real nos microcontroladores alvo, mapeando os pinos virtuais do hardware descrito em pinos de Entrada/Saída (I/O) físicos do chip.

---

## 2. Descrição Geral do Sistema

O sistema visa preencher uma lacuna educacional e de prototipagem rápida de baixo custo. Em vez de utilizar placas de FPGA de alto valor monetário para testar circuitos de baixa ou média complexidade, o usuário utiliza microcontroladores de arquitetura dual-core de 32 bits para emular o comportamento lógico ciclo a ciclo.

### 2.1 Arquitetura Proposta do Fluxo de Trabalho
* **Fase 1 (Síntese e Geração):** Tradução do código RTL para um modelo ciclo-exato (*cycle-accurate*) usando ferramentas como o **Verilator** ou síntese lógica baseada no **Yosys** para gerar uma *netlist* em formato intermediário.
* **Fase 2 (Embebição):** Compilação cruzada do modelo lógico gerado junto com o HAL (*Hardware Abstraction Layer*) específico do microcontrolador escolhido (ESP-IDF ou Pico SDK).
* **Fase 3 (Execução):** Leitura contínua das entradas físicas, avaliação sequencial das funções booleanas que representam as portas lógicas e atualização imediata das saídas físicas.

---

## 3. Requisitos Funcionais (RF)

| ID | Requisito Funcional | Descrição | Prioridade |
| :--- | :--- | :--- | :--- |
| **RF01** | Suporte a Linguagem de Descrição de Hardware | O sistema deve aceitar arquivos de entrada em Verilog padrão (IEEE 1364-2005) ou SystemVerilog. O suporte a VHDL será tratado via conversão prévia. | Alta |
| **RF02** | Tradução para Modelo Executável C/C++ | O pipeline de software no PC deve converter automaticamente a descrição de hardware em código C++ otimizado que represente fielmente a tabela verdade e o comportamento síncrono do circuito. | Alta |
| **RF03** | Mapeamento de Pinos (Pinout Binding) | O sistema deve permitir que o desenvolvedor defina um arquivo de configuração (ex: JSON ou atributos no código) vinculando os sinais de `input` e `output` do circuito digital a pinos de GPIO específicos do ESP32 ou RP2040. | Alta |
| **RF04** | Loop de Execução Isolado (Dual-Core) | O firmware embarcado deve isolar a execução do laço de emulação lógica em um núcleo do processador exclusivo (**Core 1**), impedindo interrupções de rotinas de sistema. | Alta |
| **RF05** | Emulação de Clock Síncrono | O motor de execução deve implementar uma rotina de clock virtual interno ou permitir que um pino de GPIO físico atue como o sinal de `CLK` externo para sincronizar os Flip-Flops emulados. | Alta |
| **RF06** | Interface de Diagnóstico / Telemetria | O **Core 0** do microcontrolador deve gerenciar uma interface de comunicação Serial/USB para enviar estados internos das variáveis lógicas ao PC para depuração em tempo de execução. | Média |
| **RF07** | Otimização via Blocos PIO (Apenas RP2040) | No caso do chip RP2040, o sistema deve utilizar as máquinas de estado programáveis (PIO) para realizar a amostragem ultra-rápida e determinística dos pinos de entrada antes de passá-los ao núcleo de computação. | Média |

---

## 4. Requisitos Não Funcionais (RNF)

| ID | Requisito Não Funcional | Descrição | Prioridade |
| :--- | :--- | :--- | :--- |
| **RNF01** | Frequência Mínima de Operação Virtual | O circuito emulado deve rodar com uma frequência de amostragem/avaliação lógica mínima de **100 kHz** para circuitos de complexidade média, visando aplicações didáticas em laboratório. | Alta |
| **RNF02** | Determinismo Temporal (Jitter Mínimo) | O tempo decorrido entre a leitura da entrada, processamento lógico e escrita na saída (latência de I/O) deve possuir um jitter inferior a 10% do período de clock emulado. | Alta |
| **RNF03** | Restrição de Memória RAM | O código C/C++ gerado para o modelo não deve exceder **128 KB** de pegada de memória SRAM estática, garantindo total compatibilidade com os 264 KB do RP2040 e 520 KB do ESP32. | Alta |
| **RNF04** | Portabilidade do Código do Modelo | O arquivo contendo o comportamento lógico gerado pela ferramenta de PC deve ser genérico e escrito em C ANSI puro, permitindo compilação tanto em arquiteturas Xtensa (ESP32) quanto ARM Cortex-M0+ (RP2040). | Média |
| **RNF05** | Segurança de Concorrência | A troca de dados entre o **Core 0** (comunicação/telemetria) e o **Core 1** (loop de emulação) deve utilizar primitivas de hardware seguras (*hardware mutexes* ou filas sem bloqueio) para evitar condições de corrida (*race conditions*). | Alta |

---

## 5. Restrições do Sistema

1. **Paralelismo Real Limitado:** Diferente de uma FPGA real que possui circuitos físicos paralelos operando de forma instantânea, o microcontrolador executará a lógica sequencialmente. Portas lógicas que dependem uma da outra serão avaliadas sequencialmente na ordem topológica gerada pela síntese de software.
2. **Capacidade Lógica:** Circuitos que demandem milhares de LUTs (como processadores de 32 bits complexos com caches e pipelines profundos) podem ter sua velocidade severamente degradada ou falhar em caber nos limites de memória do microcontrolador.
3. **Ausência de Blocos de Hardware Especializados:** O microcontrolador não emulará blocos nativos de DSP ou RAM de porta dupla da FPGA nativamente; toda essa lógica será convertida em variáveis em memória RAM e operações aritméticas da CPU.

---

## 6. Configurações de Hardware e Software Recomendadas

### Hardware para Testes:
* Placa de desenvolvimento baseada em **ESP32-WROOM-32** (Clock de 240 MHz).
* Placa **Raspberry Pi Pico** ou similar com chip **RP2040** (Clock de 133 MHz).

### Toolchain de Desenvolvimento:
* **PC Side:** Verilator (v5.0 ou superior) rodando em ambiente Linux (Ubuntu/Debian ou WSL2). Python 3.10+ para automação de scripts e mapeamento de pinos.
* **Microcontroller Side:** VS Code com extensões PlatformIO, utilizando o framework ESP-IDF para o ESP32 e o Pico SDK / Arduino-Pico Core para o RP2040.
