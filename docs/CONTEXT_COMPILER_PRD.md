# PRD — SEH Context Compiler v0.3

**Status:** Draft  
**Versão:** 0.3  
**Base:** Software Engineering Harness (SEH) v0.1.0a3  
**Tipo:** pivot de produto  
**Última revisão:** após o resultado da Fase 0

> **Leitura em linguagem simples:** [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md) conta o mesmo produto
> como cenário de uso, sem nenhum termo deste documento, e traz um decoder do vocabulário. Comece
> por lá se estiver voltando ao projeto depois de um tempo.

### O que mudou da v0.2 para a v0.3

1. **§2 foi refeito.** A Fase 0 rodou. "Descoberta é cara" saiu de *suspeitado* para *medido*, com
   o teto quantificado, e o §2 estava dizendo o contrário.
2. **§22 é novo:** registros de caminho. O corpus do Seed Resolver deixa de ser o histórico Git
   bruto e passa a ser um conjunto de registros compilados a partir de trabalho aceito. É a
   hipótese de reforço, na forma barata.
3. **§16 ganhou a Fase 0.5**, que mede se registros têm oportunidade suficiente para existir. A
   Fase 1 fica condicionada a ela.

O §2 continua sendo onde `README.md` e `ROADMAP.md` apontam para o resultado negativo de campo, e
esse trecho não mudou de lugar.

---

## 1. Visão curta

O SEH deixa de ser um sistema de *capabilities* reutilizáveis e passa a ser um **compilador de contexto** para coding agents.

Objetivo: receber um prompt humano, geralmente em português e na linguagem de domínio do desenvolvedor, e entregar um **pacote de contexto estruturado, pequeno e ancorado na árvore Git**, usando apenas computação determinística local.

O LLM recebe o pacote e parte direto para raciocinar, sem redescobrir o repositório.

> **O LLM não deve redescobrir o repositório. Ele deve raciocinar sobre o que o repositório já revela.**

---

## 2. O que foi medido, e o que continua em aberto

As duas coisas ficam separadas de propósito. A v0.1 desta seção as juntou, e o resultado leu mais forte do que a evidência sustentava. A v0.3 mantém a separação com uma mudança: o bloco que era "suspeitado" virou medido, e o que ocupa o lugar dele agora é outra pergunta.

### Medido, e o sinal é negativo

**Reuso de edição não se paga na frequência observada.**

Uma varredura de campo num repositório em produção — 654 commits, 15 meses, 5 autores — encontrou um procedimento genuíno de "adicionar mais um módulo com entrada em registry central". Ele recorreu **3 vezes em 5 meses, entre 2 autores diferentes**, e a recorrência foi *encontrada*, não fabricada. O wiring mecânico é de **4 linhas em 1242 inserções**, e os três primitivos que ele exigiria (`file.render`, `python.import_block`, `splice.into_collection`) não existem no SEH. Implementá-los com a disciplina dos quatro gates é trabalho de dias. Break-even: **anos**.

O POC anterior chegou ao mesmo lugar por outro eixo — ~15 min de autoria contra ~60s por repetição manual, break-even em 15–30 repetições — mas sobre um projeto de brinquedo cujos comandos eram `print(nome)`. O número de campo é o que vale, e é pior.

Este é o resultado mais sólido que o projeto produziu, e é negativo. É o que justifica abandonar o produto anterior.

### Medido, e o sinal é positivo

**Descoberta é cara, e o pacote de contexto compra o caminho até a solução.**

A Fase 0 (§16) rodou com pré-registro comitado antes da primeira sessão. Seis sessões frias, três por arm, numa tarefa real de localização entre camadas, em repositório bem documentado.

| métrica | mediana A | mediana B | B/A |
|---|---|---|---|
| tool_uses | 52 | 16 | **30,8%** |
| tokens | 146.332 | 65.126 | 44,5% |
| segundos | 521 | 166 | 31,9% |

Limiar pré-registrado `≤ 50%`: satisfeito. Piso — nenhuma repetição de B pior que a mediana de A: satisfeito. Oráculo de localização 6/6, não-regressão 6/6.

