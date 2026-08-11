# SEH — Operações Determinísticas, Evidência e Medição

## Problem Statement

Antes dos agentes de IA, IDEs como o IntelliJ já automatizavam boa parte do trabalho de engenharia de forma **determinística e assertiva**: IntelliSense, live templates, "Generate →", refactorings que compunham classes inteiras para um mesmo propósito. Agentes de código refazem esse mesmo trabalho **probabilisticamente** — mais lento, mais caro e sujeito a erro.

O custo aparece em dois eixos, não um: **tokens** (o modelo lê, reescreve e reenvia contexto que poderia ter sido computado) e **latência** (cada round-trip de inferência custa segundos onde uma operação de AST custa milissegundos). Sem instrumentação, o desenvolvedor não sabe quanto disso é desperdício nem consegue provar que qualquer mitigação funcionou.

## Evidence

- **Operações de leitura consomem 76,1% dos tokens** de um agente de código, contra 12,1% de execução e 11,8% de edição ([Augment Code](https://www.augmentcode.com/guides/ai-coding-cost-analysis-agent-token-spend)). O gargalo de custo é ingestão de contexto, não geração. **Correção de leitura desta sessão**: essa fatia de 76,1% não é dominada só por saída de teste/build/lint (que só aparece no ciclo de erro→reteste) — a maior parte é **exploração de código** (Grep/Read/Glob repetidos para entender onde mexer), que acontece em **toda tarefa**, com ou sem falha de teste. Um compressor só de saída de runtime ataca a fatia menor; a hipótese e o MVP precisam cobrir as duas.
- **Tokens de input re-enviados a cada turno representam >99% do volume de trajetória** em traces publicados de agentes. Saída de runtime que entra no contexto é paga repetidamente, não uma vez.
- Relato do autor: mesma dor observada em **3 ferramentas de players distintos** — o LLM gastando tokens caros em processos simples. *Assumption — não quantificado; sem baseline de fatura ou trace. Validar na Fase 1.*
- **Gatilho ("por que agora"): estouro de cota de tokens semanal/mensal muito rápido.** O autor esgota a cota do agente antes do previsto, recorrentemente, em pelo menos 3 ferramentas distintas. Ainda sem número (quantos dias antes do previsto, com que frequência) — validar na Fase 1 junto com o baseline.
- **O autor não conhecia o Serena antes desta conversa.** O projeto nasceu para ser desenvolvido do zero como exercício de engenharia de software, não como resposta a uma lacuna já mapeada no mercado. Isso não invalida o problema (o gatilho de cota é real e independente), mas significa que a decisão de "grafo é commodity" é uma descoberta desta sessão, não uma premissa original do projeto — ver nota em Open Questions sobre tensão de escopo.
- **Substituir inferência por replay determinístico é medido**: latência média caiu de **7,82s para 0,90s (8,7x mais rápido, 13,2x menos variância)** ao trocar execução por LLM por replay gravado, e a economia de token chega a **99% em tarefas repetidas** (93% até em tarefas diárias) — [Loop Skill Engine](https://arxiv.org/pdf/2605.14237). Valida os dois eixos: carga cognitiva e latência.
- **Prior art de navegação e refactor está ocupado** (levantamento desta sessão): [Serena](https://github.com/oraios/serena) (LSP, 40+ linguagens), [act101](https://www.productcool.com/product/act101-ai-agent-refactor-port-code) (183 operações de refactor, 163 linguagens), [OHM-MCP](https://www.ohm-mcp.dev/) (Python, AST, rename com detecção de conflito, execução de teste com rollback), [Code Scalpel](https://mcpservers.org/servers/3d-tech-solutions/code-scalpel). A própria JetBrains tem [ticket aberto](https://youtrack.jetbrains.com/projects/LLM/issues/LLM-25880/Add-AST-based-refactoring-tools-to-the-AI-Assistant-via-MCP) para expor refactorings AST ao AI Assistant via MCP.
- **A lacuna que sobra é dupla**: (a) nenhuma dessas ferramentas **prova a economia** — a documentação do OHM-MCP não faz nenhuma afirmação sobre token ou determinismo; (b) todas oferecem operações **universais** (rename, extract), nenhuma permite **gravar uma operação composta específica do projeto**. Scaffolders (cookiecutter, plop, hygen) criam arquivos novos por template mas **não inserem estruturalmente em arquivos existentes** — exatamente a parte difícil que o "Generate →" do IntelliJ resolvia.

## Proposed Solution

O SEH é o **live template do IntelliJ, para agentes, medido**: grava uma operação de engenharia deste projeto **uma vez** (com LLM, caro) e a repete **deterministicamente** (sem LLM, ~0 token, milissegundos). Envolve o agente de código já em uso (Claude Code, Codex, Kimi) sem substituí-lo.

A solução tem **três alavancas**, em ordem de valor:

1. **Operações gravadas (`seh op`)** — *alavanca principal.* Uma operação é uma transformação composta e parametrizada do repositório: cria arquivos novos **e insere estruturalmente em arquivos existentes** via AST. Exemplo real, no próprio SEH: adicionar um subcomando à CLI exige um bloco de subparser em `cli.py`, um handler e um teste. Gravado uma vez, vira `seh op run add-cli-command --name=report` — determinístico, repetível, versionado no repo e compartilhável pelo time. É o que scaffolders (cookiecutter/plop) não fazem (não editam arquivo existente) e o que refactorers universais (act101/OHM-MCP) não fazem (não compõem operações do seu projeto).
2. **Compressão de exploração** — antes de editar, o agente precisa entender o código. Sem SEH, isso é feito com várias chamadas de Read/Grep/Glob, lendo arquivos inteiros para achar uma função ou seus usos. O SEH expõe `seh inspect <symbol>` e `seh neighbors <symbol>` (já existentes no CLI desde o M0, hoje presos ao adaptador Java) sobre o índice Python (`ast`): localização exata e relações estruturais em poucas linhas. Age em **toda tarefa**, não só quando um teste falha. Também é o substrato técnico da alavanca 1 — sem AST não há inserção estrutural.
3. **Compressão de evidência de runtime** — saída de teste/build/lint comprimida em evidência estruturada, ativa no ciclo de erro→reteste. É o que mantém o agente ciente do que aconteceu sem despejar log bruto no contexto.

O ciclo de vida de uma operação — **gravar → armazenar → repetir → verificar → medir** — é o que amarra as três: cada replay executa a alavanca 1, dispensa a 2 (a estrutura já está codificada na operação) e produz a 3 como resultado verificado.

O diferencial de valor continua sendo **runtime + evidência + medição** — essa camada nunca dependeu de indexação simbólica de código; comprimir saída de `pytest` é parsing de formato de ferramenta, ortogonal a entendimento de código. Mas o **modo de entrega** muda: o autor rejeitou dependência de instalar um servidor externo (Serena) como pré-requisito de uso. O SEH é **self-contained** — instala em qualquer repositório com um único comando, sem processo externo — e se expõe via **MCP**, o protocolo que já faz funcionar em qualquer agente (Claude Code, Codex, Kimi, o que vier). Onde o produto precisar de capacidade simbólica mínima (por exemplo, mapear uma falha de teste até a função que a contém), ela é construída em **Python puro com o módulo `ast` da stdlib** — zero dependência externa, suficiente para o que o runtime/evidência exige, sem competir em profundidade com Serena ou Aider. O Serena deixa de ser dependência de produto e vira apenas **referência de benchmark opcional** — usado uma vez, em pesquisa, não instalado pelo usuário final.

## Key Hypothesis

Acreditamos que **gravar operações de engenharia do projeto e repeti-las deterministicamente** vai **reduzir tokens e latência de um loop engineering, preservando a qualidade dos artefatos**, para **desenvolvedores que operam agentes de código e pagam a própria conta**.

Saberemos que estamos certos quando, no mesmo projeto POC, mesmo agente e mesma lista de tarefas, o braço com SEH consumir **≥30% menos tokens totais** e **≥50% menos tempo de parede** que o braço sem SEH (baseline), com **taxa de conclusão de tarefas igual ou superior**.

Ambos os limiares são apostas iniciais, não números derivados. Existem para ser falsificados — se o delta de token for 5%, a tese econômica morre barato. O alvo de latência é deliberadamente mais conservador que o 8,7x medido na literatura de replay determinístico, porque o loop do SEH mantém o LLM no circuito para as partes que exigem raciocínio; só as operações gravadas saem da inferência.

**Hipótese secundária, testável em separado:** o ganho cresce com a repetição. Uma operação gravada e executada uma única vez pode até dar prejuízo (custo de gravação > economia); o payback aparece a partir de N repetições. Determinar N é resultado da Fase 5, não premissa.

## What We're NOT Building

- **Modelo LLM local** — adiado explicitamente pelo autor. Evolução futura, fora do v1.
- **Roteamento entre modelos** (barato vs. frontier) — decorre do item acima; sem modelo local, não há para onde rotear. Território já ocupado por RouteLLM e gateways.
- **Catálogo de refactorings universais** (rename global, extract method, inline, move-symbol como produto) — território de [act101](https://www.productcool.com/product/act101-ai-agent-refactor-port-code) (183 operações, 163 linguagens) e [OHM-MCP](https://www.ohm-mcp.dev/) (Python). O SEH grava operações **compostas e específicas do projeto**; não compete em quantidade de refactors genéricos. Se um dia precisar de um rename global robusto, o caminho é consumir uma dessas ferramentas, não reimplementá-las.
- **Grafo/índice de repositório em profundidade de IDE** — não se compete com Serena/Aider em cobertura ou precisão de LSP. A capacidade simbólica própria (Python `ast`) cobre consulta pontual (`seh inspect`/`seh neighbors`) e a inserção estrutural das operações gravadas, não é um produto de navegação de código.
- **Detecção automática de padrões a partir do histórico Git** (derivar operações sozinho a partir de commits antigos) — ideia atraente e provavelmente o passo seguinte, mas fuzzy demais para o MVP. No v1 a gravação é assistida: o LLM/dev descreve a operação uma vez, o SEH valida e materializa.
- **Engineering IR completo / Context Package com budget** (M1 pleno: schema de tarefa, seleção priorizada, orçamento de tokens) — fica para depois do MVP. A Fase 1 usa só a fatia mínima do M1 (adaptador + consulta de símbolo), não o compilador de contexto inteiro.
- **Dependência de servidor externo instalado à parte** — Serena não é pré-requisito do SEH. Se usado, é só para o benchmark de pesquisa opcional.
- **Um agente de código próprio** — o princípio 6 do README é explícito: *wrap coding agents rather than become one*.
- **Suporte multi-linguagem amplo no v1** — o runtime e o indexador simbólico começam em Python só, porque a hipótese e o próprio SEH são Python.

## Success Metrics

| Métrica | Alvo | Como medir |
|---|---|---|
| **Redução de tokens** (primária) | ≥30% vs. baseline (braço A) | Soma de input+output+cache do agente, mesma lista de tarefas, sessões distintas |
| **Redução de latência** (primária) | ≥50% de tempo de parede vs. baseline | Cronômetro por tarefa, do prompt até o teste verde. Registrar mediana e dispersão, não só média |
| **Preservação de qualidade** (guarda) | Taxa de conclusão ≥ baseline; testes do POC passando | Suíte de aceitação do projeto POC, avaliada por código, não por julgamento |
| **Payback de operação gravada** | ≤5 execuções | Custo de gravação (tokens+tempo) ÷ economia por replay. Determina se `seh op` se paga |
| **Compressão de evidência** | ≥10x em saída de teste com falha | Bytes de saída bruta ÷ bytes de evidência estruturada |
| **Compressão de exploração** (diagnóstica) | ≥5x em bytes por localização de símbolo | Bytes que `seh inspect`/`seh neighbors` devolvem ÷ bytes que grep+leitura manual do(s) arquivo(s) equivalente(s) exigiriam |

Latência e tokens **não são redundantes**: uma operação gravada zera a inferência (ganho nos dois), mas a compressão de evidência reduz token sem reduzir latência proporcionalmente. Medir só um dos eixos esconde metade do efeito.

Nota metodológica crítica: o **onboarding do Serena é executado pelo LLM e consome tokens**. Uma sessão curta pode ter o custo de setup mascarando ou invertendo a economia. Custo de setup e custo marginal por tarefa devem ser reportados **separadamente**.

## Open Questions

- [x] ~~Qual foi o gatilho real ("por que agora")?~~ Respondido: estouro recorrente de cota de tokens semanal/mensal. Falta apenas quantificar (dias de antecipação, frequência) — Fase 1.
- [x] ~~O autor já rodou o Serena?~~ Respondido: não, o projeto nasceu como exercício de engenharia de software, sem conhecimento prévio do Serena.
- [x] ~~Tensão de escopo: manter indexador próprio por valor de aprendizado vs. consumir Serena?~~ Resolvida: o autor não quer dependência de instalar Serena; o SEH será self-contained. A capacidade simbólica própria deixa de ser opcional/fallback e passa a ser parte do produto — só que mínima (Python `ast`), não uma tentativa de igualar Serena/Aider em profundidade.
- [x] ~~O SEH entrega valor como servidor MCP ou wrapper de CLI?~~ Resolvida: MCP, para funcionar em qualquer agent code sem acoplamento — é a exigência explícita do autor.
- [x] ~~O que fazer com o indexador Java do PR #1?~~ Resolvida: paradigma muda de Java para Python. O indexador Java do PR #1 fica congelado como referência de arquitetura (proveniência, fingerprint, schema versionado); a implementação segue em Python com `ast`, não Tree-sitter.
- [ ] Natureza do projeto: OSS público, portfólio, interno ou comercial? *Assumption atual: portfólio/exercício técnico com distribuição OSS*; `license = "Apache-2.0"` no PR #1 indica intenção de publicar, mas a motivação declarada é aprendizado, não adoção de terceiros.
- [ ] Qual o tamanho e a forma do projeto POC? Precisa ser grande o bastante para o custo de leitura aparecer, pequeno o bastante para iterar.
- [ ] Como isolar variância do LLM entre sessões? Mesma tarefa gera consumo diferente por não-determinismo; quantas repetições para significância?
- [ ] O plano técnico existente (`plans/engineering_ir_context_package.md`) foi escrito para Java/Tree-sitter e precisa ser reescrito para Python/`ast` antes de virar trabalho executável.

---

## Users & Context

**Primary User**

- **Quem**: desenvolvedor individual que opera loop engineering com um agente de código e **paga a própria conta de tokens**. Tem proficiência técnica alta, tolera setup por CLI, e sente o custo diretamente na fatura.
- **Comportamento atual**: roda o agente contra o repositório; o agente executa testes/build, ingere saída bruta, re-tenta, e o contexto cresce a cada turno.
- **Gatilho**: o momento em que a tarefa entra em ciclo de erro→correção→reteste. É aí que a saída de runtime domina o contexto.
- **Estado de sucesso**: mesma tarefa concluída, mesma qualidade de artefato, consumo mensuravelmente menor — e o desenvolvedor consegue **ver o número**.

**Job to Be Done**

Quando **preciso fazer no meu projeto algo que já fiz antes do mesmo jeito** (adicionar um endpoint, um comando, um caso de uso), eu quero **que isso seja executado por uma operação determinística já gravada, não redescoberto e reescrito pelo modelo**, para que **o LLM gaste esforço só no que é genuinamente novo, e eu não pague token nem espere inferência por trabalho mecânico**.

**Non-Users**

- Times de plataforma buscando governança e relatório corporativo de custo — governança não é o problema do v1.
- Quem quer navegação semântica de código em profundidade de IDE — isso é Serena/Aider; o SEH não compete nesse eixo.
- Quem não paga pelos próprios tokens: sem a dor na fatura, não há gatilho.

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Prioridade | Capacidade | Racional |
|---|---|---|
| Must | **`seh op record` / `seh op run`** — operação gravada e repetível | **Alavanca 1, o produto.** É o live template para agentes: onde tokens *e* latência caem juntos |
| Must | **Inserção estrutural via AST em arquivo existente** | A parte difícil que scaffolders não fazem. Sem isso, `seh op` é só cookiecutter |
| Must | **Medidor de tokens e latência / harness de benchmark** | Sem medir, nada é falsificável. É o instrumento que valida ou mata o projeto |
| Must | **Adaptador Python (`ast`) + `seh inspect`/`seh neighbors`** | Alavanca 2 e substrato técnico da alavanca 1 — sem AST não há inserção estrutural |
| Must | **Command runner + compressão de saída → evidência** | Alavanca 3. Verifica o resultado do replay e mantém o agente ciente sem log bruto |
| Must | **Projeto POC + protocolo A/B** | O experimento; sem ele o número não significa nada |
| Must | **Self-contained, zero dependência externa** | Exigência explícita do autor — nada de instalar servidor externo como pré-requisito |
| Should | **Exposição via MCP** | Funciona em qualquer agent code (Claude Code, Codex, Kimi) sem acoplamento |
| Should | Operações versionadas no repo (`.seh/operations/`) | Compartilháveis pelo time, revisáveis em PR — como live templates de projeto eram |
| Should | Aproveitar proveniência/frescor do PR #1 | Arquitetura reaproveitável; implementação muda de Tree-sitter/Java para `ast`/Python |
| Could | Derivar operação a partir de commit anterior | Passo natural seguinte; fuzzy demais para o MVP |
| Could | Engineering IR completo / Context Package com budget (M1 pleno) | Fica para depois do veredito |
| Could | Benchmark contra Serena | Referência de mercado opcional, não bloqueia a validação |
| Won't | Catálogo de refactorings universais (rename/extract/inline globais) | Território de act101 e OHM-MCP; consumir se precisar, não reimplementar |
| Won't | Modelo local, roteamento entre modelos | Adiado pelo autor — evolução futura |
| Won't | Paridade de profundidade com Serena/Aider (LSP, 40+ linguagens) | Fora de escopo por design |

### MVP Scope

O mínimo para validar a hipótese, em ordem de dependência:

1. Um **projeto POC** em Python com estrutura real (módulos, classes, testes) e **pelo menos uma operação genuinamente repetitiva** — sem repetição, `seh op` não tem o que provar.
2. Um **medidor** de tokens *e* tempo de parede por tarefa.
3. Um **adaptador Python (`ast`)** + `seh inspect`/`seh neighbors` — exploração e substrato para inserção estrutural.
4. **`seh op record` / `seh op run`** com uma operação real gravada, incluindo inserção AST em arquivo existente.
5. Um **runner + compressor** `pytest` → evidência, para verificar o replay.
6. O **experimento baseline vs. SEH**, com a operação repetida N vezes para medir a curva de payback.

O ponto de falsificação mudou de lugar: não é mais "compressão gera delta?", e sim **"o custo de gravar uma operação se paga em quantas repetições?"**. Se N for alto demais para o uso real, o projeto não se paga — e isso é descobrível cedo e barato.

### User Flow

```
─── CAMINHO A: tarefa repetitiva (o caso que o SEH otimiza) ───

dev: "adiciona o comando report na CLI"
      │
      ▼
agente reconhece operação gravada ──► seh op run add-cli-command --name=report
      │                                        │
      │                              ~0 token, milissegundos, sem inferência
      │                                        │
      │                                 cria commands/report.py
      │                                 AST-insert subparser em cli.py
      │                                 cria tests/test_report.py
      │                                        ▼
      │                                 seh test → evidência (verde)
      │                                        │
      └────────────────────────────────────────┘
                    agente reporta: "feito, 3 arquivos, testes passando"


─── CAMINHO B: tarefa nova (o LLM continua no circuito) ───

dev: "implementa cache distribuído"
      │
      ▼
seh inspect / neighbors ──► contexto mínimo ──► LLM raciocina e escreve
      │                                                 │
      │                                          seh test → evidência
      │                                                 │
      │                                    se virou padrão repetível?
      │                                                 ▼
      └──────────────────────────────► seh op record  (grava para a próxima vez)

                    medidor registra tokens + latência em ambos
```

O Caminho B alimenta o Caminho A: cada padrão que se repete vira operação gravada, e o custo migra de inferência para execução.

---

## Technical Approach

**Feasibility**: **ALTA** para o MVP. Parser de saída de `pytest` é trabalho determinístico bem delimitado; medição de token é leitura de metadados já expostos pelos agentes; o repositório já tem substrato de CLI, config, storage e disciplina de proveniência vindos do PR #1. `seh inspect`/`seh neighbors` **já existem como comandos** desde o M0 — o trabalho da alavanca de exploração é escrever `python_adapter.py` e plugá-lo no indexador existente, não construir CLI nova.

**Architecture Notes**

- **Self-contained por design.** Nenhuma dependência de instalar um servidor MCP externo (Serena) como pré-requisito. O SEH é a única coisa que o usuário instala.
- **Indexação simbólica própria, em Python, via `ast` da stdlib.** Substitui o paradigma Tree-sitter/Java do PR #1. Escopo deliberadamente mínimo — o bastante para a evidência referenciar `arquivo:linha:função`, não uma tentativa de igualar LSP.
- **Reaproveitar a disciplina de evidência do PR #1.** Fingerprint, schema versionado e recusa de dado obsoleto ("evidência confiável ou erro explícito") são exatamente a semântica que o `seh-evidence` precisa — a arquitetura sobrevive, a implementação (Tree-sitter Java) é substituída por `ast` Python.
- **Execução fora do contexto do modelo.** O runner roda no processo do SEH; o modelo só vê o resultado normalizado.
- **Exposto via MCP.** É o mecanismo concreto de "funciona em qualquer agent code" sem reescrever integração por cliente.
- **Um ecossistema primeiro (Python).** Multi-linguagem é escala, não validação.

**Technical Risks**

| Risco | Prob. | Mitigação |
|---|---|---|
| **Custo de gravar uma operação não se paga** — se N repetições para payback for alto demais, `seh op` é teatro | **Alta — é o novo ponto de falsificação** | Métrica de payback (≤5 execuções) medida explicitamente na Fase 6; POC obrigado a ter repetição real |
| **Inserção estrutural em arquivo existente é a parte difícil** — é onde scaffolders desistiram | **Alta** | Escopo travado: um tipo de âncora AST bem definido no MVP (ex.: inserir em bloco de subparser), não um motor genérico |
| **MVP com uma alavanca só (evidência) não move o número o bastante** — a maior fatia de leitura é exploração, não retry | **Alta (materializada nesta sessão)** | Mitigada: adaptador Python + `seh inspect`/`seh neighbors` entram como Must, e `seh op` passa a ser a alavanca principal |
| Operação gravada fica obsoleta quando o padrão do projeto muda, e passa a gerar código errado | Média | Fingerprint + verificação por teste após todo replay; operação que quebra teste falha explicitamente em vez de gerar lixo |
| Variância entre sessões do LLM mascara o efeito | Alta | Repetições; reportar dispersão, não só média; tarefas determinísticas |
| Indexador Python (`ast`) próprio vira scope creep e passa a competir com Serena/Aider em profundidade | Média | MoSCoW trava explicitamente: só consulta pontual (`inspect`/`neighbors`), sem Engineering IR/budget no MVP |
| POC não tem estrutura de código suficiente para a alavanca de exploração mostrar efeito | Média | POC precisa de módulos/classes reais, não só funções soltas — critério de aceite da Fase 1 |
| Compressão descarta informação que o agente precisava → qualidade cai | Média | Métrica-guarda de conclusão; evidência deve ser expansível sob demanda |
| Agentes não expõem contagem de token de forma uniforme | Média | Começar por um agente só; abstrair depois |
| Benchmark contra Serena (braço C) vira bloqueio informal mesmo sendo opcional | Baixa | Tratar como pesquisa paralela; não é dependência de release |

---

## Implementation Phases

| # | Fase | Descrição | Status | Parallel | Depends | PRP Plan |
|---|---|---|---|---|---|---|
| 1 | Baseline e instrumentação | POC com repetição real + medidor de **tokens e latência** + braço A | pending | - | - | - |
| 2 | Adaptador Python + consulta de símbolo | `python_adapter.py` + `seh inspect`/`seh neighbors` — alavanca 2 e substrato da alavanca 1 | pending | with 3 | 1 | - |
| 3 | Runner + compressor de evidência | `pytest` executado fora do contexto → evidência estruturada — alavanca 3 | pending | with 2 | 1 | - |
| 4 | **`seh op` — gravar e repetir** | Formato de operação, `record`, `run`, e inserção estrutural via AST em arquivo existente — **alavanca 1, o produto** | pending | - | 2, 3 | - |
| 5 | Dogfooding no próprio SEH | Gravar `add-cli-command` e usá-la para criar comandos reais do SEH | pending | - | 4 | - |
| 6 | Braço SEH, curva de payback e veredito | Medir tokens, latência e em quantas repetições a operação se paga; decidir seguir ou parar | pending | - | 4, 5 | - |
| 7 | Exposição via MCP | Empacotar como servidor MCP self-contained | pending | - | 6 | - |
| 8 | Benchmark opcional (Serena / OHM-MCP) | Referência de mercado; não bloqueia release | pending | with 1–7 | - | - |

### Phase Details

**Fase 1: Baseline e instrumentação**
- **Objetivo**: ter um número inicial confiável nos dois eixos.
- **Escopo**: POC em Python com estrutura real **e pelo menos uma operação genuinamente repetitiva**; lista fixa de tarefas; captura de tokens (input/output/cache) **e tempo de parede** por tarefa; protocolo de repetição documentado.
- **Sinal de sucesso**: mesma tarefa rodada N vezes produz consumo e latência dentro de faixas de dispersão conhecidas.

**Fase 2: Adaptador Python + consulta de símbolo**
- **Objetivo**: alavanca de exploração e, sobretudo, o substrato AST de que a Fase 4 depende.
- **Escopo**: `python_adapter.py` via `ast` da stdlib (fatia mínima de `plans/engineering_ir_context_package.md`: sem Engineering IR, sem budget); plugar no indexador existente; `seh inspect`/`seh neighbors` sobre o POC.
- **Sinal de sucesso**: localizar símbolo e relações consome visivelmente menos bytes que grep + leitura de arquivo.

**Fase 3: Runner + compressor de evidência**
- **Objetivo**: executar sem gastar contexto e destilar o resultado.
- **Escopo**: descoberta/execução de teste, captura de stdout/stderr/exit code, timeout; parser `pytest` → falhas com `arquivo:linha`, mensagem e diff de assertion; formato versionado; evidência expansível sob demanda.
- **Sinal de sucesso**: ≥10x de compressão numa suíte com falhas, sem perda de informação acionável.

**Fase 4: `seh op` — gravar e repetir** *(o produto)*
- **Objetivo**: materializar o live template para agentes.
- **Escopo**: formato `seh.operation/v0.1` (parâmetros, efeitos, verificação, proveniência); `seh op record` (assistido, uma vez) e `seh op run` (determinístico, N vezes); **inserção estrutural via AST em arquivo existente**, com um tipo de âncora bem definido — não um motor genérico; operações versionadas em `.seh/operations/`; idempotência e falha explícita quando a âncora não existe mais.
- **Sinal de sucesso**: `seh op run` produz o mesmo resultado byte a byte em execuções repetidas, sem nenhuma chamada de LLM.

**Fase 5: Dogfooding no próprio SEH**
- **Objetivo**: provar a operação em código real antes de medir.
- **Escopo**: gravar `add-cli-command` a partir do padrão que já existe em `src/seh/cli.py` e usá-la para criar os comandos reais que o próprio SEH ainda precisa (`seh op`, `seh report`).
- **Sinal de sucesso**: um comando do SEH nasce inteiramente de `seh op run`, com teste verde, sem edição manual.

**Fase 6: Braço SEH, curva de payback e veredito**
- **Objetivo**: falsificar ou confirmar a hipótese nos dois eixos.
- **Escopo**: rodar A (baseline) vs. SEH; reportar tokens, latência, dispersão, conclusão de tarefas, compressão e — o número decisivo — **em quantas repetições uma operação gravada se paga**.
- **Sinal de sucesso**: números defensáveis em qualquer direção. **Payback alto demais é resultado válido e encerra o projeto barato.**

**Fase 7: Exposição via MCP**
- **Objetivo**: tornar o SEH utilizável em qualquer agent code.
- **Escopo**: servidor MCP expondo `op run`, `inspect`, `neighbors`, `test`; instalação em um comando, sem processo externo.
- **Sinal de sucesso**: funciona nos três agentes do autor sem dependência além do próprio SEH.

**Fase 8: Benchmark opcional (Serena / OHM-MCP)**
- **Objetivo**: posicionamento — quanto da economia já é capturada por ferramentas existentes.
- **Escopo**: instalar, rodar a mesma lista, medir; custo de onboarding registrado à parte.
- **Sinal de sucesso**: número documentado. Não bloqueia nenhuma fase nem o release.

### Parallelism Notes

2 e 3 são paralelizáveis — adaptador e runner/compressor tocam superfícies distintas. A **Fase 4 depende das duas**: precisa do AST da 2 para inserir estruturalmente e da verificação da 3 para validar cada replay. As Fases 5 e 6 são estritamente sequenciais após a 4 — dogfooding antes de medir, medir antes de decidir. A Fase 8 é pesquisa independente e roda a qualquer momento. **A Fase 6 é o portão real**: nada de MCP ou empacotamento antes de saber se a operação se paga.

---

## Decisions Log

| Decisão | Escolha | Alternativas | Racional |
|---|---|---|---|
| **Centro do produto** | **Record-once / replay determinístico (`seh op`)** | (a) só medição/prova como produto; (b) catálogo de refactors próprio; (c) manter só as duas alavancas de leitura | Origem da ideia do autor: IDEs já automatizavam isso deterministicamente antes dos agentes. Replay determinístico tem ganho medido de 8,7x em latência e até 99% em token. Refactor genérico já é ocupado (act101, OHM-MCP); operação **composta e específica do projeto** não é |
| **Latência como métrica primária** | Sim, ao lado de tokens | Só token; latência como secundária | Levantada pelo autor e ausente do documento até aqui. Substituir inferência (3–8s) por execução (ms) pode ser o ganho mais perceptível no uso diário |
| Camada de diferenciação | Operações determinísticas + evidência + medição | Grafo próprio de repositório em profundidade de IDE | Grafo profundo é commodity (Serena MIT, 40+ linguagens; Aider PageRank) |
| Dependência de produto | Self-contained, zero servidor externo | Consumir Serena/LSP como adaptador obrigatório | Exigência explícita do autor: não quer instalar Serena para o SEH funcionar |
| Indexação simbólica | Python `ast` da stdlib, escopo mínimo | Tree-sitter multi-linguagem; nenhum indexador próprio | Zero dependência externa; suficiente para a evidência referenciar símbolos; não compete em profundidade |
| Modo de entrega | Servidor MCP | Wrapper de CLI que orquestra o agente | "Funciona em qualquer agent code" exige o protocolo que os agentes já falam |
| Modelo local e roteamento | Fora do v1 | Incluir no v1 | Decisão do autor: simplificar. Sem modelo local não há para onde rotear |
| Usuário primário | Dev solo que paga os próprios tokens | Time de plataforma; tech lead | Escolha do autor; alinha o produto a setup rápido e feedback direto |
| Ordem de validação | Medir antes de construir | Construir e medir depois | Baseline (Fase 1) e veredito (Fase 4) antes de investir em release |
| Papel do Serena | Benchmark de pesquisa opcional | Dependência de produto (versão anterior desta decisão) | Revertido nesta sessão — autor não quer instalação externa obrigatória |
| Linguagem do runtime v1 | Python | Java (seguindo o indexador atual) | O POC e o SEH são Python; autor concordou em migrar o paradigma |
| PR #1 (indexador AST Java) | Congelar como referência de arquitetura | Reverter; estender em Java | Disciplina de proveniência/fingerprint é reaproveitável; implementação Tree-sitter/Java é substituída por `ast`/Python |
| `plans/engineering_ir_context_package.md` | Precisa ser reescrito para Python/`ast` | Executar como está (Java) | Plano foi escrito antes da decisão de migrar para Python; reescrita é pré-requisito para virar trabalho executável |
| Escopo da alavanca de exploração no MVP | Fatia mínima do M1 (adaptador Python + `seh inspect`/`seh neighbors`) entra na Fase 1, não depois do veredito | (a) só evidência de runtime no MVP, exploração fica para M1 pleno depois; (b) M1 pleno (Engineering IR + budget) já no MVP | Rejeitada a opção (a) nesta sessão: leitura de exploração acontece em toda tarefa, não só em retry — cobrir só evidência deixa a maior fatia do custo intocada e o número da hipótese fica artificialmente pequeno. Rejeitada (b): `inspect`/`neighbors` já existem no CLI (M0), custam muito menos que o Engineering IR completo, e bastam para a Fase 1 |

---

## Research Summary

**Market Context** *(revisado nesta sessão — o levantamento anterior parava no Serena)*

O problema está provado por terceiros: leitura domina o custo (76,1%), input re-enviado responde por >99% do volume de trajetória, e substituir inferência por replay determinístico rende **8,7x em latência e até 99% em token** ([Loop Skill Engine](https://arxiv.org/pdf/2605.14237)).

O campo é mais povoado do que o levantamento inicial sugeria:

| Camada | Ocupantes | Situação |
|---|---|---|
| Navegação simbólica | Serena (LSP, 40+ ling.), Aider repo-map | Ocupada |
| Refactor AST universal | act101 (183 ops, 163 ling.), OHM-MCP (Python, + teste com rollback), Code Scalpel | Ocupada — JetBrains tem ticket para expor refactorings AST ao AI Assistant via MCP |
| Scaffolding por template | cookiecutter, plop, hygen, yeoman | Ocupada, mas **só cria arquivos novos** — não insere em arquivo existente |
| Roteamento de modelo | RouteLLM, gateways | Ocupada (e fora do escopo v1) |
| **Operação composta específica do projeto** | — | **Livre** |
| **Prova de economia no repo do usuário** | — | **Livre** — OHM-MCP não faz nenhuma afirmação sobre token ou determinismo |

A lacuna que sustenta o SEH é a interseção das duas últimas linhas: **gravar uma operação de engenharia deste projeto, repeti-la deterministicamente, e provar a economia com número**. Inserção estrutural em arquivo existente é a fronteira técnica — é onde os scaffolders desistiram e o que o "Generate →" do IntelliJ resolvia.

**Technical Context**

O repositório está em `0.1.0a2` com o PR #1 aberto (1510+/231−, 21 arquivos). O PR substituiu regex por Tree-sitter, introduziu identidades qualificadas e resolução determinística com ordem correta do Java, schema SQLite v2, proveniência, fingerprint e detecção de índice obsoleto. Corrigiu o defeito de colisão de nomes simples que gerava arestas erradas — `TypeCatalog.resolve` retorna `ambiguous` em vez de chutar. Validação declarada no PR (27 testes, 92,75% de cobertura de branch) não foi verificada de forma independente.

O ativo reaproveitável do PR para o novo posicionamento **não é o parser Java** — é a disciplina de proveniência e frescor: evidência confiável ou erro explícito, nunca dado obsoleto silencioso. Essa é a semântica que o `seh-evidence` precisa.

---

*Generated: 2026-08-10*
*Status: DRAFT — needs validation*
