"""Wrapper do pc_tool como biblioteca para a GUI.

Convenção: nenhuma função aqui chama sys.exit, imprime ou levanta exceção.
Tudo retorna (resultado, erro), com erro=None no sucesso e resultado=None
na falha. Feito para o loop da GUI (T2); o CLI original segue intocado.
"""
import contextlib
import io
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

EXAMPLES_DIR = os.path.join(ROOT, "examples")
EXAMPLES_SRC = os.path.join(ROOT, "firmware", "src", "examples")
HAL_SRC_DIR = os.path.join(ROOT, "firmware", "lib", "hal", "src")
RUNTIME_SRC_DIR = os.path.join(ROOT, "firmware", "lib", "runtime", "src")
HAL_INC_DIR = os.path.join(ROOT, "firmware", "lib", "hal", "include")
RUNTIME_INC_DIR = os.path.join(ROOT, "firmware", "lib", "runtime", "include")
FW_SRC_DIR = os.path.join(ROOT, "firmware", "src")

# CSVs com nome fora do padrão stim_<circuito>.csv
CSV_ALIASES = {"fsm_101": "fsm_detect.csv", "shift_register": "shift_full.csv"}

from pc_tool.parser.parser import ParseError
from pc_tool.parser.registry import ModuleRegistry
from pc_tool.parser.inliner import flatten_module
from pc_tool.codegen.c_generator import CGenerator


def _resolve_top(registry, top):
    mods = registry.all_modules()
    if not mods:
        return None, "nenhum modulo encontrado no Verilog"
    if top is None:
        if len(mods) != 1:
            names = ", ".join(m.name for m in mods)
            return None, f"multiplos modulos ({names}); especifique o top"
        top = mods[0].name
    module = registry.get(top)
    if module is None:
        return None, f'modulo top-level "{top}" nao encontrado'
    return module, None


def load_module(verilog_path, top=None):
    """Parse + flatten. Retorna ((modulo, ports), erro)."""
    if not os.path.exists(verilog_path):
        return None, f"arquivo nao encontrado: {verilog_path}"
    try:
        registry = ModuleRegistry()
        registry.parse_file(verilog_path)
    except ParseError as e:
        return None, f"erro de parsing: {e}"
    except Exception as e:  # noqa: BLE001 — fronteira da GUI nunca levanta
        return None, f"erro ao ler Verilog: {e}"
    module, err = _resolve_top(registry, top)
    if err:
        return None, err
    try:
        flat = flatten_module(module, registry) if module.instances else module
    except RuntimeError as e:
        return None, f"erro ao achatar instancias: {e}"
    ports = [(p.name, p.direction, p.width) for p in flat.ports]
    return (flat, ports), None


def generate_c(verilog_path, output_path, top=None):
    """Gera circuit_X.c. Retorna None no sucesso ou mensagem de erro."""
    loaded, err = load_module(verilog_path, top)
    if err:
        return err
    flat, _ports = loaded
    try:
        c_code = CGenerator(flat).generate()
    except Exception as e:  # noqa: BLE001
        return f"erro no codegen: {e}"
    try:
        with open(output_path, "w") as f:
            f.write(c_code)
    except OSError as e:
        return f"erro ao escrever {output_path}: {e}"
    return None


def template_entry(verilog_path, top=None):
    """Entrada JSON do circuito. Retorna ((nome, entry), erro)."""
    try:
        from pc_tool.pinmap_gen import make_template
        try:
            name, entry = make_template(verilog_path, top)
        except SystemExit as e:
            return None, str(e.code) if e.code else "erro no template"
        return (name, entry), None
    except Exception as e:  # noqa: BLE001
        return None, f"erro no template: {e}"


def regen_headers():
    """Regenera pinmap_*.h. Retorna (lista de plataformas, erro)."""
    try:
        from pc_tool import pinmap_gen
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            plats = []
            for fn in sorted(os.listdir(pinmap_gen.PINMAP_DIR)):
                if not fn.endswith(".json"):
                    continue
                plat = fn[:-5]
                with open(os.path.join(pinmap_gen.PINMAP_DIR, fn)) as f:
                    import json
                    data = json.load(f)
                pinmap_gen.validate(plat, data)
                out = os.path.join(pinmap_gen.SRC_DIR, f"pinmap_{plat}.h")
                with open(out, "w") as f:
                    f.write(pinmap_gen.gen_header(plat, data))
                plats.append(plat)
        return plats, None
    except AssertionError as e:
        return None, f"pinmap invalido: {e}"
    except Exception as e:  # noqa: BLE001
        return None, f"erro ao regenerar headers: {e}"


def example_csv(circuit):
    """Caminho do CSV de estímulo do exemplo, ou None se não houver."""
    for cand in (f"stim_{circuit}.csv", CSV_ALIASES.get(circuit, "")):
        if cand and os.path.exists(os.path.join(EXAMPLES_DIR, cand)):
            return os.path.join(EXAMPLES_DIR, cand)
    return None