O achado qualitativo vale mais que a razão: **os seis agentes convergiram para a mesma solução.** O pacote não comprou *correção*, comprou o **caminho até ela** — que é exatamente o que o §3 alega, e agora tem medição em vez de argumento.

Três limites, declarados no próprio resultado e não negociáveis ao citá-lo: o `context.md` foi montado à mão por quem formulou a hipótese, então **isto é o teto, não o produto**; o oráculo é localização, não correção; e é uma tarefa, um repositório, `R = 3` — probe, não benchmark.

Registro completo em [`../experiments/fase0/RESULT.md`](../experiments/fase0/RESULT.md). O probe anterior, contaminado nas três formas que `PROBE_FINDINGS.md` declara, foi substituído por este e não deve mais ser citado.

### Não medido, e é onde o produto ainda morre

Duas perguntas em aberto, em ordem de custo para responder.

**1. Recorrência de região — uma tarde.** O teto acima pressupõe que exista de onde tirar o seed. O resultado negativo mediu *identidade de procedimento* e a achou rara; um registro de caminho (§22) precisa de algo mais fraco — que a mudança nova caia numa região que alguma mudança anterior já visitou. Esse eixo nunca foi medido, e o número que matou as capabilities **não transfere** para ele. Fase 0.5, com limiares já fixados em [`../experiments/region_recurrence/README.md`](../experiments/region_recurrence/README.md).

**2. Recuperação — 2 a 4 semanas.** Achar o registro certo a partir do prompt é o Seed Resolver (§10), e ele foi contornado de propósito na Fase 0. O teto é 30,8%; quanto disso um mecanismo determinístico captura é a Fase 1.

### A regra que sobrevive às três

O erro do produto anterior não foi escolher a hipótese errada. Foi construir semanas antes de testá-la. A Fase 0 custou um dia e devolveu um teto; a Fase 0.5 custa uma tarde. Nenhuma das duas exigiu código de produto, e essa é a ordem a manter.

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

Dois fluxos, e o de cima é o que a v0.3 acrescenta.

