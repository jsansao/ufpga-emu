# Setup do laboratório — GUI didática (professor)

Preparar a imagem **uma vez**; o aluno só abre o app. Tudo abaixo roda em
Linux com ESP32 (`/dev/ttyUSB0`, CH340).

## 1. Pacotes do sistema

```bash
sudo apt install python3-tk  # Tkinter (o resto é pip)
```

## 2. Dependências Python + PlatformIO

```bash
pip install -r requirements.txt  # pytest, platformio, pyserial
export PATH="$HOME/.local/bin:$PATH"  # se usou --break-system-packages
# ou use o venv existente: ~/.venvs/pio/bin/pio
```

## 3. Toolchains ESP32 (pré-baixar — exige internet, faça antes da aula)

```bash
~/.venvs/pio/bin/pio run -e esp32-blinky
```

Sem isso, o primeiro "Programar" da aula trava baixando a plataforma.

## 4. Permissão da serial

```bash
sudo usermod -aG dialout $USER  # logout/login depois
ls -la /dev/ttyUSB0  # deve mostrar grupo dialout
```

## 5. Verificação pré-aula (5 min)

```bash
python3 -m pytest tests/ -q                    # esperado: 114 passed
timeout 20 xvfb-run -a python3 tools/gui/app.py &  # abre? (ou com display)
python3 scripts/serial_monitor.py --port /dev/ttyUSB0 --seconds 6  # placa responde?
```

## Checklist do piloto (critério didático da spec)

- [ ] Aluno sem experiência em terminal abre só o app (nada de terminal).
- [ ] Modo A: abre um exemplo, lê o fonte, roda a simulação PC.
- [ ] Modo B: escreve/edita Verilog, Verificar OK, vê a tabela de pinos,
      Programa o ESP32, alterna uma entrada no monitor e vê a saída mudar.
- [ ] Tudo acima dentro de **uma aula**, sem o professor abrir terminal.
- [ ] Falhas anotadas: onde o aluno travou? (vira ajuste da GUI, não do aluno).

## Problemas conhecidos (v1)

- Só ESP32; due/esp8266/rp2040 não aparecem na GUI.
- `clk`/`rst` não têm toggle no monitor (de propósito).
- Sem internet na hora: programar funciona se o passo 3 foi feito antes.
- Placa fora de `/dev/ttyUSB0`: a GUI ainda não deixa trocar a porta.
