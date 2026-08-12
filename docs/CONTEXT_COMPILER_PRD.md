# PRD — SEH Context Compiler v0.2

**Status:** Draft  
**Versão:** 0.2  
**Base:** Software Engineering Harness (SEH) v0.1.0a3  
**Tipo:** pivot de produto  
**Última revisão:** após crítica de v0.1

---

## 1. Visão curta

O SEH deixa de ser um sistema de *capabilities* reutilizáveis e passa a ser um **compilador de contexto** para coding agents.

Objetivo: receber um prompt humano, geralmente em português e na linguagem de domínio do desenvolvedor, e entregar um **pacote de contexto estruturado, pequeno e ancorado na árvore Git**, usando apenas computação determinística local.

O LLM recebe o pacote e parte direto para raciocinar, sem redescobrir o repositório.

> **O LLM não deve redescobrir o repositório. Ele deve raciocinar sobre o que o repositório já revela.**

---

## 2. O que foi medido, e o que apenas se suspeita

As duas coisas ficam separadas de propósito. A versão anterior desta seção as juntou, e o resultado leu mais forte do que a evidência sustenta.

### Medido, e o sinal é negativo

**Reuso de edição não se paga na frequência observada.**

Uma varredura de campo num repositório em produção — 654 commits, 15 meses, 5 autores — encontrou um procedimento genuíno de "adicionar mais um módulo com entrada em registry central". Ele recorreu **3 vezes em 5 meses, entre 2 autores diferentes**, e a recorrência foi *encontrada*, não fabricada. O wiring mecânico é de **4 linhas em 1242 inserções**, e os três primitivos que ele exigiria (`file.render`, `python.import_block`, `splice.into_collection`) não existem no SEH. Implementá-los com a disciplina dos quatro gates é trabalho de dias. Break-even: **anos**.

O POC anterior chegou ao mesmo lugar por outro eixo — ~15 min de autoria contra ~60s por repetição manual, break-even em 15–30 repetições — mas sobre um projeto de brinquedo cujos comandos eram `print(nome)`. O número de campo é o que vale, e é pior.

Este é o resultado mais sólido que o projeto produziu, e é negativo. É o que justifica abandonar o produto anterior.

### Suspeitado, sem medição limpa

**Descoberta parece ser cara. Isso não está estabelecido.**

O probe registrou 54 → 27 tool calls e 123k → 96k tokens entre um agente sem tratamento e um agente recebendo a descrição do procedimento. O delta **não é atribuível** ao tratamento, e `PROBE_FINDINGS.md` declara três razões:

- o agente do Arm A **encontrou e usou o pacote da capacidade** como documentação, então também tinha a convenção — não era um baseline sem documentação;
- o escopo diferiu: o Arm A ainda refatorou outro módulo, +97 linhas;
- n = 1 por arm, sem controle de não-determinismo do modelo.

O que resta é observação estrutural, não medida: no repositório de campo, o registry tem 607 linhas e os três pontos de edição ficam dentro de uma única função, na linha 515. Isso torna "caro" **plausível**. Não o mede.

### Por que mirar aí de qualquer forma

Três razões, e a terceira é a que decide:

1. é a única hipótese que sobra depois do resultado negativo;
2. é consistente com tudo que foi observado, inclusive com o agente que preferiu o pacote da capacidade ao resto do repositório;
3. **testá-la custa um dia** (§16, Fase 0), contra as semanas que o produto anterior consumiu antes de falhar.

O erro anterior não foi escolher a hipótese errada. Foi construir semanas antes de testá-la.

---

## 3. Hipótese de produto

Se o SEH puder mapear termos da linguagem de domínio do desenvolvedor (prompt em português) para arquivos e símbolos do repositório (código em inglês) usando sinais determinísticos — principalmente **histórico Git** —, então um coding agent que receba o pacote resultante fará menos operações exploratórias antes da primeira edição correta.

A hipótese não é sobre tokens. É sobre **tool calls até a primeira edição correta**.

---

## 4. O que muda em relação ao SEH anterior

| Antes (capabilities) | Agora (Context Compiler) |
|---|---|
| Capturar edições recorrentes | Compilar contexto relevante |
| Reutilizar mudanças de código | Evitar redescoberta do repositório |
| Quatro gates de validação | Proveniência + medição de exploração evitada |
| Vocabulário fechado de primitivas | Expansão de grafo + histórico Git como índice de termos |
| Instalar capability em `.seh-capabilities/` | Gerar `.context/<task>/context.md` ancorado em um commit |