```text
        ┌─────────── acumulação, sem inferência (§22) ───────────┐
        │                                                        │
   commit aceito ──► compilador de registro ──► .seh-records/    │
        │            (diff → arquivos → símbolos)                │
        └────────────────────────────┬───────────────────────────┘
                                     │  corpus
                                     ▼
Developer Prompt
       │
       ▼
┌──────────────────────────┐
│  Seed Resolver           │
│  ├── symbol/file match   │
│  ├── record match        │  ← mecanismo principal na v0.3
│  └── git-history match   │  ← fallback, era o principal na v0.2
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

- `seh.records.compiler` → commit aceito → registro de caminho (§22). Sem inferência.
- `seh.context.seed_resolver` → symbol/file match + record match + git-history match.
- `seh.context.expander` → BFS limitada no grafo.
- `seh.context.renderer` → Markdown estruturado.
- `seh compile` → novo comando CLI.
- `seh record` → compila o registro do commit aceito; idempotente, chamável de hook.

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

> **Revisão da v0.3.** O corpus deste componente muda. A v0.2 casava o prompt contra 654 mensagens
> de commit brutas; a v0.3 casa primeiro contra os registros de caminho do §22, que já declaram sua
> região como fato do diff e vêm rotulados em linguagem de domínio. O §10.2 abaixo continua válido
> e vira o **fallback** para o período em que o repositório ainda não acumulou registros —
> inclusive o primeiro dia, quando não há nenhum.
>
> O mecanismo não fica mais fácil por decreto: casar português com português continua sendo
> matching lexical sobre texto curto. O que melhora é o material — menos entradas, cada uma com
> região declarada em vez de inferida por "arquivos daquele commit".

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

O seed é escolhido a mão **de propósito**. Isso remove o Seed Resolver — o componente mais fraco e mais caro do PRD — do experimento, e o que sobra é o **melhor caso que o produto poderia alcançar**. Se o teto não compensa, nenhuma engenharia no resolver salva, porque o resolver só pode se aproximar desse teto, nunca ultrapassá-lo.

#### Pré-registro

Tudo nesta subseção é fixado **antes** da primeira sessão. Um valor que mude depois invalida o experimento em vez de emendá-lo. É a mesma disciplina de `experiments/m2_pilot/manifest.yaml`, e existe pela mesma razão: depois do fato, um critério ajustado é indistinguível de um critério medido.

#### Montagem

1. Escolher um **commit-alvo resolvido** num repositório de trabalho com histórico suficiente. Preferir um que tenha adicionado ou alterado testes — a razão está no oráculo.
2. Árvore no commit **anterior** ao alvo. O agente não pode alcançar o alvo nem nada posterior a ele: é o controle de vazamento do §15, e é assim que o probe da fase anterior se estragou.
3. Prompt = **paráfrase** da mensagem do commit, escrita sem olhar o diff.
4. Montar `context.md` a mão, com o seed que um humano sabe estar certo.
5. Fixar o escopo: a tarefa é a mudança que o commit-alvo fez, e nada além. Refatoração adjacente não solicitada é registrada e **exclui a repetição** — no probe anterior um arm refatorou outro módulo de brinde, +97 linhas, e o delta virou mistura de dois efeitos.

#### Arms e repetições

| arm | tratamento |
|---|---|
| A | prompt + acesso raw ao repositório, com toda a documentação que ele já tem |
| B | prompt + `context.md` anexado, mesmo acesso raw |

`R = 3` sessões frias por arm, seis no total. A repetição não mede variância de tarefa — a tarefa é a mesma — e sim **não-determinismo do modelo**, que foi a fraqueza declarada do probe anterior (`n = 1` por arm, sem controle algum).

#### O oráculo: localização, não correção comportamental

Executável, e decidido antes de rodar. Nenhum humano e nenhum modelo julga.

**A edição conta quando seu caminho está no conjunto de arquivos-fonte que o commit-alvo modificou.** Esse conjunto é fato histórico, não escolha de autor. Somado a uma condição de não-regressão: a suíte pré-existente continua passando depois da sessão.

Isto é uma **revisão**, e a razão está registrada porque contradiz o que esta seção dizia antes. O oráculo original eram os testes do próprio commit-alvo, aplicados após a sessão. Uma filtragem mecânica de 12 candidatos reais mostrou que ele não é praticável:

| resultado | quantos |
|---|---|
| os testes do alvo falham na árvore pai (oráculo válido) | 6 |
| **passam na árvore pai** — não discriminam | 6 |

Metade dos testes de regressão reais **passa antes do fix**. E entre os que discriminam, os inspecionados falharam por motivos distintos: um exigia tags editoriais (`"holerite"`, `"contra check"`) que nenhum prompt transmite e nenhum agente adivinha; outro cobria apenas um módulo novo e autocontido, onde descoberta importa menos.

A tensão de fundo é estrutural, e vale mais que o oráculo descartado: **as tarefas que melhor testam a hipótese de descoberta são as que atravessam muitas camadas, e atravessar camadas significa tocar superfícies editoriais.** Seus oráculos codificam escolhas arbitrárias. Já as tarefas com oráculo limpo são módulos novos autocontidos — exatamente onde localizar é fácil.

Localização resolve isso porque é o que a hipótese realmente afirma. O PRD não alega que o pacote de contexto faz o modelo implementar melhor; alega que ele gasta menos exploração **antes de chegar ao lugar certo**. Correção comportamental é outro eixo, e conflacionar os dois foi o que tornou a seleção impraticável.

O que se perde está declarado: o experimento não verifica que a mudança está correta. Um agente que edite o arquivo certo com conteúdo errado marca ponto. Isso é aceitável na Fase 0 e não seria numa fase de qualidade.

#### A métrica

**Tool calls até a primeira edição no lugar certo.** Conta toda invocação de ferramenta — leitura, busca, listagem, shell, edição — do início da sessão até a edição que satisfaz o oráculo, **incluindo edições em arquivos fora do conjunto declarado**. Editar o arquivo errado é custo real e conta.

Registrados mas não decisórios: arquivos distintos lidos, cobertura do conjunto declarado ao final da sessão, tokens, tempo de parede.

#### O limiar, fixado agora

"Vencer claramente" precisa de número, senão é lido depois do resultado.

| mediana de B ÷ mediana de A | leitura |
|---|---|
| **≤ 50%** | vence. Segue para a Fase 1, sabendo o teto |
| 50%–90% | inconclusivo. O ganho não paga 2–4 semanas *no melhor caso possível*; ou se amplia a amostra, ou se para |
| **> 90%** | morto. O projeto termina aqui, sem código |

Além da mediana, uma condição de piso: **nenhuma repetição de B pode ser pior que a mediana de A.** Um ganho que só aparece na média, com sessões piores no meio, não é o efeito que o produto promete.

O corte em 50% não é arbitrário: é aproximadamente o que a prosa contaminada já entregou no probe anterior (54 → 27 tool calls). Um pacote com seed perfeito, montado a mão, precisa bater isso para justificar construir o resolver.

**Se B não vencer, o projeto morre aqui sem uma linha de código.**  
**Se B vencer, o número é o teto — e quanto automatizar passa a ser decisão econômica em vez de fé.**

#### Resultado: **B venceu**, `B/A = 30,8%`

Fechada. Números, cobertura, e os **dois desvios declarados** — a métrica pré-registrada não foi
medível como especificada, e os hooks do harness inflam a contagem em modo comum — estão em
[`../experiments/fase0/RESULT.md`](../experiments/fase0/RESULT.md). O §2 resume; o RESULT decide.

A lição transferível do desvio vale para toda fase seguinte: **se for medir agentes, não peça que
eles se contem.** A telemetria do harness subnotificou até 44% num arm e 0% em outro — viés
diferencial, na direção que favoreceria o resultado desejado.

### Fase 0.5 — Recorrência de região (uma tarde)

Nova na v0.3, e vem **antes** da Fase 1 porque decide se a Fase 1 tem do que se alimentar.

A Fase 0 estabeleceu o teto de **valor** com seed perfeito montado à mão. Falta o teto de
**frequência**: com que frequência a oportunidade sequer existe, ou seja, quantas mudanças caem em
região que alguma mudança anterior já visitou (§22).

Pré-registro completo, com limiares, cooldown decisório, nulls e vieses de direção declarada:
[`../experiments/region_recurrence/README.md`](../experiments/region_recurrence/README.md).

```bash
python experiments/region_recurrence/measure.py \
  --repo /caminho/do/repo-de-campo --cooldown-days 30 --json resultado.json
