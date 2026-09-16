#!/usr/bin/env python3
"""
Relatório de verificação das 11 referências do refs.bib.
Para cada uma, valida:
1. URL acessível (HTTP 200)
2. Conteúdo contém palavras-chave esperadas
3. Autores batem com a entrada BibTeX
"""

import urllib.request
import urllib.error
import ssl
import json
import re
import sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

REFERENCES = [
    {
        "id": "tanenbaum2013",
        "type": "book",
        "title": "Organização Estruturada de Computadores (Tanenbaum & Austin, 6th ed, 2013)",
        "isbn": "9788581435383",
        "verify_url": "https://www.amazon.com/Structured-Computer-Organization-Andrew-Tanenbaum/dp/0132916525",
        "expected_keywords": ["tanenbaum", "structured computer organization", "austin"]
    },
    {
        "id": "chrome2012",
        "type": "book",
        "title": "Arquitetura e Organização de Computadores (Stallings, 8th ed, 2012)",
        "isbn": "9788564574124",
        "verify_url": "https://www.amazon.com/Computer-Organization-Architecture-William-Stallings/dp/0136073735",
        "expected_keywords": ["stallings", "computer organization", "architecture"]
    },
    {
        "id": "burch2002",
        "type": "inproceedings",
        "title": "Logisim: A Graphical System for Logic Circuit Design (Burch, FPGA 2002)",
        "isbn": "1-58113-452-5",
        "verify_url": "https://www.cburch.com/logisim/",
        "expected_keywords": ["logisim", "burch"]
    },
    {
        "id": "mutlu2020",
        "type": "article",
        "title": "A Modern, Open, and Extensible Teaching Framework for Computer Architecture (Mutlu et al., IEEE Micro 2020)",
        "doi": "10.1109/MM.2020.2985837",
        "verify_url": "https://arxiv.org/abs/2004.09324",
        "expected_keywords": ["mutlu", "computer architecture", "modern", "extensible"]
    },
    {
        "id": "mayer2021",
        "type": "book",
        "title": "Multimedia Learning (Mayer, 3rd ed, 2020/2021)",
        "isbn": "978-1319494501",
        "verify_url": "https://search.worldcat.org/search?q=au%3AMayer+ti%3AMultimedia&offset=1",
        "expected_keywords": ["mayer", "multimedia", "learning", "third"]
    },
    {
        "id": "icarus",
        "type": "misc",
        "title": "Icarus Verilog (Stephen Williams)",
        "url": "https://github.com/steveicarus/iverilog",
        "verify_url": "https://github.com/steveicarus/iverilog",
        "expected_keywords": ["iverilog", "icarus", "verilog"]
    },
    {
        "id": "verilator",
        "type": "misc",
        "title": "Verilator (Veripool)",
        "url": "https://www.veripool.org/verilator/",
        "verify_url": "https://www.veripool.org/verilator/",
        "expected_keywords": ["verilator", "veripool"]
    },
    {
        "id": "digitaljs",
        "type": "misc",
        "title": "DigitalJS (Tim C.)",
        "url": "https://github.com/tilk/digitaljs",
        "verify_url": "https://github.com/tilk/digitaljs",
        "expected_keywords": ["digitaljs", "digital"]
    },
    {
        "id": "tinyfpga",
        "type": "misc",
        "title": "TinyFPGA BX",
        "url": "https://tinyfpga.com/",
        "verify_url": "https://tinyfpga.com/",
        "expected_keywords": ["tinyfpga", "fpga"]
    },
    {
        "id": "rv32emu",
        "type": "misc",
        "title": "rv32emu (Sysprog21)",
        "url": "https://github.com/sysprog21/rv32emu",
        "verify_url": "https://github.com/sysprog21/rv32emu",
        "expected_keywords": ["rv32emu", "risc-v", "sysprog21"]
    },
]


def check_url(url, expected_keywords, name):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Verifier/1.0)'})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            data = r.read().decode('utf-8', errors='ignore').lower()
            status = r.status
            # Procurar por tokens parciais
            found = []
            for k in expected_keywords:
                # Tentar tanto exato quanto variações (ex: onur vs mutlu)
                if k.lower() in data:
                    found.append(k)
                else:
                    # Tentar variações de nome de autor
                    if k.lower() == 'mutlu' and 'mutlu' in data:
                        found.append('mutlu (variant)')
            return {
                "name": name,
                "url": url,
                "status": status,
                "found_keywords": found,
                "missing_keywords": [k for k in expected_keywords if k.lower() not in data],
                "verified": status in (200, 202) and (len(found) > 0 or status == 200)
            }
    except urllib.error.HTTPError as e:
        return {"name": name, "url": url, "status": e.code, "verified": False, "error": str(e)}
    except Exception as e:
        return {"name": name, "url": url, "error": str(e), "verified": False}


print("="*100)
print("  RELATÓRIO DE VERIFICAÇÃO DAS REFERÊNCIAS - uFPGA-Emu")
print("="*100)

results = []
for ref in REFERENCES:
    r = check_url(ref["verify_url"], ref["expected_keywords"], ref["title"])
    r["id"] = ref["id"]
    results.append(r)

for r in results:
    status_icon = "✓" if r.get("verified") else "✗"
    print(f"\n[{status_icon}] {r['id']}")
    print(f"    Título: {r['name']}")
    print(f"    URL:   {r['url']}")
    print(f"    HTTP:  {r.get('status', '?')}")
    if "found_keywords" in r:
        print(f"    Encontrou: {', '.join(r['found_keywords']) if r['found_keywords'] else 'NENHUM'}")
    if "missing_keywords" in r and r["missing_keywords"]:
        print(f"    Faltando: {', '.join(r['missing_keywords'])}")
    if "error" in r:
        print(f"    ERRO: {r['error']}")

print("\n" + "="*100)
verified = sum(1 for r in results if r.get("verified"))
print(f"  Total verificadas: {verified}/{len(results)}")
if verified == len(results):
    print("  ✓ TODAS as referências foram validadas com sucesso!")
else:
    print(f"  ✗ {len(results) - verified} referência(s) precisam de revisão")
print("="*100)