A base do SEH continua válida: indexação Python via AST, grafo versionado em SQLite, integração Git, CLI.

---

## 5. O defeito central que v0.1 ignorou: seed resolution

Todo o valor está em acertar o *seed*.

Prompt: *"Renovação de licença caindo em CNH"*. Código: `Classifier.match`, `ServiceDefinition`. Nenhum termo do prompt aparece nos identificadores.

Matching lexical falha nesse caso. E é justamente esse caso — tradução domínio→código — que justifica o produto.

### A saída determinística que v0.1 relegou

Mensagens de commit são escritas na linguagem de domínio do desenvolvedor. O repositório usado na varredura de campo — 654 commits, 15 meses, 5 autores — tem assuntos em português: "renovação", "classificação", "licença". Cada commit aponta para arquivos e, indiretamente, para símbolos.

O repositório é referenciado sem identificação porque este documento é público e aquele não é. A evidência que importa é a forma e a frequência, não a identidade: contagem de commits, janela temporal, número de autores e idioma dos assuntos.

**Mecanismo principal do Seed Resolver:** casar termos do prompt contra mensagens de commit, e usar os arquivos daqueles commits como seeds.

Isso não exige LLM nem embeddings. Exige:

- índice invertido de termos → commits;
- mapeamento commit → arquivos modificados;
- mapeamento arquivo → símbolos indexados.

---

## 6. Escopo do MVP

### Entra no MVP

- Índice incremental do repositório (`seh index`).
- Índice de termos de mensagens de commit → commits → arquivos.
- Seed Resolver com duas fontes:
  1. matching direto contra símbolos e arquivos (caso fácil);
  2. matching via histórico Git (caso domínio→código).
- Expansão de grafo pelas arestas que o índice **realmente emite** (`declares`, `contains`, `imports`, `extends`), mais referência lexical de nome. Grafo de chamadas fica fora do MVP — ver §11.
- Dois níveis de representação: `summary` (assinatura + docstring) e `source` (código completo).
- Geração de `context.md` com seções fixas.
- CLI simples: `seh compile "prompt" --output ./context`.
- Explicabilidade: cada símbolo inclui `included_because`.
- Proveniência: `context.md` registra o commit/tree de origem e falha alto se a árvore mudou.

### Não entra no MVP

- Task Interpreter com LLM.
- Relevance engine com scoring complexo.
- Embeddings como mecanismo principal.
- Adapters para múltiplos providers.
- Architecture rules engine.
- Validation loop pós-geração.
- Edição de código.
- Suporte a múltiplas linguagens.

---

## 7. Arquitetura mínima

```text
Developer Prompt
       │
       ▼
┌──────────────────────────┐
│  Seed Resolver           │
│  ├── symbol/file match   │
│  └── git-history match   │  ← mecanismo principal
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  Graph Expander            │  ← BFS determinística: 1–2 hops
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  Representation Selector   │  ← summary vs source, heurística simples
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  Context Compiler        │  ← monta context.md + proveniência
└────────────┬─────────────┘
             │
             ▼
        context.md
             │
             ▼
           LLM
```

### Componentes reutilizados do SEH

- `seh index` → popula/atualiza o grafo.
- `GraphStore` → SQLite com nodes, edges, metadata. **Quatro** tipos de aresta reais, não seis — ver §11.
- `python_adapter` → AST Python. Não extrai chamadas.
- `git` → tracked files, HEAD, diff, commit messages.

### Novos componentes

- `seh.context.seed_resolver` → symbol/file match + git-history match.
- `seh.context.expander` → BFS limitada no grafo.
- `seh.context.renderer` → Markdown estruturado.
- `seh compile` → novo comando CLI.

---

## 8. CLI

```bash
# indexa ou atualiza o repositório
seh index

# compila contexto a partir de um prompt
seh compile "Arrumar o bug na classificação de renovação de licença" --output ./context

# usa uma seed explícita quando o desenvolvedor já sabe
seh compile "Renovação de licença caindo em CNH" --seed Classifier.match --output ./context

# mostra por que cada símbolo foi incluído
seh explain ./context
```

---

## 9. Formato do Context Package

Arquivo `.context/<task-id>/context.md`:

````markdown
# Task
Arrumar o bug na classificação de renovação de licença

## Provenance
- repository: /path/to/repo
- commit: a91fc31d...
- tree: 7b3e9a...
- generated_at: 2026-08-12T14:30:00Z