```

Os três desfechos possíveis já estão escritos, e um deles **não** é a Fase 1:

| desfecho | consequência |
|---|---|
| recorrência frequente, e vence o null de arquivos quentes | funda a Fase 1 abaixo |
| recorrência frequente, mas **não** vence o null | o produto é uma lista estática de arquivos quentes, custa uma tarde, e a Fase 1 é cancelada |
| recorrência rara | registros não pagam. Mesmo veredito das capabilities, e pelo mesmo motivo |

### Fase 1 — Seed Resolver e Context Compiler (2–4 semanas)

**Condicionada à Fase 0.5.** Não iniciar antes do número.

- [ ] `seh record` — compilador de registro de caminho (§22), sem inferência no caminho.
- [ ] Índice de registros → região, **truncável por commit-alvo** (§15).
- [ ] Índice de mensagens de commit → arquivos, mesma truncabilidade — fallback do §10.2 para
      repositório sem registros acumulados.
- [ ] Seed Resolver (symbol/file + record match + git-history).
- [ ] Graph Expander pelas arestas existentes + referência de nome (§11).
- [ ] Renderer Markdown.
- [ ] Proveniência no pacote e no registro.
- [ ] Benchmark com 20 commits resolvidos, com os dois controles de vazamento.

Fora desta fase, e explicitamente: grafo de chamadas Python (§11).

#### O limiar da Fase 1, fixado agora

Fixado aqui pelo mesmo motivo que o da Fase 0: depois do fato, um critério ajustado é
indistinguível de um critério medido.

A Fase 0 entregou `B/A = 30,8%` com seed humano. A Fase 1 roda **a mesma tarefa, o mesmo oráculo de
localização, a mesma telemetria**, trocando o `context.md` montado à mão pelo pacote que o
`seh compile` gerar sozinho, sem `--seed`.

| fração do teto capturada | leitura |
|---|---|
| **`B'/A ≤ 50%`** | vence. O resolver captura o essencial; segue para a Fase 2 |
| `50% < B'/A ≤ 75%` | inconclusivo. Reavaliar contra a lista estática de arquivos quentes, que é muito mais barata |
| **`B'/A > 75%`** | o resolver não recupera o teto. O produto é o `context.md` manual como convenção de time, não uma ferramenta |

