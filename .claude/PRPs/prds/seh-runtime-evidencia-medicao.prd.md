# SEH — Memória Procedural Versionada do Projeto

> Cenário de produto ponta a ponta: [`docs/PRODUCT_SCENARIO.md`](../../../docs/PRODUCT_SCENARIO.md).
> Este PRD trata da hipótese, das métricas e da sequência de validação.

## Problem Statement

Antes dos agentes de IA, IDEs como o IntelliJ já automatizavam boa parte do trabalho de engenharia de forma **determinística e assertiva**: IntelliSense, live templates, "Generate →", refactorings que compunham classes inteiras para um mesmo propósito. Agentes de código refazem esse mesmo trabalho **probabilisticamente** — mais lento, mais caro e sujeito a erro.

O custo aparece em dois eixos, não um: **tokens** (o modelo lê, reescreve e reenvia contexto que poderia ter sido computado) e **latência** (cada round-trip de inferência custa segundos onde uma operação de AST custa milissegundos). Sem instrumentação, o desenvolvedor não sabe quanto disso é desperdício nem consegue provar que qualquer mitigação funcionou.

## Evidence

- **Operações de leitura consomem 76,1% dos tokens** de um agente de código, contra 12,1% de execução e 11,8% de edição ([Augment Code](https://www.augmentcode.com/guides/ai-coding-cost-analysis-agent-token-spend)). O gargalo de custo é ingestão de contexto, não geração. **Correção de leitura desta sessão**: essa fatia de 76,1% não é dominada só por saída de teste/build/lint (que só aparece no ciclo de erro→reteste) — a maior parte é **exploração de código** (Grep/Read/Glob repetidos para entender onde mexer), que acontece em **toda tarefa**, com ou sem falha de teste. Um compressor só de saída de runtime ataca a fatia menor; a hipótese e o MVP precisam cobrir as duas.
- **Tokens de input re-enviados a cada turno representam >99% do volume de trajetória** em traces publicados de agentes. Saída de runtime que entra no contexto é paga repetidamente, não uma vez.
- Relato do autor: mesma dor observada em **3 ferramentas de players distintos** — o LLM gastando tokens caros em processos simples. *Assumption — não quantificado; sem baseline de fatura ou trace. Validar na Fase 5.*
- **Gatilho ("por que agora"): estouro de cota de tokens semanal/mensal muito rápido.** O autor esgota a cota do agente antes do previsto, recorrentemente, em pelo menos 3 ferramentas distintas. Ainda sem número (quantos dias antes do previsto, com que frequência) — validar na Fase 5 junto com o baseline.
- **O autor não conhecia o Serena antes desta conversa.** O projeto nasceu para ser desenvolvido do zero como exercício de engenharia de software, não como resposta a uma lacuna já mapeada no mercado. Isso não invalida o problema (o gatilho de cota é real e independente), mas significa que a decisão de "grafo é commodity" é uma descoberta desta sessão, não uma premissa original do projeto — ver nota em Open Questions sobre tensão de escopo.
- **Substituir inferência por replay determinístico é medido**: latência média caiu de **7,82s para 0,90s (8,7x mais rápido, 13,2x menos variância)** ao trocar execução por LLM por replay gravado, e a economia de token chega a **99% em tarefas repetidas** (93% até em tarefas diárias) — [Loop Skill Engine](https://arxiv.org/pdf/2605.14237). Valida os dois eixos: carga cognitiva e latência.
- **Prior art de navegação e refactor está ocupado** (levantamento desta sessão): [Serena](https://github.com/oraios/serena) (LSP, 40+ linguagens), [act101](https://www.productcool.com/product/act101-ai-agent-refactor-port-code) (183 operações de refactor, 163 linguagens), [OHM-MCP](https://www.ohm-mcp.dev/) (Python, AST, rename com detecção de conflito, execução de teste com rollback), [Code Scalpel](https://mcpservers.org/servers/3d-tech-solutions/code-scalpel). A própria JetBrains tem [ticket aberto](https://youtrack.jetbrains.com/projects/LLM/issues/LLM-25880/Add-AST-based-refactoring-tools-to-the-AI-Assistant-via-MCP) para expor refactorings AST ao AI Assistant via MCP.
- **A lacuna que sobra é dupla**: (a) nenhuma dessas ferramentas **prova a economia** — a documentação do OHM-MCP não faz nenhuma afirmação sobre token ou determinismo; (b) todas oferecem operações **universais** (rename, extract), nenhuma permite transformar um procedimento composto e específico do projeto em uma **capacidade versionada**. Scaffolders (cookiecutter, plop, hygen) criam arquivos novos por template mas **não inserem estruturalmente em arquivos existentes** — exatamente a parte difícil que o "Generate →" do IntelliJ resolvia.

## Proposed Solution

O SEH é o **live template do IntelliJ, para agentes, medido**: o agente externo escreve uma capacidade de engenharia deste projeto **uma vez**; o SEH a valida, instala e instancia como operações **determinísticas** (~0 token, milissegundos). O SEH nunca chama modelo e envolve o agente de código já em uso (Claude Code, Codex, Kimi) sem substituí-lo.

A solução tem **três alavancas**, em ordem de valor:

1. **Capacidades do projeto (`seh capability`)** — *alavanca principal.* Uma capacidade é um procedimento composto e parametrizado, versionado em `.seh-capabilities/`; cada execução instancia uma operação. Exemplo real: adicionar um subcomando exige um bloco de subparser em `cli.py`, um handler e um teste. Capturado uma vez, vira `seh capability run add-cli-command --name=report`. É o que scaffolders não fazem (não editam arquivo existente) e o que refactorers universais não fazem (não compõem o procedimento específico do projeto).
2. **Compressão de exploração** — antes de editar, o agente precisa entender o código. Sem SEH, isso é feito com várias chamadas de Read/Grep/Glob, lendo arquivos inteiros para achar uma função ou seus usos. O SEH expõe `seh inspect <symbol>` e `seh neighbors <symbol>` (já existentes no CLI desde o M0, hoje presos ao adaptador Java) sobre o índice Python (`ast`): localização exata e relações estruturais em poucas linhas. Age em **toda tarefa**, não só quando um teste falha. Também é o substrato técnico da alavanca 1 — sem AST não há inserção estrutural.
3. **Compressão de evidência de runtime** — saída de teste/build/lint comprimida em evidência estruturada, ativa no ciclo de erro→reteste. É o que mantém o agente ciente do que aconteceu sem despejar log bruto no contexto.

O ciclo de vida de uma capacidade — **propor → confirmar → validar → instalar → instanciar → verificar → medir** — é o que amarra as três: cada operação executa a alavanca 1, dispensa a 2 (a estrutura já está codificada na capacidade) e produz a 3 como resultado verificado.

O diferencial de valor continua sendo **runtime + evidência + medição** — essa camada nunca dependeu de indexação simbólica de código; comprimir saída de `pytest` é parsing de formato de ferramenta, ortogonal a entendimento de código. Mas o **modo de entrega** muda: o autor rejeitou dependência de instalar um servidor externo (Serena) como pré-requisito de uso. O SEH é **self-contained** — instala em qualquer repositório com um único comando, sem processo externo — e se expõe via **MCP**, o protocolo que já faz funcionar em qualquer agente (Claude Code, Codex, Kimi, o que vier). Onde o produto precisar de capacidade simbólica mínima (por exemplo, mapear uma falha de teste até a função que a contém), ela é construída em **Python puro com o módulo `ast` da stdlib** — zero dependência externa, suficiente para o que o runtime/evidência exige, sem competir em profundidade com Serena ou Aider. O Serena deixa de ser dependência de produto e vira apenas **referência de benchmark opcional** — usado uma vez, em pesquisa, não instalado pelo usuário final.

## Key Hypothesis

Acreditamos que **um projeto pode acumular capacidades de engenharia como memória procedural versionada** — capturadas uma vez com o agente e instanciadas como operações determinísticas — e que isso vai **transferir trabalho recorrente do modelo para código revisável, reduzindo tokens e latência sem perder qualidade**, para **desenvolvedores que operam agentes de código e pagam a própria conta**.

São **duas hipóteses independentes**, avaliadas separadamente — uma pode passar sem a outra.

**Hipótese A — técnica (o portão).** Uma capacidade escrita a partir de **uma** implementação aceita passa pelos quatro gates: reproduz o exemplo original, gera corretamente um **segundo** caso com parâmetros diferentes, é idempotente, e recusa explicitamente uma estrutura incompatível. Duas capacidades de formatos diferentes reutilizam um vocabulário pequeno de primitivas, em vez de esconder scripts específicos.

Reprodução sozinha não basta — prova **fidelidade**, não reuso; uma capacidade que apenas memorizou um caso passa no gate 1 e falha como produto. O segundo caso é proposto pelo agente e **aprovado ou editado pelo dev**, para que o candidato não seja julgado só contra um exemplo que seu próprio autor escolheu.

**Hipótese B — econômica.** Com A confirmada, o braço com SEH consome **≥30% menos tokens** e **≥50% menos tempo de parede** que o baseline, com taxa de conclusão igual ou superior. O ganho cresce com repetição e com o tamanho do catálogo: uma capacidade instanciada uma única vez dá prejuízo (custo de captura > economia); o payback aparece a partir de N operações, e determinar N é resultado, não premissa.

### Bifurcação de resultado

```text
A falhou
    → tese central encerrada. Não há produto: capacidade que emite código
      quase-certo deterministicamente é pior que capacidade nenhuma.

A passou, B falhou
    → a memória procedural funciona, mas não se paga em token/tempo.
      Continua relevante para quem valoriza padronização, onboarding e
      governança — times, não o dev solo com cota estourando.
      Exige reposicionar o ICP ou encerrar a promessa econômica.
      NÃO exige encerrar o projeto.

A e B passaram
    → produto validado para o ICP original (dev solo que paga a própria conta).
```

O terceiro ramo é o alvo. O segundo é o que torna esta formulação mais robusta que a anterior: antes, um benchmark morno matava o projeto inteiro. **Mas ele muda o ICP** — e isso precisa estar dito, porque o gatilho original deste projeto foi estouro de cota, uma dor de dev solo, não de governança de time.

Os limiares de 30%/50% são apostas iniciais. O de latência é deliberadamente conservador em relação ao 8,7x medido na literatura de replay determinístico, porque o LLM permanece no circuito para o trabalho novo — só o procedimento conhecido sai da inferência.

## What We're NOT Building

- **Modelo LLM local** — fora da fronteira do produto por design. O SEH nunca chama modelo; modelos pertencem ao agente consumidor.
- **Roteamento entre modelos** (barato vs. frontier) — fora da fronteira pelo mesmo motivo e já coberto por agentes, RouteLLM e gateways.
- **Catálogo de refactorings universais** (rename global, extract method, inline, move-symbol como produto) — território de [act101](https://www.productcool.com/product/act101-ai-agent-refactor-port-code) (183 operações, 163 linguagens) e [OHM-MCP](https://www.ohm-mcp.dev/) (Python). O SEH captura capacidades **compostas e específicas do projeto**; não compete em quantidade de refactors genéricos.
- **Grafo/índice de repositório em profundidade de IDE** — não se compete com Serena/Aider em cobertura ou precisão de LSP. A capacidade simbólica própria (Python `ast`) cobre consulta pontual e localização de âncoras; não reescreve a AST.
- **Detecção automática de padrões a partir do histórico Git** (derivar capacidades sozinho a partir de commits antigos) — ideia atraente e provavelmente o passo seguinte, mas fuzzy demais para o MVP. No v1 o agente externo escreve o candidato; o SEH valida e instala.
- **Pontos de extensão preenchidos pelo modelo** — incompatíveis com a métrica do MVP: o custo de duas instanciações deixaria de ser comparável. Se existirem no futuro, serão outra categoria e outro baseline.
- **Composição entre capacidades no MVP** — adiada por dependências de versão, ciclos, propagação de parâmetros, conflitos de efeito e rollback. Capacidades compõem apenas primitivas do SEH.
- **Primitivas, plugins ou hooks arbitrários definidos pelo projeto** — o vocabulário é fechado e versionado pelo SEH; comandos do projeto aparecem apenas na verificação declarada.
- **Engineering IR completo / Context Package com budget** (M1 pleno: schema de tarefa, seleção priorizada, orçamento de tokens) — fica para depois do MVP. A Fase 1 usa só a fatia mínima do M1 (adaptador + consulta de símbolo), não o compilador de contexto inteiro.
- **Dependência de servidor externo instalado à parte** — Serena não é pré-requisito do SEH. Se usado, é só para o benchmark de pesquisa opcional.
- **Um agente de código próprio** — o princípio 6 do README é explícito: *wrap coding agents rather than become one*.
- **Suporte multi-linguagem amplo no v1** — o runtime e o indexador simbólico começam em Python só, porque a hipótese e o próprio SEH são Python.

## Success Metrics

| Métrica | Alvo | Como medir |
|---|---|---|
| **Gate 1 — Fidelidade** | Patch idêntico | Replay do candidato comparado à implementação aceita, **sobre os arquivos declarados**, não o repo inteiro |
| **Gate 2 — Generalização** | 2º caso correto, testes verdes | Parâmetros diferentes; caso proposto pelo agente e **aprovado/editado pelo dev**; verificação pela suíte, não por inspeção visual |
| **Gate 3 — Idempotência** | Reaplicar não duplica nem corrompe | Rodar duas vezes seguidas; segunda execução é no-op ou falha explícita, nunca duplicação silenciosa |
| **Gate 4 — Recusa segura** | Erro explícito, zero escrita parcial | Rodar contra estrutura incompatível (âncora ausente/alterada) e verificar que nada foi escrito |
| **Redução de tokens** | ≥30% vs. baseline (braço A) | Soma de input+output+cache do agente, mesma lista de tarefas, sessões distintas |
| **Redução de latência** (primária) | ≥50% de tempo de parede vs. baseline | Cronômetro por tarefa, do prompt até o teste verde. Registrar mediana e dispersão, não só média |
| **Preservação de qualidade** (guarda) | Taxa de conclusão ≥ baseline; testes do POC passando | Suíte de aceitação do projeto POC, avaliada por código, não por julgamento |
| **Payback de capacidade** | ≤5 operações | Custo de autoria/validação ÷ economia por instanciação. Determina se a capacidade se paga |
| **Compressão de evidência** | ≥10x em saída de teste com falha | Bytes de saída bruta ÷ bytes de evidência estruturada |
| **Compressão de exploração** (diagnóstica) | ≥5x em bytes por localização de símbolo | Bytes que `seh inspect`/`seh neighbors` devolvem ÷ bytes que grep+leitura manual do(s) arquivo(s) equivalente(s) exigiriam |

Latência e tokens **não são redundantes**: instanciar uma capacidade fechada zera a inferência na operação (ganho nos dois), mas a compressão de evidência reduz token sem reduzir latência proporcionalmente.

Nota metodológica crítica: o **onboarding do Serena é executado pelo LLM e consome tokens**. Uma sessão curta pode ter o custo de setup mascarando ou invertendo a economia. Custo de setup e custo marginal por tarefa devem ser reportados **separadamente**.

## Open Questions

- [x] ~~Qual foi o gatilho real ("por que agora")?~~ Respondido: estouro recorrente de cota de tokens semanal/mensal. Falta apenas quantificar (dias de antecipação, frequência) — Fase 5.
- [x] ~~O autor já rodou o Serena?~~ Respondido: não, o projeto nasceu como exercício de engenharia de software, sem conhecimento prévio do Serena.
- [x] ~~Tensão de escopo: manter indexador próprio por valor de aprendizado vs. consumir Serena?~~ Resolvida: o autor não quer dependência de instalar Serena; o SEH será self-contained. A capacidade simbólica própria deixa de ser opcional/fallback e passa a ser parte do produto — só que mínima (Python `ast`), não uma tentativa de igualar Serena/Aider em profundidade.
- [x] ~~O SEH entrega valor como servidor MCP ou wrapper de CLI?~~ Resolvida: MCP, para funcionar em qualquer agent code sem acoplamento — é a exigência explícita do autor.
- [x] ~~O que fazer com o indexador Java do PR #1?~~ Resolvida: paradigma muda de Java para Python. O indexador Java do PR #1 fica congelado como referência de arquitetura (proveniência, fingerprint, schema versionado); a implementação segue em Python com `ast`, não Tree-sitter.
- [ ] Natureza do projeto: OSS público, portfólio, interno ou comercial? *Assumption atual: portfólio/exercício técnico com distribuição OSS*; `license = "Apache-2.0"` no PR #1 indica intenção de publicar, mas a motivação declarada é aprendizado, não adoção de terceiros.
- [ ] Qual o tamanho e a forma do projeto POC? Precisa ser grande o bastante para o custo de leitura aparecer, pequeno o bastante para iterar.
- [ ] Como isolar variância do LLM entre sessões? Mesma tarefa gera consumo diferente por não-determinismo; quantas repetições para significância?
- [ ] O plano técnico do Context Compiler (mantido fora do versionamento) foi escrito para Java/Tree-sitter e precisa ser reescrito para Python/`ast` antes de virar trabalho executável — e reduzido à fatia mínima, já que o M1b saiu do caminho crítico.
- [ ] Qual o tipo de âncora AST do MVP para inserção em arquivo existente? Precisa ser um caso bem definido (ex.: bloco de subparser em `cli.py`), não um motor genérico.

---

## Users & Context

**Primary User**

- **Quem**: desenvolvedor individual que opera loop engineering com um agente de código e **paga a própria conta de tokens**. Tem proficiência técnica alta, tolera setup por CLI, e sente o custo diretamente na fatura.
- **Comportamento atual**: roda o agente contra o repositório; o agente executa testes/build, ingere saída bruta, re-tenta, e o contexto cresce a cada turno.
- **Gatilho**: o momento em que a tarefa entra em ciclo de erro→correção→reteste. É aí que a saída de runtime domina o contexto.
- **Estado de sucesso**: mesma tarefa concluída, mesma qualidade de artefato, consumo mensuravelmente menor — e o desenvolvedor consegue **ver o número**.

**Job to Be Done**

Quando **preciso fazer no meu projeto algo que já fiz antes do mesmo jeito**, eu quero **instanciar uma capacidade versionada como operação determinística, não redescobrir e reescrever o procedimento com o modelo**, para que **o LLM gaste esforço só no que é genuinamente novo**.

**Non-Users**

- Times de plataforma buscando governança e relatório corporativo de custo — governança não é o problema do v1.
- Quem quer navegação semântica de código em profundidade de IDE — isso é Serena/Aider; o SEH não compete nesse eixo.
- Quem não paga pelos próprios tokens: sem a dor na fatura, não há gatilho.

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Prioridade | Capacidade | Racional |
|---|---|---|
| Must | **`seh capability validate` / `install` / `run`** | **O produto.** O agente escreve o candidato; SEH roda os quatro gates, promove só o aprovado e instancia operações |
| Must | **Álgebra fechada de primitivas** | A menor linguagem determinística compartilhada por duas capacidades reais; sem plugins/hooks arbitrários |
| Must | **Inserção source-preserving: AST localiza, splice escreve** | `ast.unparse()` destrói comentários e formatação mesmo sem mudança; fidelidade exige patch localizado |
| Must | **Medidor de tokens e latência / harness de benchmark** | Sem medir, nada é falsificável. É o instrumento que valida ou mata o projeto |
| Must | **Adaptador Python (`ast`) + `seh inspect`/`seh neighbors`** | Alavanca 2 e substrato técnico da alavanca 1 — sem AST não há inserção estrutural |
| Must | **Command runner + compressão de saída → evidência** | Alavanca 3. Verifica o resultado do replay e mantém o agente ciente sem log bruto |
| Must | **Projeto POC + protocolo A/B** | O experimento; sem ele o número não significa nada |
| Must | **Self-contained, zero dependência externa** | Exigência explícita do autor — nada de instalar servidor externo como pré-requisito |
| Should | **Exposição via MCP** | Funciona em qualquer agent code (Claude Code, Codex, Kimi) sem acoplamento |
| Should | Capacidades versionadas em `.seh-capabilities/` | Compartilháveis, revisáveis em PR. Operações e evidência permanecem no estado local `.seh/` |
| Should | Aproveitar proveniência/frescor do PR #1 | Arquitetura reaproveitável; implementação muda de Tree-sitter/Java para `ast`/Python |
| Could | Derivar capacidade a partir de commit anterior | Passo natural seguinte; fuzzy demais para o MVP |
| Could | Engineering IR completo / Context Package com budget (M1 pleno) | Fica para depois do veredito |
| Could | Benchmark contra Serena | Referência de mercado opcional, não bloqueia a validação |
| Won't | Catálogo de refactorings universais (rename/extract/inline globais) | Território de act101 e OHM-MCP; consumir se precisar, não reimplementar |
| Won't | Modelo local, roteamento entre modelos | Fora da fronteira do produto por design; pertencem ao agente consumidor |
| Won't | Paridade de profundidade com Serena/Aider (LSP, 40+ linguagens) | Fora de escopo por design |

### MVP Scope

O mínimo para validar a hipótese, em ordem de dependência:

1. Duas **capacidades de formas diferentes**, escritas à mão no próprio SEH, para derivar a primeira álgebra de primitivas e provar que não são apenas casos hard-coded.
2. Um **medidor** de tokens *e* tempo de parede por tarefa.
3. Um **adaptador Python (`ast`)** + `seh inspect`/`seh neighbors` — exploração e localização estrutural; AST nunca reescreve fonte.
4. **`seh capability validate` / `install` / `run`** com capacidades reais instaladas, fixtures pré-implementação e splice textual source-preserving.
5. Um **runner + compressor** `pytest` → evidência, para verificar o replay.
6. O **experimento baseline vs. SEH**, com capacidades instanciadas N vezes para medir a curva de payback.

O ponto de falsificação mudou duas vezes. Não é mais "compressão gera delta?", nem apenas "em quantas repetições se paga?" — é primeiro **"um candidato passa nos quatro gates?"** (hipótese A, técnica, respondida na Fase 0) e só depois a curva de payback (hipótese B, econômica). Ver a bifurcação de resultado em *Key Hypothesis*.

### User Flow

```
─── CAMINHO A: tarefa repetitiva (o caso que o SEH otimiza) ───

dev: "adiciona o comando report na CLI"
      │
      ▼
agente seleciona capacidade ──► seh capability run add-cli-command --name=report
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
      │                            agente OFERECE capturar o procedimento
      │                                                 │
      │                                    dev confirma │ dev recusa ──► fim
      │                                                 ▼
      │                            agente escreve candidato + 2º caso proposto
      │                                                 │
      │                                    dev aprova/edita o 2º caso
      │                                                 ▼
      └──────────────────────► seh capability validate  (4 gates + fixtures)
                                                        │
                                          reprovado ◄────┴───► seh capability install
                                          (nada entra                  │
                                           no catálogo)      capacidade disponível
                                                             para o Caminho A

                    medidor registra tokens + latência em ambos
```

O Caminho B alimenta o Caminho A: cada padrão aprovado vira capacidade; cada uso futuro instancia uma operação e migra custo de inferência para execução.

---

## Technical Approach

**Feasibility**: **ALTA** para o MVP. Parser de saída de `pytest` é trabalho determinístico bem delimitado; medição de token é leitura de metadados já expostos pelos agentes; o repositório já tem substrato de CLI, config, storage e disciplina de proveniência vindos do PR #1. `seh inspect`/`seh neighbors` **já existem como comandos** desde o M0 — o trabalho da alavanca de exploração é escrever `python_adapter.py` e plugá-lo no indexador existente, não construir CLI nova.

**Architecture Notes**

- **Self-contained por design.** Nenhuma dependência de instalar um servidor MCP externo (Serena) como pré-requisito. O SEH é a única coisa que o usuário instala.
- **Indexação simbólica própria, em Python, via `ast` da stdlib.** Substitui o paradigma Tree-sitter/Java do PR #1. Escopo deliberadamente mínimo — o bastante para a evidência referenciar `arquivo:linha:função`, não uma tentativa de igualar LSP.
- **AST localiza; texto escreve.** `ast.unparse()` é proibido no caminho de mutação porque destrói comentários e reformata código mesmo sem mudança. Offsets AST validam a âncora; splice textual local preserva bytes e deriva estilo do texto vizinho.
- **Álgebra fechada.** Capacidades compõem somente primitivas implementadas e versionadas pelo SEH. Uma primitiva ausente é sinal de produto, não autorização para plugin ou hook arbitrário.
- **Seleção barata.** O modelo recebe apenas projeção compacta de intenção e parâmetros das capacidades aplicáveis; templates, fixtures e passos ficam fora do contexto.
- **Reaproveitar a disciplina de evidência do PR #1.** Fingerprint, schema versionado e recusa de dado obsoleto ("evidência confiável ou erro explícito") são exatamente a semântica que o `seh-evidence` precisa — a arquitetura sobrevive, a implementação (Tree-sitter Java) é substituída por `ast` Python.
- **Execução fora do contexto do modelo.** O runner roda no processo do SEH; o modelo só vê o resultado normalizado.
- **Exposto via MCP.** É o mecanismo concreto de "funciona em qualquer agent code" sem reescrever integração por cliente.
- **Um ecossistema primeiro (Python).** Multi-linguagem é escala, não validação.

**Technical Risks**

| Risco | Prob. | Mitigação |
|---|---|---|
| **Custo de capturar uma capacidade não se paga para o ICP original** | Alta | Métrica de payback (≤5 operações) na Fase 6; se a hipótese técnica passar e a econômica falhar, reposicionar o ICP ou encerrar a promessa econômica |
| **Inserção estrutural preserva semântica, mas destrói source fidelity** | Alta | AST apenas localiza; splice textual escreve e preserva bytes fora do fragmento; `ast.unparse()` excluído |
| **Uma capacidade só produz uma “álgebra” hard-coded** | Alta | Fase 0 exige duas capacidades de formas diferentes e registra quais primitivas foram compartilhadas ou divididas |
| **MVP com uma alavanca só (evidência) não move o número o bastante** | Alta | Adaptador Python e capacidades entram como Must; evidência é uma alavanca de suporte |
| Capacidade instalada fica obsoleta quando o padrão do projeto muda | Média | Precondições locais + verificação após a operação; estrutura incompatível falha antes de escrever |
| Seleção exige ler o catálogo inteiro e recria custo de contexto | Média | Filtro determinístico de aplicabilidade + projeção compacta somente de `intent` e parâmetros |
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
| 0 | **Spike da álgebra de capacidades** | Escrever **duas capacidades de formas diferentes** à mão, derivar primitivas compartilhadas, provar splice source-preserving e passar os quatro gates com fixtures. **Sem CLI ou schema final** | pending | - | - | - |
| 1 | Adaptador Python + consulta de símbolo | `python_adapter.py` + `seh inspect`/`seh neighbors` — substrato AST para âncoras estruturais | pending | with 2 | 0 | - |
| 2 | Runner + compressor de evidência | `pytest` executado fora do contexto → evidência estruturada | pending | with 1 | 0 | - |
| 3 | **`seh capability` — formato e runtime** | `seh.capability/v0.1`, primitivas fechadas, catálogo compacto, quatro gates e operações imutáveis — **o produto** | pending | - | 1, 2 | - |
| 4 | Dogfooding no próprio SEH | Instalar as duas capacidades da Fase 0 e usá-las em novos casos reais | pending | - | 3 | - |
| 5 | POC, instrumentação e baseline | Projeto POC com repetição real + medidor de tokens e latência + braço A | pending | with 3, 4 | 0 | - |
| 6 | Braço SEH, curva de payback e veredito | Medir tokens, latência e em quantas operações cada capacidade se paga | pending | - | 4, 5 | - |
| 7 | Exposição via MCP | Empacotar como servidor MCP self-contained | pending | - | 6 | - |
| 8 | Benchmark opcional (Serena / OHM-MCP) | Referência de mercado; não bloqueia release | pending | with 1–7 | - | - |

### Phase Details

**Fase 0: Spike da álgebra de capacidades** *(o portão — nada começa antes disso)*
- **Objetivo**: descobrir se existe uma linguagem determinística pequena e compartilhável para procedimentos reais, antes de investir em CLI, schema final, medição ou empacotamento.
- **Escopo**: escolher **dois padrões repetidos e de formas diferentes** no SEH — `add-cli-command` e um segundo candidato confirmado durante o spike. Escrever duas capacidades à mão, com fixtures sintéticas e versionadas do estado pré-implementação. Implementar apenas o necessário para AST localizar spans e splice textual produzir patches, nunca `ast.unparse()`.
- **Quatro gates por capacidade**: fidelidade sobre arquivos declarados; generalização em segundo caso aprovado/editado pelo dev; idempotência; recusa segura com zero escrita parcial.
- **Sinal de sucesso**: ambas passam os gates; o resto do arquivo tocado permanece byte a byte idêntico; e emerge um vocabulário pequeno com primitivas realmente compartilhadas.
- **Sinal de fracasso**: primitivas específicas para cada template, perda de comentários/formatação, excesso de casos especiais, ou incapacidade de recusar estrutura incompatível.
- **Entregas**: primeira álgebra fechada; dois pacotes de capacidade; fixtures dos quatro gates; protótipo AST→offset + splice; log de primitivas compartilhadas, divididas, adicionadas e rejeitadas.
- **Fora de escopo**: CLI de produção, schema definitivo, MCP, plugins, hooks arbitrários, pontos de extensão e composição entre capacidades.

**Fase 1: Adaptador Python + consulta de símbolo**
- **Objetivo**: substrato AST para as âncoras estruturais, e alavanca de exploração.
- **Escopo**: `python_adapter.py` via `ast` da stdlib — fatia mínima do Context Compiler: só parse, qualified name e spans, sem Engineering IR e sem budget; plugar no indexador existente; `seh inspect`/`seh neighbors`.
- **Sinal de sucesso**: localizar símbolo e relações consome visivelmente menos bytes que grep + leitura de arquivo; as âncoras improvisadas na Fase 0 passam a ser expressas via AST.

**Fase 2: Runner + compressor de evidência**
- **Objetivo**: executar sem gastar contexto e destilar o resultado.
- **Escopo**: descoberta/execução de teste, captura de stdout/stderr/exit code, timeout; parser `pytest` → falhas com `arquivo:linha`, mensagem e diff de assertion; formato versionado; evidência expansível sob demanda.
- **Sinal de sucesso**: ≥10x de compressão numa suíte com falhas, sem perda de informação acionável.

**Fase 3: `seh capability` — formato e runtime** *(o produto)*
- **Objetivo**: transformar o que a Fase 0 provou à mão em capacidade de primeira classe.
- **Escopo**: `seh.capability/v0.1`; primitivas fechadas; fixtures; projeção compacta de catálogo; **`seh capability validate`**, **`install`** e **`run`**; cada `run` instancia uma operação imutável. Contrato: `capacidade + parâmetros + estado-base compatível → mesmo plano e patch`. AST localiza; splice textual escreve.
- **Sinal de sucesso**: candidato reprovado nunca chega ao catálogo; capacidade aprovada produz o mesmo plano e patch, sem modelo no SEH e sem alterar bytes fora dos fragmentos declarados.

**Fase 4: Dogfooding no próprio SEH**
- **Objetivo**: provar as capacidades em código real antes de medir.
- **Escopo**: instalar as duas capacidades da Fase 0 e instanciá-las em novos casos necessários ao SEH.
- **Sinal de sucesso**: dois casos reais nascem de `seh capability run`, com testes verdes e sem edição manual do procedimento mecânico.

**Fase 5: POC, instrumentação e baseline**
- **Objetivo**: ter um número inicial confiável nos dois eixos.
- **Escopo**: POC em Python com estrutura real **e pelo menos um padrão genuinamente repetitivo**; lista fixa de tarefas; captura de tokens (input/output/cache) **e tempo de parede** por tarefa; protocolo de repetição documentado.
- **Sinal de sucesso**: mesma tarefa rodada N vezes produz consumo e latência dentro de faixas de dispersão conhecidas.

**Fase 6: Braço SEH, curva de payback e veredito**
- **Objetivo**: quantificar a economia, já com a viabilidade estabelecida na Fase 0.
- **Escopo**: rodar A (baseline) vs. SEH; reportar tokens, latência, dispersão, conclusão de tarefas, compressão e **em quantas operações uma capacidade se paga**.
- **Sinal de sucesso**: números defensáveis em qualquer direção. Payback alto demais não mata a tese de memória procedural — mas redefine para quem o produto vale a pena, e isso precisa estar escrito.

**Fase 7: Exposição via MCP**
- **Objetivo**: tornar o SEH utilizável em qualquer agent code.
- **Escopo**: servidor MCP expondo `capability run`, catálogo compacto, `inspect`, `neighbors` e `test`; instalação em um comando, sem processo externo.
- **Sinal de sucesso**: funciona nos três agentes do autor sem dependência além do próprio SEH.

**Fase 8: Benchmark opcional (Serena / OHM-MCP)**
- **Objetivo**: posicionamento — quanto da economia já é capturada por ferramentas existentes.
- **Escopo**: instalar, rodar a mesma lista, medir; custo de onboarding registrado à parte.
- **Sinal de sucesso**: número documentado. Não bloqueia nenhuma fase nem o release.

### Parallelism Notes

**A Fase 0 é o portão real e bloqueia tudo.** É deliberadamente artesanal porque precisa responder se duas capacidades distintas revelam uma álgebra pequena e source-preserving. Uma capacidade só provaria que sabemos hard-codear um caso.

Depois dela, 1 e 2 são paralelizáveis (adaptador e runner tocam superfícies distintas). A **Fase 3 depende das duas**: precisa do AST da 1 para inserir estruturalmente e da verificação da 2 para validar cada replay. A Fase 5 (POC e baseline) só depende da Fase 0 e pode correr em paralelo com 3 e 4 — construir o experimento não depende do produto estar pronto. A Fase 6 exige 4 e 5. A Fase 8 é pesquisa independente e roda a qualquer momento.

---

## Decisions Log

| Decisão | Escolha | Alternativas | Racional |
|---|---|---|---|
| **Tese do produto** | **Memória procedural versionada do projeto** — o projeto aprende como é construído | "Ferramenta de economia de token/latência" | Economia vira consequência, não promessa: sobrevive a um benchmark morno e é diferenciável sem precisar de número. Formulada pelo autor em `docs/PRODUCT_SCENARIO.md` |
| **Gatilho de captura** | Agente oferece, **dev confirma** | (a) agente decide sozinho após a 1ª vez; (b) SEH detecta na 2ª ocorrência via similaridade de diff | Após uma ocorrência não há como *saber* que recorre, só apostar. Quem tem contexto para decidir é o dev. Mantém o catálogo pequeno e confiável; (b) fica como evolução |
| **Unidade de aprendizagem** | **Capacidade** é o artefato versionado; **operação** é uma instanciação | Chamar o artefato persistido de operação | A capacidade descreve procedimento reutilizável; a operação possui parâmetros, plano, patch e evidência de uma execução concreta |
| **Generalização (arquivo → template)** | **Agente externo escreve** o template; SEH valida por reprodução | SEH deriva do diff; dev escreve à mão | O agente acabou de escrever o código e sabe o que é domínio vs. estrutura. SEH não infere essa fronteira — só rejeita capacidade que não reconstrói o próprio exemplo |
| **SEH chama modelo?** | **Nunca** — em nenhum milestone | SEH com provider próprio para criar capacidades | O agente externo materializa a capacidade. Elimina API key, billing, auth e configuração de modelo do produto inteiro |
| **Ponto de falsificação** | **Técnico** antes de econômico | Só econômico, via benchmark | Capacidade que emite código quase-certo deterministicamente é pior que capacidade nenhuma. Testável em dias — daí a Fase 0 |
| **Critério de aceite de um candidato** | **Quatro gates**: fidelidade, generalização, idempotência, recusa segura | Só reprodução do primeiro exemplo | Reprodução prova fidelidade, não reuso — uma capacidade que memorizou um caso passa no gate 1 e falha como produto |
| **Quem escolhe o 2º caso** | Agente propõe, **dev aprova ou edita** | Agente escolhe sozinho; dev projeta do zero | Agente sozinho se autoavalia contra um caso que ele escolheu. Dev projetando do zero adiciona atrito a cada captura. Aprovar/editar preserva o controle sem o custo |
| **Contrato de determinismo** | `capacidade + parâmetros + estado-base compatível → mesmo plano e patch`, escopado aos arquivos declarados | "Mesmo resultado no repositório" | Mudança não relacionada em outro arquivo não pode invalidar uma capacidade. Compatibilidade verificada por precondições locais, não por fingerprint global |
| **Mutação Python** | AST localiza spans; splice textual escreve | Modificar AST e chamar `ast.unparse()`; adotar LibCST | Parse/unparse altera comentários e formatação sem nenhuma mudança semântica. Splice preserva bytes e mantém zero dependência externa |
| **Vocabulário de primitivas** | Fechado, pequeno, versionado pelo SEH e derivado de duas capacidades | Plugins/scripts/hooks definidos pelo projeto | Primitiva ausente é sinal de produto. Vocabulário aberto cria API pública, superfície de segurança e comportamento opaco |
| **Estado-base dos gates** | Fixtures sintéticas, mínimas e versionadas com a capacidade | Repo atual; refs Git | A capacidade é escrita depois da implementação; o repo atual já contém os artefatos. Fixtures sobrevivem a rebase e squash |
| **Seleção de capacidade** | Filtro determinístico + projeção compacta de intenção | Modelo lê todos os manifestos | Ler templates e passos de 30 capacidades recriaria o custo de exploração que o produto quer remover |
| **Composição no MVP** | Capacidades compõem apenas primitivas | Capacidade chama capacidade | Evita versões, ciclos, conflito de efeitos, propagação de parâmetros e rollback distribuído |
| **Pontos de extensão no MVP** | Excluídos | Slots de código preenchidos pelo agente | Tornam o custo de duas instanciações incomparável e quebram a métrica econômica |
| **Semântica dos comandos** | `validate` → `install` → `run` | `record` (ambíguo: SEH não grava com LLM) | O agente escreve o candidato; SEH julga. Separar `validate` de `install` garante que candidato reprovado nunca entre no catálogo |
| **Onde ficam capacidades e operações** | Capacidades em `.seh-capabilities/`; operações/evidência em `.seh/` | `.seh/operations/`; `.seh-operations/` | Memória procedural é revisável em PR; instâncias de runtime são estado local e derivado |
| **Adaptadores de modelo / roteamento** | **Fora da fronteira do produto** — removidos do roadmap | "Adiados para M5" | Decorre do invariante "SEH nunca chama modelo": um componente que não invoca modelo não tem por que escolher um. Pertence ao agente consumidor |
| Centro da implementação | **Capacidade versionada → operação determinística (`seh capability`)** | Só medição; catálogo de refactors; apenas leitura | IDEs já automatizavam procedimentos deterministicamente. A lacuna é a capacidade composta e específica do projeto, não a operação universal |
| **Latência como métrica primária** | Sim, ao lado de tokens | Só token; latência como secundária | Levantada pelo autor e ausente do documento até aqui. Substituir inferência (3–8s) por execução (ms) pode ser o ganho mais perceptível no uso diário |
| Camada de diferenciação | Capacidades + operações determinísticas + evidência + medição | Grafo próprio de repositório em profundidade de IDE | Grafo profundo é commodity (Serena MIT, 40+ linguagens; Aider PageRank) |
| Dependência de produto | Self-contained, zero servidor externo | Consumir Serena/LSP como adaptador obrigatório | Exigência explícita do autor: não quer instalar Serena para o SEH funcionar |
| Indexação simbólica | Python `ast` da stdlib, escopo mínimo | Tree-sitter multi-linguagem; nenhum indexador próprio | Zero dependência externa; suficiente para a evidência referenciar símbolos; não compete em profundidade |
| Modo de entrega | Servidor MCP | Wrapper de CLI que orquestra o agente | "Funciona em qualquer agent code" exige o protocolo que os agentes já falam |
| Usuário primário | Dev solo que paga os próprios tokens | Time de plataforma; tech lead | Escolha do autor; alinha o produto a setup rápido e feedback direto |
| Ordem de validação | Viabilidade técnica antes da infraestrutura; economia antes do release | Construir o produto inteiro antes de validar | Fase 0 testa os quatro gates artesanalmente; Fases 5–6 medem a economia antes de investir em distribuição |
| Papel do Serena | Benchmark de pesquisa opcional | Dependência de produto (versão anterior desta decisão) | Revertido nesta sessão — autor não quer instalação externa obrigatória |
| Linguagem do runtime v1 | Python | Java (seguindo o indexador atual) | O POC e o SEH são Python; autor concordou em migrar o paradigma |
| PR #1 (indexador AST Java) | Congelar como referência de arquitetura | Reverter; estender em Java | Disciplina de proveniência/fingerprint é reaproveitável; implementação Tree-sitter/Java é substituída por `ast`/Python |
| Plano técnico do Context Compiler | Mantido fora do versionamento; precisa ser reescrito para Python/`ast` | Executar como está (Java); versionar no repo | Escrito antes da decisão de migrar para Python. Desrastreado por decisão do autor — é material de trabalho, não documentação pública do projeto |
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
| Roteamento de modelo | RouteLLM, gateways | Ocupada e fora da fronteira do produto |
| **Capacidade composta específica do projeto** | — | **Livre** |
| **Prova de economia no repo do usuário** | — | **Livre** — OHM-MCP não faz nenhuma afirmação sobre token ou determinismo |

A lacuna que sustenta o SEH é a interseção das duas últimas linhas: **capturar uma capacidade de engenharia deste projeto, instanciá-la como operações determinísticas e provar a economia com número**. Inserção estrutural source-preserving em arquivo existente é a fronteira técnica.

**Technical Context**

O repositório está em `0.1.0a2` e o PR #1 já foi incorporado à `main`. Ele substituiu regex por Tree-sitter, introduziu identidades qualificadas, schema SQLite v2, proveniência, fingerprint e detecção de índice obsoleto. A suíte atual de 27 testes foi executada e passou durante esta revisão documental.

O ativo reaproveitável do PR para o novo posicionamento **não é o parser Java** — é a disciplina de proveniência e frescor: evidência confiável ou erro explícito, nunca dado obsoleto silencioso. Essa é a semântica que o `seh-evidence` precisa.

---

*Generated: 2026-08-10*
*Status: DRAFT — needs validation*