## Seeds
- `Classifier.match` (from git history: commit 91bd721 "Ajusta classificação de renovação de licença")
- `ServiceDefinition` (from git history: commit 44c8a1 "Adiciona definição de serviços de licenciamento")

## Target Symbols
### `Classifier.match(query: str) -> ServiceMatch`
- file: `src/services/classifier.py:42`
- included because: seed from git history

<source>
```python
def match(query: str) -> ServiceMatch:
    ...
```
</source>

## Related Symbols
### `Classifier.score_service(query: str, candidates: list) -> ServiceMatch`
- file: `src/services/classifier.py:81`
- included because: 1-hop caller from `Classifier.match`

<summary>
Calcula score entre query e candidatos.
</summary>

## Tests
### `tests/services/test_classifier.py::test_service_classification`
- included because: references `Classifier.match`

## Recent Changes
- `91bd721` — `Ajusta classificação de renovação de licença` (`src/services/classifier.py`, `src/services/scoring.py`)

## Unknowns
- Term "CNH" matched no symbols or commits.
````

Todos os identificadores acima — `Classifier.match`, `ServiceDefinition`, caminhos e SHAs — são sintéticos e ilustrativos. Não correspondem a nenhum repositório real, e não devem ser conferidos contra um.

O formato é Markdown porque é legível por humanos e LLMs, não exige adapters específicos, e é fácil de inspecionar.

---

## 10. Seed Resolver

### 10.1 Symbol/File Match (caso fácil)

- Símbolos e arquivos cujos nomes aparecem literalmente no prompt.
- Matching por substring, camelCase/snake_case split.

### 10.2 Git-History Match (caso domínio→código)

Este é o mecanismo principal.

Passos:

1. Tokenizar mensagens de commit (assunto + corpo, quando disponível).
2. Construir índice invertido termo → lista de commits.
3. Tokenizar o prompt.
4. Para cada termo do prompt, recuperar commits contendo termos similares.
5. Ranquear commits por número de termos coincidentes.
6. Para os top-N commits, extrair arquivos modificados.
7. Mapear arquivos para símbolos indexados naqueles arquivos.

Exemplo:

```text
prompt: "Renovação de licença caindo em CNH"
termos: [renovação, licença, caindo, cnh]

commits:
  91bd721 "Ajusta classificação de renovação de licença"
  44c8a1  "Adiciona definição de serviços de licenciamento"

arquivos:
  src/services/classifier.py
  src/services/scoring.py
  src/models/service_definition.py

seeds:
  Classifier.match
  ServiceDefinition
```

### 10.3 Fallback explícito

Se nenhum seed for encontrado:

```text
error: no seed found for prompt
  tried: symbol/file match, git-history match
  rerun with --seed <symbol-or-file>
```

A recusa explícita é preferível a um pacote ruim.

---

## 11. Graph Expansion

### O que o grafo realmente oferece hoje

Verificado em `src/seh/indexer.py`, não suposto a partir do enum:

| aresta | emitida | onde |
|---|---|---|
| `contains` | sim | `indexer.py:116` — repo → arquivo |
| `declares` | sim | `indexer.py:129,153` — arquivo → módulo, dono → símbolo |
| `imports` | sim | `indexer.py:176` — arquivo → alvo |
| `extends` | sim | `indexer.py:191` — classe → base |
| `calls` | **não** | membro de `EdgeKind`, zero emissões |
| `tests` | **não** | membro de `EdgeKind`, zero emissões |

`EdgeKind.CALLS` e `EdgeKind.TESTS` existem como vocabulário declarado e **nada os
produz**. `python_adapter.py` não trata `ast.Call`.

A v0.1 e a v0.2 leram o enum e concluíram que a capacidade existia. É o mesmo modo
de falha que o `CAPABILITY_MODEL.md` já registra: *a documented primitive with no
implementation and no proof is worse than an absent one.*

Planejar expansão por callers/callees é planejar **construir um grafo de chamadas
Python** — dispatch dinâmico, ausência de tipos, `getattr`, decorators. É o problema
difícil desta área, e a razão pela qual ferramentas equivalentes se apoiam em
language server. Não cabe como item de checklist dentro de outra fase.

### Expansão do MVP: só o que existe, mais referência de nome

A partir de cada seed:

- **1 hop estrutural** pelas arestas reais: `declares`, `contains`, `imports`, `extends`.
- **Referência de nome:** arquivos rastreados que mencionam o nome de um símbolo já
  selecionado. Determinístico e barato, porque o índice já guarda os nomes.