Piso, herdado da Fase 0: nenhuma repetição de B′ pior que a mediana de A. `R = 3` no mínimo.

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

### Risco 1: O agente já é adaptativo — **resolvido, a favor**

O agente faz grep, lê, e decide o próximo grep sabendo mais. Um pacote pré-compilado é um chute único. Não sabíamos se um chute bom é melhor que muitos chutes adaptativos.

**Resultado:** é. Na Fase 0, o chute único bom venceu a exploração adaptativa por ~3× em tool calls, e os dois arms chegaram na mesma solução.

**O que continua valendo do risco:** o chute foi *humano e perfeito*. O risco não some, migra — vira o Risco 5.

### Risco 5: O chute automático pode não ser bom

O que a Fase 0 mostrou é que um seed certo compensa. Um seed **errado** entregue com a mesma confiança é pior que nenhum, porque o agente começa convicto no lugar errado.

**Mitigação:** as três contenções do §22.6, e o limiar da Fase 1 fixado no §16 — que inclui um desfecho em que o produto é cancelado em favor de uma lista estática de arquivos quentes.

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

---

## 22. Registros de caminho

Novo na v0.3. É a hipótese de reforço — o repositório aprende com a própria manutenção — na única
forma que a medição de campo permite.

### 22.1 O que é

Um **registro de caminho** é a anotação de que um trabalho aceito tocou uma região do repositório:
quais arquivos, quais símbolos, sob qual rótulo em linguagem de domínio, ancorado em qual commit.

O que ele **não** é: uma receita. A versão anterior do projeto tentava guardar como a mudança foi
feita e falhou economicamente (§2). Um registro guarda apenas **onde**.

### 22.2 Por que "onde" paga e "como" não

A distinção é a razão de a v0.3 existir, e é medível:

| | capability (morta) | registro de caminho |
|---|---|---|
| condição de reuso | **identidade de procedimento** — o mesmo wiring recorre | **sobreposição de região** — a mudança nova cai perto |
| frequência observada | 3 eventos em 5 meses | não medido → Fase 0.5 |
| custo de autoria | dias: 4 gates, primitivos, fixtures, aprovação | uma travessia de diff |
| quem escreve | agente propõe, desenvolvedor confirma | ninguém — é compilado |

O número que matou as capabilities mediu a primeira linha. **Ele não transfere para a segunda**, e
supor que transfere seria o mesmo erro do §11: ler uma medida de um eixo e concluir sobre outro.

### 22.3 Compilado, não escrito

Nenhum LLM no caminho de autoria, nenhum passo de confirmação, nenhum custo por unidade aprendida.
O registro é uma projeção determinística de algo que o Git já guardou:

1. **arquivos** — `git diff --name-only` do commit aceito;
2. **símbolos** — linhas do diff atribuídas a declarações do índice;
3. **rótulo** — o assunto do commit, que já está em linguagem de domínio (§5).

Isso é o que torna o loop de reforço viável. Uma capability custava dias por unidade; um registro
custa uma travessia de diff. Se a Fase 0.5 mostrar oportunidade, o payback não depende de o
desenvolvedor lembrar de nada.

#### A limitação que o índice impõe hoje, verificada e não suposta

`Node.line` (`models.py:32`) guarda a **linha inicial** da declaração. `python_adapter.py` lê
`statement.lineno` e **não** captura `end_lineno`, embora o `ast` o ofereça desde a 3.8.

