# Intenção confirmada — editor de testbench-CSV na GUI

*Confirmada pelo usuário em 2026-09-24 via entrevista (skill interview-me).
Contexto: a simulação PC da aba Exemplos já aplicava os CSVs via
`STIMULUS_CSV`, mas de forma invisível — e 10 dos 19 CSVs usam o sinal
`inputs`, que o runtime ignora silenciosamente.*

- **Resultado:** na aba Exemplos, área de texto editável com o CSV de
  estímulo (o "testbench") que alimenta a simulação PC — aluno edita,
  roda, vê o efeito na saída.
- **Usuário:** alunos do laboratório de FPGA/Verilog.
- **Por que agora:** o CSV já dirige a simulação hoje, mas é invisível;
  escrever estímulos é o ato didático do testbench sem sintaxe Verilog TB.
- **Sucesso:** aluno muda um estímulo (ex.: tempo do `rst`) e vê a mudança
  na saída, sem terminal.
- **Restrição:** formato CSV atual intacto, **zero mudança no toolchain**;
  edição salva em temporário (CSVs do repo intocados); validação com erro
  claro (sinal inexistente, colunas erradas); expande `inputs` packed no
  lado da GUI (o runtime não mapeia).
- **Fora do escopo:** coluna `expected`/PASS-FAIL (v2 via stim_test);
  sintaxe de testbench Verilog (`initial`/`#`); editor de estímulo na aba
  Novo circuito (não tem harness PC por circuito).