def example_has_pc_sim(circuit):
    """True se há <circuit>.c + <circuit>_main.c para simulação PC."""
    return (os.path.exists(os.path.join(EXAMPLES_SRC, f"{circuit}.c"))
            and os.path.exists(os.path.join(EXAMPLES_SRC, f"{circuit}_main.c")))


def compile_example(circuit, workdir="/tmp/ufpga_gui"):
    """Compila o exemplo p/ PC. Retorna (caminho do binário, erro)."""
    os.makedirs(workdir, exist_ok=True)
    binary = os.path.join(workdir, f"sim_{circuit}")
    hal_src = [os.path.join(HAL_SRC_DIR, f) for f in
               ("hal_gpio.c", "hal_timer.c", "hal_stimulus.c",
                "hal_mutex.c", "hal_serial.c")]
    runtime_src = [os.path.join(RUNTIME_SRC_DIR, f) for f in
                   ("emulator.c", "pin_map.c", "telemetry.c", "vcd_writer.c")]
    src = [os.path.join(EXAMPLES_SRC, f"{circuit}.c"),
           os.path.join(EXAMPLES_SRC, f"{circuit}_main.c")]
    cmd = (["gcc", "-I" + HAL_INC_DIR, "-I" + RUNTIME_INC_DIR,
            "-I" + FW_SRC_DIR]
           + src + hal_src + runtime_src
           + ["-lpthread", "-o", binary])
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        return None, f"falha ao invocar gcc: {e}"
    if r.returncode != 0:
        return None, "erro de compilação:\n" + r.stderr.decode()[-2000:]
    return binary, None