Consequência: atribuir uma linha do diff a um símbolo só pode ser feito por **declaração
imediatamente anterior**, e isso erra em dois casos reais — mudança em código de nível de módulo
depois da última função, e mudança em decorator antes da declaração seguinte.

Duas saídas, e a primeira é barata: capturar `end_lineno` no adapter, um campo, e a atribuição
passa a ser exata por contenção de span. Fica como item da Fase 1. Enquanto não existir, o registro
declara `attribution: nearest_preceding` e o `included_because` diz isso ao consumidor, pelo mesmo
motivo que o §11 faz com referência de nome: **nenhum consumidor deve ler mais do que o dado
sustenta.**

### 22.4 Formato

`.seh-records/<commit-curto>.yaml`, versionado no Git — aprendizado é código e dado revisável e
removível num PR, invariante herdado do modelo anterior.

```yaml
schema: seh.record/v0.1
commit: 91bd721c4f...
tree: 7b3e9a2f...
subject: "Adiciona cupom de desconto no checkout"
recorded_at: "2026-01-14T10:22:00Z"
attribution: nearest_preceding
region:
  - path: api/checkout/pricing.py
    symbols: [apply_discounts]
    lines_changed: 34
  - path: api/promotions/models.py
    symbols: [Coupon, CouponRule]
    lines_changed: 121
  - path: tests/test_pricing.py
    symbols: [test_discount_applied]
    lines_changed: 32
```

Identificadores sintéticos, como no §9.

### 22.5 O loop

```text
merge  ──►  seh record  ──►  .seh-records/91bd721c.yaml
                                      │
prompt ──►  seh compile  ◄────────────┘
                │
                ▼
          context.md (§9)
```

`seh record` é idempotente e chamável de hook. Um registro nunca é sobrescrito: um commit é fato
histórico, e reescrevê-lo repetiria o defeito que o `PHASE0_FINDINGS.md` registra em
*"capture must preserve the true before-state"*.

### 22.6 Os dois modos de falha, e as contenções

**Registro errado recuperado com confiança.** É o risco que o M5 do roadmap antigo já nomeia para o
catálogo de capabilities, e aqui é pior: um seed errado é pior que nenhum seed, porque o agente
começa convicto no lugar errado. Três contenções, todas já presentes em forma no projeto:

1. **O pacote nunca substitui o repositório.** O Arm B da Fase 0 tinha `context.md` **mais** acesso
   raw, e foi *isso* que mediu 30,8%. Nenhuma versão do produto pode fechar o acesso ao código.
2. **`Unknowns` (§9) é obrigatório**, não decorativo. Termo do prompt que não casou é impresso.
3. **Cada registro carrega o quanto historicamente acertou.** O pacote diz o quanto confiar, em vez
   de apresentar tudo com o mesmo peso.

**Apodrecimento silencioso.** A proveniência (§13) resolve o caso duro — arquivo sumiu, árvore
mudou, falha alto. Ela não pega o caso mole: o arquivo existe, mas a convenção mudou. Contenção
barata: registro cuja região não é tocada há N meses é **rebaixado, não apagado**. A versão cara é
health check em CI, e não deve ser construída antes de rot ser observado.

### 22.7 O que este design pressupõe, e que ainda não foi medido

Declarado aqui para que nenhuma seção posterior o trate como estabelecido:

- **que a oportunidade existe** — Fase 0.5, não rodada;
- **que a recuperação funciona** — Fase 1, não rodada. O máximo sobre todos os registros é um
  oráculo; achar o registro certo a partir do prompt é outro problema;
- **que sobreposição de região implica sobreposição de conhecimento.** Dois commits podem tocar o
  mesmo arquivo por razões sem relação. É a mesma limitação que o oráculo de localização da Fase 0
  declarou: mede o lugar, não o conteúdo.

Se a Fase 0.5 voltar negativa, esta seção inteira é retida como registro de design e não é
implementada — mesmo tratamento que o `CAPABILITY_MODEL.md` recebeu.
