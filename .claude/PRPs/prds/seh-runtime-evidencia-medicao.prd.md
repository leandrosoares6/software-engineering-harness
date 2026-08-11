# SEH — Runtime Determinístico, Evidência e Medição

## Problem Statement

Desenvolvedores que operam loop engineering com agentes de código pagam tokens caros para o modelo executar trabalho que engenharia de software resolve deterministicamente. A maior fatia do custo não é raciocínio: é **leitura** — o agente ingerindo saída bruta de teste, build, lint e diff, turno após turno. Sem instrumentação, o desenvolvedor não sabe quanto disso é desperdício nem consegue provar que qualquer mitigação funcionou.

## Evidence

- **Operações de leitura consomem 76,1% dos tokens** de um agente de código, contra 12,1% de execução e 11,8% de edição ([Augment Code](https://www.augmentcode.com/guides/ai-coding-cost-analysis-agent-token-spend)). O gargalo de custo é ingestão de contexto, não geração.
- **Tokens de input re-enviados a cada turno representam >99% do volume de trajetória** em traces publicados de agentes. Saída de runtime que entra no contexto é paga repetidamente, não uma vez.
- Relato do autor: mesma dor observada em **3 ferramentas de players distintos** — o LLM gastando tokens caros em processos simples. *Assumption — não quantificado; sem baseline de fatura ou trace. Validar na Fase 1.*
- **Gatilho ("por que agora"): estouro de cota de tokens semanal/mensal muito rápido.** O autor esgota a cota do agente antes do previsto, recorrentemente, em pelo menos 3 ferramentas distintas. Ainda sem número (quantos dias antes do previsto, com que frequência) — validar na Fase 1 junto com o baseline.
- **O autor não conhecia o Serena antes desta conversa.** O projeto nasceu para ser desenvolvido do zero como exercício de engenharia de software, não como resposta a uma lacuna já mapeada no mercado. Isso não invalida o problema (o gatilho de cota é real e independente), mas significa que a decisão de "grafo é commodity" é uma descoberta desta sessão, não uma premissa original do projeto — ver nota em Open Questions sobre tensão de escopo.
- Prior art confirma o problema mas **não cobre esta camada**: Serena declara explicitamente não tratar execução de teste, build, medição de custo ou roteamento ([oraios/serena](https://github.com/oraios/serena)).

## Proposed Solution

O SEH passa a ser uma camada de **runtime determinístico + evidência estruturada + medição**, que envolve o agente de código já em uso (Claude Code, Codex, Kimi) sem substituí-lo. Em vez de o agente executar `pytest` e ingerir 3.000 linhas de saída, o SEH executa, faz o parse e devolve evidência normalizada — falhas, `arquivo:linha`, diff de assertion — em dezenas de linhas. O mesmo vale para build, lint e diff.

O diferencial de valor continua sendo **runtime + evidência + medição** — essa camada nunca dependeu de indexação simbólica de código; comprimir saída de `pytest` é parsing de formato de ferramenta, ortogonal a entendimento de código. Mas o **modo de entrega** muda: o autor rejeitou dependência de instalar um servidor externo (Serena) como pré-requisito de uso. O SEH é **self-contained** — instala em qualquer repositório com um único comando, sem processo externo — e se expõe via **MCP**, o protocolo que já faz funcionar em qualquer agente (Claude Code, Codex, Kimi, o que vier). Onde o produto precisar de capacidade simbólica mínima (por exemplo, mapear uma falha de teste até a função que a contém), ela é construída em **Python puro com o módulo `ast` da stdlib** — zero dependência externa, suficiente para o que o runtime/evidência exige, sem competir em profundidade com Serena ou Aider. O Serena deixa de ser dependência de produto e vira apenas **referência de benchmark opcional** — usado uma vez, em pesquisa, não instalado pelo usuário final.

## Key Hypothesis

Acreditamos que **compressão determinística de saída de runtime em evidência estruturada** vai **reduzir o consumo de tokens de um loop engineering, preservando a qualidade dos artefatos**, para **desenvolvedores que operam agentes de código e pagam a própria conta**.

Saberemos que estamos certos quando, no mesmo projeto POC, mesmo agente e mesma lista de tarefas, o braço com SEH consumir **≥30% menos tokens totais** que o braço sem SEH (baseline), com **taxa de conclusão de tarefas igual ou superior**.

O limiar de 30% é uma aposta inicial, não um número derivado. Ele existe para ser falsificado — se o delta real for 5%, a tese morre barato. A comparação com Serena isolado permanece útil como referência de mercado (quanto da economia já é resolvido por navegação semântica de código, sem nenhum SEH), mas deixou de ser condição para validar a hipótese central.

## What We're NOT Building

- **Modelo LLM local** — adiado explicitamente pelo autor. Evolução futura, fora do v1.
- **Roteamento entre modelos** (barato vs. frontier) — decorre do item acima; sem modelo local, não há para onde rotear. Território já ocupado por RouteLLM e gateways.
- **Grafo/índice de repositório em profundidade de IDE** — não se compete com Serena/Aider em cobertura ou precisão de LSP. A capacidade simbólica própria (Python `ast`) é mínima, a serviço da evidência, não um produto de navegação de código.
- **Dependência de servidor externo instalado à parte** — Serena não é pré-requisito do SEH. Se usado, é só para o benchmark de pesquisa opcional.
- **Um agente de código próprio** — o princípio 6 do README é explícito: *wrap coding agents rather than become one*.
- **Suporte multi-linguagem amplo no v1** — o runtime e o indexador simbólico começam em Python só, porque a hipótese e o próprio SEH são Python.

## Success Metrics

| Métrica | Alvo | Como medir |
|---|---|---|
| **Redução de tokens** (primária) | ≥30% vs. baseline (braço A) | Soma de input+output+cache do agente, mesma lista de tarefas, sessões distintas |
| **Preservação de qualidade** (guarda) | Taxa de conclusão ≥ baseline; testes do POC passando | Suíte de aceitação do projeto POC, avaliada por código, não por julgamento |
| **Compressão de evidência** | ≥10x em saída de teste com falha | Bytes de saída bruta ÷ bytes de evidência estruturada |
| **Custo de setup amortizado** | Payback em ≤10 tarefas | Tokens de onboarding ÷ economia marginal por tarefa |

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

Quando **meu agente entra num ciclo de erro e reteste e o contexto começa a inchar**, eu quero **que a saída de runtime chegue ao modelo já destilada em evidência**, para que **eu resolva a tarefa gastando token em raciocínio, não em leitura de log**.

**Non-Users**

- Times de plataforma buscando governança e relatório corporativo de custo — governança não é o problema do v1.
- Quem quer navegação semântica de código em profundidade de IDE — isso é Serena/Aider; o SEH não compete nesse eixo.
- Quem não paga pelos próprios tokens: sem a dor na fatura, não há gatilho.

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Prioridade | Capacidade | Racional |
|---|---|---|
| Must | **Medidor de tokens / harness de benchmark** | Sem medir, nada é falsificável. É o instrumento que valida ou mata o projeto |
| Must | **Command runner determinístico** | Executa teste/build/lint fora do contexto do modelo |
| Must | **Compressão de saída → evidência estruturada** | O mecanismo de economia. Onde os 76,1% de leitura são atacados |
| Must | **Projeto POC + protocolo A/B** | O experimento; sem ele o número não significa nada |
| Must | **Self-contained, zero dependência externa** | Exigência explícita do autor — nada de instalar Serena como pré-requisito |
| Should | **Exposição via MCP** | Funciona em qualquer agent code (Claude Code, Codex, Kimi) sem acoplamento — é como "instala em qualquer repo" se torna real |
| Should | **Indexador simbólico próprio em Python (`ast`)** | Mínimo necessário para a evidência referenciar símbolos (ex.: falha de teste → função). Não compete em profundidade com Serena/Aider |
| Should | Aproveitar proveniência/frescor do PR #1 | Arquitetura reaproveitável; implementação muda de Tree-sitter/Java para `ast`/Python |
| Could | Política de retry determinística | Decidir re-tentar sem consultar o modelo |
| Could | Braço C — benchmark contra Serena | Referência de mercado opcional, não bloqueia a validação da hipótese |
| Won't | Modelo local, roteamento entre modelos | Adiado pelo autor — evolução futura |
| Won't | Paridade de profundidade com Serena/Aider (LSP, 40+ linguagens) | Fora de escopo por design; o indexador próprio é deliberadamente mínimo |

### MVP Scope

O mínimo para validar a hipótese, em ordem de dependência:

1. Um **projeto POC** em Python com suíte de testes e uma lista fixa de tarefas de engenharia reproduzíveis.
2. Um **medidor** que capture input/output/cache tokens por sessão do agente.
3. Um **runner + compressor** para um único caso: `pytest` → evidência estruturada de falhas.
4. O **experimento baseline vs. SEH**, rodado o suficiente para distinguir sinal de variância. O benchmark contra Serena (braço opcional) fica fora do caminho crítico do MVP.

Um único caso comprimido (`pytest`) já basta para falsificar a hipótese. Se a compressão do caso mais favorável não produzir delta, os outros não vão salvar.

### User Flow

```
dev define tarefa
      │
      ▼
agente pede execução de teste ──► SEH runner (fora do contexto)
                                        │
                                   saída bruta 3.000 linhas
                                        │
                                   parser determinístico
                                        │
                                   evidência: 2 falhas, arquivo:linha, diff
                                        │
                                        ▼
                              agente recebe 30 linhas ──► raciocina ──► corrige
                                        │
                                        ▼
                                 medidor registra consumo
```

---

## Technical Approach

**Feasibility**: **ALTA** para o MVP. Parser de saída de `pytest` é trabalho determinístico bem delimitado; medição de token é leitura de metadados já expostos pelos agentes; o repositório já tem substrato de CLI, config, storage e disciplina de proveniência vindos do PR #1.

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
| Variância entre sessões do LLM mascara o efeito | Alta | Repetições; reportar dispersão, não só média; tarefas determinísticas |
| Indexador Python (`ast`) próprio vira scope creep e passa a competir com Serena/Aider em profundidade | Média | MoSCoW trava explicitamente: só o mínimo para a evidência referenciar símbolos, sem viés de IDE |
| Compressão descarta informação que o agente precisava → qualidade cai | Média | Métrica-guarda de conclusão; evidência deve ser expansível sob demanda |
| Agentes não expõem contagem de token de forma uniforme | Média | Começar por um agente só; abstrair depois |
| Benchmark contra Serena (braço C) vira bloqueio informal mesmo sendo opcional | Baixa | Tratar como pesquisa paralela; não é dependência de release |

---

## Implementation Phases

| # | Fase | Descrição | Status | Parallel | Depends | PRP Plan |
|---|---|---|---|---|---|---|
| 1 | Baseline e instrumentação | POC + medidor de tokens + braço A | pending | - | - | - |
| 2 | Runner determinístico | Execução de teste fora do contexto do modelo | pending | with 3 | 1 | - |
| 3 | Compressor de evidência | `pytest` → evidência estruturada | pending | with 2 | 1 | - |
| 4 | Braço SEH e veredito | Medir o delta do SEH sobre o baseline; decidir seguir ou parar | pending | - | 2, 3 | - |
| 5 | Exposição via MCP | Empacotar como servidor MCP self-contained | pending | - | 4 | - |
| 6 | Benchmark opcional (Serena) | Referência de mercado; não bloqueia release | pending | with 1–5 | - | - |

### Phase Details

**Fase 1: Baseline e instrumentação**
- **Objetivo**: ter um número inicial confiável.
- **Escopo**: projeto POC em Python; lista fixa de tarefas; captura de input/output/cache tokens por sessão; protocolo de repetição documentado.
- **Sinal de sucesso**: mesma tarefa rodada N vezes produz consumo dentro de uma faixa de dispersão conhecida.

**Fase 2: Runner determinístico**
- **Objetivo**: executar sem gastar contexto.
- **Escopo**: descoberta e execução de teste; captura de stdout/stderr/exit code; timeout; determinismo.
- **Sinal de sucesso**: agente obtém resultado de teste sem a saída bruta entrar no contexto.

**Fase 3: Compressor de evidência**
- **Objetivo**: destilar saída em evidência.
- **Escopo**: parser de `pytest` → falhas com `arquivo:linha`, mensagem e diff de assertion; formato estável e versionado; evidência expansível sob demanda; indexador Python (`ast`) mínimo para mapear falha até função/símbolo quando necessário.
- **Sinal de sucesso**: ≥10x de compressão numa suíte com falhas, sem perda de informação acionável.

**Fase 4: Braço SEH e veredito**
- **Objetivo**: falsificar ou confirmar a hipótese.
- **Escopo**: rodar A (baseline) vs. SEH; reportar tokens, dispersão, conclusão de tarefas, compressão e payback.
- **Sinal de sucesso**: um número defensável — em qualquer direção. **Delta insuficiente é resultado válido e encerra o projeto barato.**

**Fase 5: Exposição via MCP**
- **Objetivo**: tornar o SEH self-contained e utilizável em qualquer agent code.
- **Escopo**: servidor MCP com as ferramentas de runtime/evidência; instalação em um comando, sem processo externo para configurar.
- **Sinal de sucesso**: funciona nos três agentes do autor (Claude Code, Codex, Kimi) sem dependência de nada além do próprio SEH.

**Fase 6: Benchmark opcional (Serena)**
- **Objetivo**: saber quanto da economia de mercado já é capturada por navegação semântica isolada, como dado de posicionamento.
- **Escopo**: instalar Serena uma vez, rodar a mesma lista de tarefas, medir; custo de onboarding registrado separadamente.
- **Sinal de sucesso**: número documentado. Não bloqueia nenhuma outra fase nem o release.

### Parallelism Notes

2 e 3 são paralelizáveis: o runner (execução, captura, timeout) e o compressor (parsing de saída) tocam superfícies distintas e se encontram num contrato de dados. A fase 6 (Serena) é pesquisa independente e pode rodar a qualquer momento em paralelo às demais — deixou de ser portão. As fases 1→2/3→4→5 permanecem sequenciais: cada uma informa a seguinte.

---

## Decisions Log

| Decisão | Escolha | Alternativas | Racional |
|---|---|---|---|
| Camada de diferenciação | Runtime + evidência + medição | Grafo próprio de repositório em profundidade de IDE | Grafo profundo é commodity (Serena MIT, 40+ linguagens; Aider PageRank). Runtime/evidência/medição está vago |
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

---

## Research Summary

**Market Context**

O problema está provado por terceiros — leitura domina o custo (76,1%) e input re-enviado responde por >99% do volume de trajetória. Mas a camada de contexto já tem dois ocupantes maduros e gratuitos: **Serena** (MCP+LSP, 40+ linguagens, MIT, roda sem IDE, conecta a Claude Code/Codex/Kimi em poucos comandos) e **Aider repo-map** (tree-sitter, PageRank, orçamento de tokens). Roteamento de modelo também é território ocupado (RouteLLM: 75–85% de redução em tráfego roteado).

A lacuna real está em **runtime, evidência e medição**: a documentação do Serena declara que ele não trata execução de teste, build, medição de custo nem roteamento. Benchmarks de contexto existem apenas no meio acadêmico (ContextBench, SWE Context Bench, SWE-Pruner) — não como ferramenta que o desenvolvedor roda no próprio repositório.

**Technical Context**

O repositório está em `0.1.0a2` com o PR #1 aberto (1510+/231−, 21 arquivos). O PR substituiu regex por Tree-sitter, introduziu identidades qualificadas e resolução determinística com ordem correta do Java, schema SQLite v2, proveniência, fingerprint e detecção de índice obsoleto. Corrigiu o defeito de colisão de nomes simples que gerava arestas erradas — `TypeCatalog.resolve` retorna `ambiguous` em vez de chutar. Validação declarada no PR (27 testes, 92,75% de cobertura de branch) não foi verificada de forma independente.

O ativo reaproveitável do PR para o novo posicionamento **não é o parser Java** — é a disciplina de proveniência e frescor: evidência confiável ou erro explícito, nunca dado obsoleto silencioso. Essa é a semântica que o `seh-evidence` precisa.

---

*Generated: 2026-08-10*
*Status: DRAFT — needs validation*
