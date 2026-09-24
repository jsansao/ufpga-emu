"""Alocador automático de pinos (ESP32) para a GUI didática (T5).

Regras (derivadas dos 26 pinmaps existentes + constraints do README):
- clk -> 4, rst -> 5 (só se o circuito tiver o sinal).
- Inputs: input-only primeiro (34-39), depois bidirecionais livres.
- Outputs: 2 primeiro, depois bidirecionais livres (nunca 4/5).
- Proibidos: 6-11 (SPI flash). 34-39 jamais como output.
- Determinístico: mesma lista de ports => mesmo mapeamento.
- virtual_init sai vazio; exceções (ex. run=1) o professor edita no JSON.

Entrada: ports = [(nome, direção, largura)] na ordem de declaração.
Saída: (entry, erro) no schema de firmware/pinmaps/*.json.
"""

INPUT_POOL = [34, 35, 36, 37, 38, 39,
              12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27]
OUTPUT_POOL = [2,
               12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33]
FORBIDDEN = set(range(6, 12))

assert not (set(INPUT_POOL) & FORBIDDEN)
assert not (set(OUTPUT_POOL) & FORBIDDEN)
assert not (set(OUTPUT_POOL) & {34, 35, 36, 37, 38, 39})
assert 4 not in INPUT_POOL and 5 not in INPUT_POOL
assert 4 not in OUTPUT_POOL and 5 not in OUTPUT_POOL


def allocate(ports, platform="esp32"):
    """Aloca pinos. Retorna (entry, erro)."""
    if platform != "esp32":
        return None, f"plataforma sem alocador no v1: {platform}"
    pins = []
    bit = {"input": 0, "output": 0}
    pools = {"input": list(INPUT_POOL), "output": list(OUTPUT_POOL)}
    for name, direction, width in ports:
        if direction not in pools:
            return None, f'direção "{direction}" do sinal "{name}" não suportada'
        if width < 1:
            return None, f'largura inválida de "{name}": {width}'
        for i in range(width):
            sig = name if width == 1 else f"{name}[{i}]"
            if sig == "clk":
                pin = 4
            elif sig == "rst":
                pin = 5
            else:
                if not pools[direction]:
                    need = sum(w for _, d, w in ports if d == direction)
                    return None, (
                        f"sem pino livre p/ {direction} (sinal \"{sig}\"): "
                        f"circuito precisa de {need}, há "
                        f"{len(INPUT_POOL) if direction == 'input' else len(OUTPUT_POOL)}"
                    )
                pin = pools[direction].pop(0)
            pins.append({"name": sig, "pin": pin,
                         "bit": bit[direction], "dir": direction})
            bit[direction] += 1
    return {"pins": pins, "virtual_init": {}}, None
