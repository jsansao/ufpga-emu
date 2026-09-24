#!/usr/bin/env python3
"""uFPGA-Emu Lab — GUI didática (esqueleto T1).

Uso:
    python3 tools/gui/app.py
"""
import queue
import threading
import tkinter as tk
from tkinter import ttk

from pctool import (ROOT, compile_example, example_has_pc_sim,
                    run_example)


def list_examples():
    import os
    d = os.path.join(ROOT, "examples")
    return sorted(f[:-2] for f in os.listdir(d) if f.endswith(".v"))


def read_example_source(name):
    import os
    with open(os.path.join(ROOT, "examples", name + ".v")) as f:
        return f.read()


class LogPane(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._queue: queue.Queue = queue.Queue()
        self.text = tk.Text(self, height=8, state="disabled")
        scroll = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.after(100, self._flush)

    def log(self, msg):
        """Só da main thread."""
        self.text.configure(state="normal")
        self.text.insert("end", msg + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def post(self, msg):
        """Thread-safe: worker threads usam este."""
        self._queue.put(msg)

    def _flush(self):
        try:
            while True:
                self.log(self._queue.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._flush)


class ViewerTab(ttk.Frame):
    """Modo A — visualizador de exemplos com simulação PC."""

    def __init__(self, parent, log):
        super().__init__(parent)
        self._log = log
        self._sim_thread = None
        self._sim_result = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=4, pady=4)
        ttk.Label(left, text="Exemplos").pack(anchor="w")
        self.names = list_examples()
        self.listbox = tk.Listbox(left, height=20, exportselection=False)
        for n in self.names:
            self.listbox.insert("end", n)
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        right = ttk.Frame(self)
        right.pack(side="right", fill="both", expand=True, padx=4, pady=4)
        ttk.Label(right, text="Fonte Verilog (somente leitura)").pack(anchor="w")
        self.source = tk.Text(right, height=12, state="disabled")
        self.source.pack(fill="both", expand=True)

        stimframe = ttk.LabelFrame(right, text="Testbench (estímulo CSV — editável)")
        stimframe.pack(fill="x", padx=0, pady=4)
        self.stim = tk.Text(stimframe, height=5)
        self.stim.pack(fill="both", expand=True)
        self.stim_hint = ttk.Label(stimframe, text="")
        self.stim_hint.pack(anchor="w")

        simrow = ttk.Frame(right)
        simrow.pack(fill="x", pady=4)
        self.sim_button = ttk.Button(simrow, text="Simular no PC",
                                     command=self._on_simulate)
        self.sim_button.pack(side="left")
        self.sim_status = ttk.Label(simrow, text="")
        self.sim_status.pack(side="left", padx=8)

        ttk.Label(right, text="Trace da simulação").pack(anchor="w")
        self.trace = tk.Text(right, height=6, state="disabled")
        self.trace.pack(fill="both", expand=True)

        if self.names:
            self.listbox.selection_set(0)
            self._show(self.names[0])

    def _current(self):
        sel = self.listbox.curselection()
        return self.names[sel[0]] if sel else None

    def _on_select(self, _event):
        name = self._current()
        if name:
            self._show(name)

    def _show(self, name):
        try:
            src = read_example_source(name)
        except OSError as e:
            self._log(f"erro ao ler exemplo: {e}")
            return
        self.source.configure(state="normal")
        self.source.delete("1.0", "end")
        self.source.insert("end", src)
        self.source.configure(state="disabled")
        from pctool import stimulus_text
        text, err = stimulus_text(name)
        self.stim.delete("1.0", "end")
        if err:
            self.stim_hint.configure(text="")
            self._log(f"estímulo de {name}: {err}")
        elif text is None:
            self.stim_hint.configure(
                text="sem estímulo embutido — escreva o seu ou simule sem")
        else:
            self.stim.insert("end", text)
            self.stim_hint.configure(
                text="estímulo do exemplo — pode editar e simular de novo")

    def _set_trace(self, text):
        self.trace.configure(state="normal")
        self.trace.delete("1.0", "end")
        self.trace.insert("end", text)
        self.trace.configure(state="disabled")

    def _on_simulate(self):
        name = self._current()
        if name is None:
            return
        if not example_has_pc_sim(name):
            self.sim_status.configure(text="sem simulação PC para este exemplo")
            self._log(f"{name}: sem <name>.c + <name>_main.c em firmware/src/examples/")
            return
        if self._sim_thread and self._sim_thread.is_alive():
            return
        from pctool import example_signals, validate_stimulus
        signals, err = example_signals(name)
        if err:
            self.sim_status.configure(text="sem simulação PC para este exemplo")
            self._log(f"{name}: {err}")
            return
        edited = self.stim.get("1.0", "end")
        expanded, verr = validate_stimulus(edited, signals)
        if verr:
            self.sim_status.configure(text="testbench inválido — veja o trace")
            self._set_trace(f"Testbench com problema:\n{verr}")
            self._log(f"testbench inválido p/ {name}: {verr[:150]}")
            return
        csv_path = None
        if expanded is not None:
            import os
            import tempfile
            csv_path = os.path.join(tempfile.gettempdir(), "ufpga_gui_stim.csv")
            try:
                with open(csv_path, "w") as f:
                    f.write(expanded)
            except OSError as e:
                self.sim_status.configure(text="falhou (ver trace)")
                self._set_trace(f"não consegui salvar o testbench: {e}")
                return
        self.sim_button.configure(state="disabled")
        self.sim_status.configure(text="compilando...")
        self._sim_result = None

        def work():
            binary, err = compile_example(name)
            if err:
                self._sim_result = ("erro", err)
                return
            self._sim_result = ("compilado", None)
            out, err = run_example(binary, csv_path, seconds=3)
            self._sim_result = ("pronto", out if err is None else f"erro: {err}")

        self._sim_thread = threading.Thread(target=work, daemon=True)
        self._sim_thread.start()
        self.after(150, self._poll_sim)

    def _poll_sim(self):
        if self._sim_thread and self._sim_thread.is_alive():
            if self._sim_result and self._sim_result[0] == "compilado":
                self.sim_status.configure(text="executando (3s)...")
            self.after(150, self._poll_sim)
            return
        if self._sim_result:
            state, payload = self._sim_result
            if state == "pronto":
                self._set_trace(payload or "(sem saída)")
                n = len((payload or "").splitlines())
                self.sim_status.configure(text=f"concluído ({n} linhas)")
                self._log(f"simulação concluída: {n} linhas de trace")
            else:
                self._set_trace(payload or "erro desconhecido")
                self.sim_status.configure(text="falhou (ver trace)")
                self._log(f"falha na simulação: {(payload or '')[:200]}")
        self.sim_button.configure(state="normal")


class BuilderTab(ttk.Frame):
    """Modo B — Verilog do zero ao hardware (mapear/programar em T7-T8)."""

    DEFAULT_SOURCE = """\
module meu_circuito(
    input wire clk,
    input wire rst,
    input wire a,
    output wire y
);
    reg q;
    always @(posedge clk) begin
        if (rst)
            q <= 1'b0;
        else
            q <= a;
    end
    assign y = q;
endmodule
"""

    def __init__(self, parent, log, post):
        super().__init__(parent)
        self._log = log
        self._post = post  # thread-safe (worker -> main via fila)
        self._ports = None
        self._module = None
        self._verilog_path = None
        self._mapped = None
        self._prog_thread = None
        self._prog_error = None

        ttk.Label(self, text="Seu Verilog").pack(anchor="w", padx=4)
        self.editor = tk.Text(self, height=14)
        self.editor.pack(fill="both", expand=True, padx=4)
        self.editor.insert("end", self.DEFAULT_SOURCE)

        btnrow = ttk.Frame(self)
        btnrow.pack(fill="x", pady=4, padx=4)
        self.verify_button = ttk.Button(btnrow, text="Verificar",
                                        command=self._on_verify)
        self.verify_button.pack(side="left")
        self.map_button = ttk.Button(btnrow, text="Mapear pinos",
                                     command=self._on_map, state="disabled")
        self.map_button.pack(side="left", padx=4)
        self.prog_button = ttk.Button(btnrow, text="Programar ESP32",
                                      command=self._on_program, state="disabled")
        self.prog_button.pack(side="left")
        self.verify_status = ttk.Label(btnrow, text="")
        self.verify_status.pack(side="left", padx=8)

        ttk.Label(self, text="Resultado").pack(anchor="w", padx=4)
        self.result = tk.Text(self, height=6, state="disabled")
        self.result.pack(fill="x", padx=4, pady=(0, 4))

        monrow = ttk.Frame(self)
        monrow.pack(fill="x", pady=2, padx=4)
        self.mon_button = ttk.Button(monrow, text="Conectar monitor",
                                     command=self._on_monitor, state="disabled")
        self.mon_button.pack(side="left")
        self.mon_status = ttk.Label(monrow, text="")
        self.mon_status.pack(side="left", padx=8)

        self.mon_frame = ttk.Frame(self)
        self.mon_frame.pack(fill="x", padx=4)
        self._link = None
        self._out_labels = {}
        self._in_state = {}

    def _set_result(self, text):
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("end", text)
        self.result.configure(state="disabled")

    def _on_verify(self):
        import os
        import tempfile
        from pctool import load_module
        src = self.editor.get("1.0", "end")
        tmp = os.path.join(tempfile.gettempdir(), "ufpga_gui_check.v")
        try:
            with open(tmp, "w") as f:
                f.write(src)
        except OSError as e:
            self._set_result(f"não consegui salvar p/ verificar: {e}")
            return
        (loaded, err) = load_module(tmp)
        if err:
            self._ports = None
            self._module = None
            self._verilog_path = None
            self._mapped = None
            self.map_button.configure(state="disabled")
            self.prog_button.configure(state="disabled")
            self.verify_status.configure(text="erro — veja abaixo")
            self._set_result(f"Verilog com problema:\n{err}\n\n"
                             "Dica: confira parênteses, ';' no fim das linhas "
                             "e se todos os sinais usados foram declarados.")
            self._log(f"verificação falhou: {err[:120]}")
            return
        flat, ports = loaded
        self._ports = ports
        self._module = flat.name
        self._verilog_path = tmp
        self._mapped = None
        self.map_button.configure(state="normal")
        self.prog_button.configure(state="disabled")
        lines = [f"OK! Módulo '{flat.name}' entendido.",
                 f"Sinais ({len(ports)}):"]
        for name, direction, width in ports:
            lines.append(f"  {direction:6s} {name}" + (f"[{width}]" if width > 1 else ""))
        self.verify_status.configure(text=f"OK — módulo '{flat.name}'")
        self._set_result("\n".join(lines) + "\n\nPróximo: Mapear pinos.")
        self._log(f"verificado: {flat.name} ({len(ports)} sinais)")

    def _on_map(self):
        from allocator import allocate
        if not self._ports:
            return
        entry, err = allocate(self._ports)
        if err:
            self._set_result(f"não deu p/ alocar pinos:\n{err}")
            self._log(f"alocação falhou: {err[:150]}")
            return
        self._mapped = (self._module, entry)
        lines = [f"Pinos automáticos p/ '{self._module}' (ESP32, somente leitura):"]
        for p in entry["pins"]:
            lines.append(f"  {p['name']:16s} -> GPIO {p['pin']}")
        if entry["virtual_init"]:
            lines.append("Init: " + ", ".join(
                f"{k}={v}" for k, v in entry["virtual_init"].items()))
        self._set_result("\n".join(lines) + "\n\nPróximo: Programar ESP32.")
        self.prog_button.configure(state="normal")
        self._log(f"mapeados {len(entry['pins'])} sinais de '{self._module}'")

    def _on_program(self):
        from pctool import program_pipeline
        if not self._mapped or not self._verilog_path:
            return
        if self._prog_thread and self._prog_thread.is_alive():
            return
        name, _entry = self._mapped
        self.prog_button.configure(state="disabled")
        self.verify_status.configure(text="programando... (até ~2 min)")
        self._prog_error = None
        vpath = self._verilog_path
        ports = self._ports

        def work():
            try:
                self._prog_error = program_pipeline(
                    name, ports, vpath, self._post)
            except Exception as e:  # noqa: BLE001 — worker nunca falha muda
                self._prog_error = f"erro interno: {e}"

        self._prog_thread = threading.Thread(target=work, daemon=True)
        self._prog_thread.start()
        self.after(500, self._poll_prog)

    def _poll_prog(self):
        if self._prog_thread and self._prog_thread.is_alive():
            self.after(500, self._poll_prog)
            return
        if self._prog_error:
            self.verify_status.configure(text="falhou — veja o log")
            self._set_result(f"Programação falhou:\n{self._prog_error}")
        else:
            self.verify_status.configure(text="no ESP32! Conecte o monitor.")
            self._set_result("Circuito programado no ESP32.\n\nPróximo: Conectar monitor.")
            self.mon_button.configure(state="normal")
        self.prog_button.configure(state="normal")

    def _on_monitor(self):
        from pctool import SerialLink
        if self._link and self._link.alive:
            self._link.close()
            self._link = None
            self.mon_button.configure(text="Conectar monitor")
            self.mon_status.configure(text="desconectado")
            return
        if not self._mapped:
            self.mon_status.configure(text="mapeie e programe antes")
            return
        _name, entry = self._mapped
        link = SerialLink()
        err = link.connect()
        if err:
            self.mon_status.configure(text=err)
            self._log(f"monitor: {err}")
            return
        self._link = link
        self._build_monitor(entry)
        self.mon_button.configure(text="Desconectar")
        self.mon_status.configure(text=f"{link.port} — aguardando telemetria...")
        self._log(f"monitor conectado em {link.port}")
        self.after(200, self._poll_monitor)

    def _clear_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def _build_monitor(self, entry):
        self._clear_frame(self.mon_frame)
        self._out_labels = {}
        self._in_state = {}
        inputs = [p for p in entry["pins"]
                  if p["dir"] == "input" and p["name"] not in ("clk", "rst")]
        outputs = [p for p in entry["pins"] if p["dir"] == "output"]

        inframe = ttk.LabelFrame(self.mon_frame, text="Entradas (clique p/ alternar)")
        inframe.pack(side="left", fill="y", padx=4)
        if not inputs:
            ttk.Label(inframe, text="(só clk/rst)").pack(padx=4, pady=2)
        for p in inputs:
            self._in_state[p["pin"]] = 0
            btn = ttk.Button(
                inframe, text=f"{p['name']} = 0",
                command=lambda pin=p["pin"], nm=p["name"]: self._on_toggle(pin, nm))
            btn.pack(fill="x", padx=4, pady=1)
            self._in_state[f"btn{p['pin']}"] = btn

        outframe = ttk.LabelFrame(self.mon_frame, text="Saídas (ao vivo)")
        outframe.pack(side="left", fill="y", padx=4)
        if not outputs:
            ttk.Label(outframe, text="(nenhuma)").pack(padx=4, pady=2)
        for p in outputs:
            lbl = ttk.Label(outframe, text=f"{p['name']} = ?")
            lbl.pack(anchor="w", padx=4)
            self._out_labels[p["name"]] = (lbl, p["bit"])

    def _on_toggle(self, pin, name):
        if not self._link:
            return
        val = 1 - self._in_state.get(pin, 0)
        err = self._link.send(f"vset {pin} {val}")
        if err:
            self._log(f"toggle {name}: {err}")
            return
        self._in_state[pin] = val
        btn = self._in_state.get(f"btn{pin}")
        if btn:
            btn.configure(text=f"{name} = {val}")

    def _poll_monitor(self):
        if not self._link or not self._link.alive:
            return
        for kind, payload in self._link.poll():
            if kind == "telemetry":
                outs = []
                for sig, (lbl, bit) in self._out_labels.items():
                    v = (payload["out"] >> bit) & 1
                    lbl.configure(text=f"{sig} = {v}")
                    outs.append(f"{sig}={v}")
                self.mon_status.configure(
                    text=f"CLK={payload['clk']} FREQ={payload['freq']}Hz "
                         + " ".join(outs))
            else:
                self._log(f"< {payload}")
        self.after(200, self._poll_monitor)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("uFPGA-Emu Lab")
        self.geometry("800x600")

        self.notebook = ttk.Notebook(self)
        self.log_pane = LogPane(self)

        self.viewer = ViewerTab(self.notebook, self.log_pane.log)
        self.builder = BuilderTab(self.notebook, self.log_pane.log,
                                  self.log_pane.post)
        self.notebook.add(self.viewer, text="Exemplos")
        self.notebook.add(self.builder, text="Novo circuito")

        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)
        self.log_pane.pack(fill="x", padx=4, pady=(0, 4))
        self.log_pane.log("uFPGA-Emu Lab iniciado.")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
