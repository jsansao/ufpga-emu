# Spec — GUI didática do ufpga-emu (v1)

*Intenção confirmada em `docs/intent/gui-didatica.md`. Stack e fluxos reaproveitam
o que já existe no repo: `pc_tool.cli`, `pc_tool.pinmap_gen`, envs `platformio.ini`,
protocolo serial (`vset`/`read`/`status`, telemetria `CLK/IN/OUT`).*

## 1. Objetivo

Permitir que um aluno sem experiência em terminal complete, dentro da aula,
o ciclo escrever → programar → ver rodando no ESP32, e explore os 26 circuitos
de exemplo sem tocar em terminal, JSON ou `platformio.ini`.

## 2. Modos

### Modo A — Visualizador de exemplos

- Lista os 26 circuitos embutidos (`examples/*.v`).
- Ao selecionar: exibe o fonte Verilog (somente leitura) + descrição curta.
- **Executar na simulação PC**: usa o CSV de estímulo quando existir
  (19 circuitos têm `stim_*.csv`); mostra evolução de inputs/outputs em texto.
  Circuitos sem CSV: exibe o fonte e permite programar no hardware, sem simulação.
- **Programar no ESP32** (se placa conectada): flasha o env correspondente e
  abre o monitor ao vivo (mesmo monitor do modo B).

### Modo B — Construtor (Verilog do zero → hardware)

Passos guiados, um por tela/etapa, sem terminal:

1. **Editar**: área de texto com exemplo inicial carregado. Sem syntax
   highlight no v1.
2. **Verificar**: roda o parser (`pc_tool` como biblioteca) e mostra erros
   de sintaxe/construção em linguagem simples. Só avança se passar.
3. **Mapear**: alocação automática (regras §4) + **tabela exibida**
   sinal → pino físico. Somente leitura no v1.
4. **Programar**: gera C + entrada JSON + regen + `pio run -t upload`
   com barra de progresso e log filtrado (só marcos: gerado, compilado,
   flashado, erro resumido).
5. **Monitorar**: telemetria ao vivo + botões de toggle por sinal de entrada
   (emite `vset`) + leitura dos outputs (via `read`). Sem caixa de comando
   textual no v1.

## 3. Alocador automático de pinos (ESP32)

- `clk` → 4, `rst` → 5 (convenção do repo; só se o circuito tiver o sinal).
- Demais inputs → pool de entrada na ordem dos pinmaps existentes;
  outputs → pool de saída. Determinístico para o mesmo Verilog.
- Restrições rígidas: nunca GPIOs 6–11 (SPI flash); 34–39 só como input;
  só pinos 2,4,5,12–19,21–23,25–27,32–39.
- Erro legível se faltar pino ("circuito precisa de N outputs, há M livres").
- Implementação: reaproveita `pinmap_gen.validate()`; a entrada gerada entra
  em `firmware/pinmaps/` como circuito comum (sem caminho especial).

## 4. Stack técnica

- **Tkinter (stdlib)** — zero dependência nova; lab Linux típico já tem
  (Debian: pacote `python3-tk`, incluído no setup do professor).
- **`pyserial`** (já em `requirements.txt`) para console e upload-monitor.
- **`pc_tool` importado como biblioteca** (parse, codegen, template, validate).
- **PlatformIO via subprocesso** para compilar/flashar (instalado pelo
  professor na imagem do lab; primeiro uso baixa toolchains — exigir setup
  pré-aula, não na hora).
- Alvo v1: **só ESP32** (`/dev/ttyUSB0`, 115200). due/esp8266/rp2040: nada no
  código impede, mas seleção de plataforma fica para versão futura.

## 5. Setup (professor, fora do app)

Imagem do lab com: Python 3.10+, `python3-tk`, `pip install -r requirements.txt`,
`pio` no PATH, toolchains ESP32 pré-baixadas (`pio run -e esp32-blinky` uma vez),
usuário no grupo `dialout`. O app não instala nada sozinho no v1.

## 6. Critérios de aceite

- [ ] Aluno sem experiência em terminal completa modo B de ponta a ponta em
      aula, sem o professor abrir terminal (critério didático, piloto).
- [ ] Os 26 exemplos abrem no modo A; os 19 com CSV simulam no PC.
- [ ] Modo B funciona para ao menos: combinacional simples (ex. `mux`),
      sequencial com clk/rst (ex. `counter`) e um com init especial
      (ex. `tiny_cpu`, `run=1` exibido no mapeamento).
- [ ] Erro de Verilog inválido aparece em linguagem simples antes de qualquer
      build; nada exige terminal em nenhum passo.
- [ ] `pytest tests/` continua 109/109 (a GUI não quebra o fluxo CLI).

## 7. Fora do escopo (v1)

Edição pino a pino; syntax highlight; Windows/macOS; due/esp8266/rp2040
selecionáveis; múltiplas placas; caixa de comando serial textual;
instalação de dependências pelo próprio app.

## 8. Decisões em aberto (não travam o v1)

- Descrições curtas dos 26 exemplos: escrever na mão ou gerar do Verilog?
- Toggle de inputs no monitor: botões por sinal (proposto) vs. sliders/switches
  gráficos — validar no piloto qual os alunos entendem mais rápido.
- Nome do app e onde ele mora no repo (`tools/gui/` proposto, a confirmar).