- **Testes:** arquivos classificados como `NodeKind.TEST` (`indexer.py:114`) que
  mencionam o nome do símbolo.
- Parar ao atingir o limite de símbolos (padrão: 20).

Referência de nome **não é** chamada resolvida: perde dispatch dinâmico e sobra em
colisão de nome. O `included_because` diz exatamente isso —
`name reference, not a resolved call` — para que nenhum consumidor, humano ou
modelo, leia mais do que o dado sustenta.

### Diferido para fase própria

Grafo de chamadas real, com resolução de atributo e de herança. Só depois de a
Fase 0 mostrar que contexto entregue vence exploração adaptativa. Construir o
grafo primeiro seria pagar o item mais caro antes de saber se o produto tem valor.

---

## 12. Representation Selection

Heurística simples:

- Símbolo alvo (`seed`) → `source` completo.
- Símbolos 1-hop → `source` se pequeno (< 50 linhas), senão `summary`.
- Símbolos 2-hop → `summary`.
- Testes → `source` se pequeno, senão `summary`.

---

## 13. Proveniência e staleness

O `context.md` carrega:

```yaml
provenance:
  repository_root: /path/to/repo
  commit: a91fc31d...
  tree: 7b3e9a...
  generated_at: "2026-08-12T14:30:00Z"
  schema_version: "seh.context/v0.1"
```

Se o agente tentar usar o pacote com uma árvore diferente, a ferramenta de consumo deve recusar. O SEH já sabe fazer isso — é o mesmo mecanismo de fingerprint do `seh index`.

---

## 14. Métricas

### Métrica principal

**Exploration Operations Saved**

```text
tool calls until first correct edit

Agent + raw repo access     : X
Agent + SEH context package : Y

saved = X - Y
```

Medida em sessões instrumentadas. O veredito é essa diferença.

### Métricas diagnósticas

- **Context Recall:** |relevant ∩ generated| / |relevant|
- **Context Precision:** |relevant ∩ generated| / |generated|
- **Context Package Size:** tokens estimados do `context.md`.
- **Seed Hit Rate:** fração de tarefas onde o Seed Resolver encontrou ao menos um seed sem `--seed`.
- **Index Refresh Time:** tempo para atualizar o grafo após mudanças.

Recall e precision não decidem; explicam por que a principal está onde está.

---

## 15. Benchmark honesto

### Gabarito via commits resolvidos

Não definimos `relevant_symbols` manualmente. Usamos commits reais de bug-fix:

- prompt = **paráfrase** da mensagem do commit, nunca a mensagem literal;
- `relevant_files` = arquivos tocados pelo commit;
- `relevant_symbols` = símbolos daqueles arquivos modificados pelo diff — factível,
  porque `Node.line` existe no índice.

Isso elimina o viés de quem constrói o sistema.

### O vazamento que este gabarito cria, e os dois controles obrigatórios

O mecanismo principal do Seed Resolver (§10.2) casa termos do prompt contra
mensagens de commit. Se o prompt **for** a mensagem do commit-alvo, o resolver casa
com o próprio alvo e extrai dele os arquivos — que são o gabarito. `seed_hit` e
`recall` mediriam o resolver encontrando a chave da resposta, e mediriam alto.

É o mesmo vazamento que queimou `t1-uninstall` no probe da fase anterior: dois
agentes resolveram a tarefa e a solução ficou registrada no próprio experimento.

1. **Índice truncado.** O índice termo → commits é construído apenas com commits
   **anteriores** ao alvo. O commit-alvo e todos os posteriores ficam fora. Sem
   isso, o resolver está lendo o futuro.
2. **Prompt parafraseado.** A mensagem literal não é usada, para que o casamento
   não seja idêntico por construção. A paráfrase é escrita sem olhar o diff, e
   registrada junto com o resultado para poder ser auditada.

Sem os dois controles, o número não significa nada e não deve ser publicado.

### Execução

```bash
seh compile <prompt> --output ./tmp
cat ./tmp/context.md
```

### Avaliação

```python
recall = len(relevant_symbols & generated_symbols) / len(relevant_symbols)
precision = len(relevant_symbols & generated_symbols) / len(generated_symbols)
seed_hit = len(generated_seeds) > 0
```

### Meta inicial MVP

- seed_hit >= 0.60
- recall >= 0.60
- precision >= 0.50

Números arbitrários, usados apenas para detectar regressão. O benchmark real dirá se são razoáveis.

---

## 16. Roadmap

### Fase 0 — Experimento manual (1 dia)

