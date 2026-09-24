# Intenção confirmada — GUI didática do ufpga-emu

*Confirmada pelo usuário em 2026-09-23 via entrevista (skill interview-me).
Fonte: pedido "criar uma gui para utilização mais amigável do ufpga-emu".*

- **Outcome:** app desktop em Python (Linux) para o ufpga-emu com dois modos:
  (a) visualizador dos exemplos embutidos e (b) fluxo Verilog-do-zero →
  programação do ESP32, com alocação automática de pinos apenas exibida.
- **User:** alunos de práticas de laboratório em curso de FPGA/Verilog.
- **Why now:** tornar o ufpga-emu usável em aula sem a barreira de
  terminal + JSON + `platformio.ini`.
- **Success:** piloto em sala — alunos sem experiência em terminal completam
  o ciclo (escrever → programar → ver rodando) dentro da aula, sem o
  professor abrir terminal.
- **Constraint:** Linux + ESP32 na configuração default; due/esp8266/rp2040
  ficam para versões futuras.
- **Out of scope (v1):** tela de atribuição pino a pino; empacotamento fora
  do Linux; outros alvos de hardware.

Decisões da entrevista:
- Alocação automática inicialmente, mas com o mapeamento exibido.
- Dois modos confirmados: (a) visualizador + (b) construtor.