def run_example(binary, csv=None, seconds=2):
    """Roda o binário capturando stdout. Retorna (texto, erro)."""
    env = os.environ.copy()
    if csv:
        env["STIMULUS_CSV"] = csv
    try:
        proc = subprocess.Popen(
            [binary], env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        try:
            out, _ = proc.communicate(timeout=seconds)
            return out, None
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                out, _ = proc.communicate(timeout=5)
            except Exception:  # noqa: BLE001
                proc.kill()
                out, _ = proc.communicate()
            return out, None
    except Exception as e:  # noqa: BLE001
        return None, f"falha ao executar simulação: {e}"


# Circuitos originais: a GUI nunca sobrescreve (só cria/atualiza os demais).
BUILTINS = frozenset({
    "counter", "fsm_101", "shift_register", "param_counter", "pwm",
    "uart_tx", "tiny_cpu", "task_func", "reduction", "priority_encoder",
    "decoder", "mixed", "mux", "mux2", "negedge_counter", "sign_extend",
    "concat_multi", "part_select_lhs", "adder_n", "alu", "case_equality",
    "not_keyword", "localparam_example", "module_inst", "repeat_example",
    "blinky",
})

PIO = (os.environ.get("PIO") or shutil.which("pio")
       or os.path.expanduser("~/.venvs/pio/bin/pio"))
PLATFORMIO_INI = os.path.join(ROOT, "platformio.ini")
GUI_ENV_MARK_BEGIN = "# >>> uFPGA-GUI (gerado, nao editar)"
GUI_ENV_MARK_END = "# <<< uFPGA-GUI"


def _env_block(name):
    macro = f"EMU_CIRCUIT_{name.upper()}"
    return (
        f"{GUI_ENV_MARK_BEGIN}\n"
        f"[env:esp32-gui-{name}]\n"
        "platform = espressif32\n"
        "board = esp32dev\n"
        "framework = espidf\n"
        "build_src_filter = +<*> -<*rp2040*> -<stim_test_*> -<examples/>\n"
        "board_build.f_cpu = 240000000L\n"
        "monitor_speed = 115200\n"
        "build_flags = \n"
        "    -I${PROJECT_DIR}/firmware/lib/hal/include\n"
        "    -I${PROJECT_DIR}/firmware/lib/runtime/include\n"
        f"    -D{macro}\n"
        f"{GUI_ENV_MARK_END}\n"
    )


def ensure_env(name):
    """Garante env esp32-gui-<name> no platformio.ini. Retorna (env, erro)."""
    env = f"esp32-gui-{name}"
    macro = f"EMU_CIRCUIT_{name.upper()}"
    try:
        with open(PLATFORMIO_INI) as f:
            ini = f.read()
    except OSError as e:
        return None, f"erro ao ler platformio.ini: {e}"
    if f"[env:{env}]" in ini:
        return env, None
    if macro in ini:
        return None, f'já existe env com {macro} — renomeie o módulo'
    block = _env_block(name)
    if not ini.endswith("\n"):
        ini += "\n"
    try:
        with open(PLATFORMIO_INI, "a") as f:
            f.write("\n" + block)
    except OSError as e:
        return None, f"erro ao escrever platformio.ini: {e}"
    return env, None


def program_pipeline(name, ports, verilog_path, log, plat="esp32",
                     upload_port="/dev/ttyUSB0"):
    """Fluxo completo até o flash. log(msg) recebe progresso. Retorna erro ou None."""
    import json
    from pc_tool import pinmap_gen

    if plat != "esp32":
        return f"programação GUI só para ESP32 no v1 (pedido: {plat})"
    if name in BUILTINS:
        return (f'módulo "{name}" é um exemplo embutido — '
                "renomeie o módulo p/ programar sua versão")
    if not os.path.exists(upload_port):
        return f"placa não encontrada em {upload_port} — conecte o ESP32"
    if not (os.path.exists(PIO) or shutil.which(PIO)):
        return f"platformio não encontrado ({PIO})"

    log(f"[1/5] gerando circuit_{name}.c ...")
    err = generate_c(verilog_path, os.path.join(FW_SRC_DIR, f"circuit_{name}.c"))
    if err:
        return err

    log("[2/5] alocando pinos ...")
    from allocator import allocate
    entry, err = allocate(ports)
    if err:
        return err

    log("[3/5] atualizando firmware/pinmaps/esp32.json ...")
    json_path = os.path.join(pinmap_gen.PINMAP_DIR, "esp32.json")
    try:
        with open(json_path) as f:
            data = json.load(f)
        data[name] = entry
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except (OSError, ValueError) as e:
        return f"erro no pinmap JSON: {e}"

    log("[4/5] regenerando headers ...")
    _, err = regen_headers()
    if err:
        return err

    log("[5/5] compilando e gravando (pode levar ~1 min) ...")
    env, err = ensure_env(name)
    if err:
        return err
    try:
        proc = subprocess.Popen(
            [PIO, "run", "-t", "upload", "-e", env,
             "--upload-port", upload_port],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True)
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line and ("SUCCESS" in line or "FAILED" in line or "error" in line.lower()
                         or "Hash of data" in line or "Writing at" in line):
                log("  " + line[-160:])
        rc = proc.wait(timeout=600)
    except subprocess.TimeoutExpired:
        proc.kill()
        return "timeout no upload (>10 min)"
    except Exception as e:  # noqa: BLE001
        return f"falha no upload: {e}"
    if rc != 0:
        return f"upload falhou (rc={rc}) — veja o log acima"
    log("pronto! circuito no ESP32.")
    return None


TELEMETRY_RE = re.compile(
    r"CLK=(\d+)\s+IN=(0x[0-9A-Fa-f]+)\s+OUT=(0x[0-9A-Fa-f]+)\s+"
    r"REG0=(0x[0-9A-Fa-f]+)\s+FREQ=(\d+)Hz")


def parse_telemetry(line):
    """Linha CLK=... -> dict, ou None se não for telemetria."""
    m = TELEMETRY_RE.search(line)
    if not m:
        return None
    clk, inp, out, reg0, freq = m.groups()
    return {"clk": int(clk), "in": int(inp, 16), "out": int(out, 16),
            "reg0": int(reg0, 16), "freq": int(freq)}


class SerialLink:
    """Console serial com thread de leitura (T8). Eventos via poll().

    Eventos: ("telemetry", dict), ("line", str) p/ respostas OK/ERR/banner.
    Escrita (send) é síncrona e rápida — pode ir da main thread com lock.
    """

    def __init__(self, port="/dev/ttyUSB0", baud=115200):
        self.port = port
        self.baud = baud
        self._ser = None
        self._thread = None
        self._running = False
        self._events: queue.Queue = queue.Queue()
        self._wlock = threading.Lock()

    def connect(self):
        """Abre a porta e inicia a leitura. Retorna erro ou None."""
        if self._thread and self._thread.is_alive():
            return None
        try:
            import serial
        except ImportError:
            return "pyserial não instalado (pip install pyserial)"
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=0.2)
        except Exception as e:  # noqa: BLE001
            return f"não abri {self.port}: {e}"
        time.sleep(0.3)
        try:
            self._ser.reset_input_buffer()
        except Exception:  # noqa: BLE001
            pass
        self._running = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        return None

    def close(self):
        self._running = False
        thread, self._thread = self._thread, None
        if thread and thread.is_alive():
            thread.join(timeout=1.0)
        ser, self._ser = self._ser, None
        if ser:
            try:
                ser.close()
            except Exception:  # noqa: BLE001
                pass

    @property
    def alive(self):
        return bool(self._thread and self._thread.is_alive())

    def send(self, cmd):
        """Envia comando (sem \\n). Retorna erro ou None."""
        if not self._ser:
            return "desconectado"
        try:
            with self._wlock:
                self._ser.write((cmd + "\n").encode())
            return None
        except Exception as e:  # noqa: BLE001
            return f"falha de escrita: {e}"

    def poll(self):
        """Drena eventos pendentes. Só da main thread."""
        out = []
        try:
            while True:
                out.append(self._events.get_nowait())
        except queue.Empty:
            pass
        return out

    def _reader(self):
        assert self._ser is not None
        while self._running:
            try:
                raw = self._ser.readline()
            except Exception:  # noqa: BLE001
                break
            if not raw:
                continue
            try:
                line = raw.decode("utf-8", errors="replace").strip()
            except Exception:  # noqa: BLE001
                continue
            if not line:
                continue
            tele = parse_telemetry(line)
            if tele:
                self._events.put(("telemetry", tele))
            elif len(line) < 160 and (
                    line.startswith("OK ") or line.startswith("ERR")
                    or "uFPGA-Emu" in line):
                self._events.put(("line", line))