Antes de escrever `seh compile`, responder a pergunta estrutural:

> Um pacote de contexto feito à mão, com seed perfeito escolhido por um humano, reduz tool calls em relação ao agente usando apenas a documentação existente?

Passos:

1. Escolher uma tarefa real num repositório de trabalho com histórico suficiente — o da varredura de campo serve, e os controles de vazamento do §15 se aplicam aqui também: árvore no commit anterior ao alvo, para que o agente não possa ler a resposta.
2. Montar `context.md` manualmente.
3. Rodar duas sessões frias:
   - Sessão A: agente com prompt + acesso raw ao repo.
   - Sessão B: agente com prompt + `context.md` anexado.
4. Medir tool calls até a primeira edição correta.

**Se B não vencer A claramente, o projeto morre aqui sem código.**  
**Se B vencer, sabemos o teto e podemos decidir quanto automatizar.**

### Fase 1 — Seed Resolver e Context Compiler (2–4 semanas)

- [ ] Índice de mensagens de commit → arquivos, **truncável por commit-alvo** (§15).
- [ ] Seed Resolver (symbol/file + git-history).
- [ ] Graph Expander pelas arestas existentes + referência de nome (§11).
- [ ] Renderer Markdown.
- [ ] Proveniência no pacote.
- [ ] Benchmark com 20 commits resolvidos, com os dois controles de vazamento.

Fora desta fase, e explicitamente: grafo de chamadas Python (§11).

### Fase 2 — Refinamentos (4–6 semanas)

- [ ] Ranqueamento melhor de commits por termos do prompt.
- [ ] Inclusão de testes relacionados.
- [ ] Ajuste do Representation Selector.
- [ ] Expansão semântica mínima via docstrings.

### Fase 3 — Integração (4–8 semanas)

- [ ] MCP server simples.
- [ ] Adapter leve para um agente.
- [ ] Medição de exploração evitada em sessões reais.

---

## 17. Riscos e objeções

### Risco 1: O agente já é adaptativo

O agente faz grep, lê, e decide o próximo grep sabendo mais. Um pacote pré-compilado é um chute único. Não sabemos se um chute bom é melhor que muitos chutes adaptativos.

**Mitigação:** Fase 0 testa isso antes de qualquer código.

### Risco 2: Histórico Git pode ser ruído

Mensagens de commit genéricas, squash merges, commits em inglês misturados com português.

**Mitigação:** O Seed Resolver reporta `seed source` para cada seed; o desenvolvedor inspeciona e decide.

### Risco 3: Benchmark via commits resolvidos é limitado

Commits futuros podem não ser representativos. Mas são melhores que gabarito do autor.

**Mitigação:** Coletar commits de múltiplos repositórios; reportar limitação.

### Risco 4: Concorrência madura

Aider, Cursor, Copilot, Cody já fazem context intelligence.

**Mitigação:** Diferenciação não é ter grafo, é **explicabilidade + proveniência + local-first + medição honesta**.

---

## 18. Diferenciação

1. **Explicabilidade:** cada símbolo diz por que foi incluído.
2. **Proveniência:** o pacote sabe de qual commit/tree veio e recusa ficar stale.
3. **Local-first:** o repositório inteiro não precisa sair da máquina.
4. **Métrica honesta:** tool calls até primeira edição correta, não "tokens economizados".
5. **Seed via histórico Git:** usa a linguagem de domínio já escrita pelos desenvolvedores.

---

## 19. Princípios mantidos do SEH original

1. **Code before tokens.** Determinístico primeiro.
2. **Local before frontier.** Análise local barata antes de chamada remota.
3. **Evidence over conversation.** O artefato é `context.md`, não chat.
4. **Model agnostic.** Output é Markdown; adapters são camadas finas.
5. **Provenance or refusal.** Pacote ancorado ou explícito fracasso.

---

## 20. Decisões de não-fazer (no MVP)

- Não usaremos LLM para interpretar a task.
- Não usaremos embeddings como mecanismo principal.
- Não faremos edição de código.
- Não faremos capabilities ou primitivas de splice.
- Não tentaremos provar economia de tokens antes de provar redução de exploração.
- Não construiremos adapters multi-provider antes de validar o consumo.

---

## 21. North Star

> **O coding agent deve começar a raciocinar no momento em que o contexto relevante já está organizado à sua frente, ancorado na árvore correta do repositório.**

A unidade de valor deixa de ser a *edição reutilizável* e passa a ser o *conhecimento do repositório entregue no formato certo, com origem verificável*.
