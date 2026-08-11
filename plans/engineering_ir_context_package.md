# M1.1 — Engineering IR e Context Package v0.1 (Python / `ast`)

## Resumo

Entregar a primeira fatia vertical do M1: um agente descreve uma tarefa em JSON, o SEH valida o Engineering IR e compila um pacote determinístico, limitado por orçamento e contendo trechos de código relacionados aos símbolos-alvo. O incremento será publicado como `0.2.0a1` e documentado em `docs/product/engineering-context-v0.1.md`.

Esta versão substitui o paradigma Java/Tree-sitter do plano original pelo paradigma decidido para o v1 do SEH: **Python puro, indexado com o módulo `ast` da stdlib, zero dependência externa**. O SEH deixa de depender de qualquer indexador de terceiros e passa a ser instalável em um comando, sem processo externo — o adaptador Java do PR #1 fica congelado como referência de arquitetura (proveniência, fingerprint, schema versionado), sem receber novas features nesta fase.

## Contratos públicos

- Adicionar `seh task validate TASK`, aceitando arquivo ou `-` para stdin e emitindo o IR normalizado como JSON canônico.
- Adicionar `seh context build TASK [--output PATH] [--repo PATH]`; sem `--output`, o pacote vai para stdout; com arquivo, a escrita é atômica e stdout permanece vazio.
- Definir `seh.task/v0.1` em JSON Schema 2020-12, sem propriedades desconhecidas:
  - `id`: identificador de 1–64 caracteres `[A-Za-z0-9._-]`;
  - `objective`: texto não vazio;
  - `targets`: lista não vazia e sem duplicatas de `{node_id}`;
  - `budget.max_context_tokens`: inteiro positivo obrigatório;
  - `selection.neighbor_depth`: `0` ou `1`, default `1`;
  - `selection.include_tests`: default `true`;
  - `constraints` e `verification_requirements`: listas de textos, default vazio, apenas declarativas nesta versão.
- Definir `seh.context/v0.1` com tarefa normalizada, `HEAD`/fingerprint, estimador e budget, alvos, itens selecionados, relações/razões de inclusão, conteúdo com spans e hashes, total estimado e diagnósticos de itens omitidos.
- JSON canônico usará UTF-8, `sort_keys`, indentação de dois espaços e newline final; não conterá timestamp nem caminho absoluto, garantindo bytes idênticos para mesma tarefa e fingerprint.
- Erros de schema, alvo inexistente, índice obsoleto, mudança concorrente ou estouro obrigatório retornam `2` e mensagem em stderr.

## Implementação

### Adaptador Python (`src/seh/python_adapter.py`, novo)

- Usar `ast.parse` da stdlib — sem dependência de pacote externo. `ast.NodeVisitor`/`ast.walk` sobre `ClassDef`, `FunctionDef`, `AsyncFunctionDef`, `Import`, `ImportFrom`.
- Aproveitar que o `ast` já expõe `lineno`/`end_lineno`/`col_offset`/`end_col_offset` nativamente (Python ≥3.8) — dispensa a lógica de span manual que o Tree-sitter exigia no adaptador Java.
- **Qualified name**: resolver o nome de módulo pontuado seguindo a mesma regra que o `import` do Python usa — subir diretórios enquanto existir `__init__.py`, formando `pkg.subpkg.module`. Para este repositório (`src/seh/*.py`, com `src/seh/__init__.py`), `src/seh/indexer.py` resolve para `seh.indexer`, consistente com os imports relativos já usados no código (`from .git import ...`).
- **Escopo de indexação**: apenas declarações em nível de módulo e de classe (incluindo classes aninhadas). Funções aninhadas dentro do corpo de outra função (closures locais) não são indexadas nesta versão — ver Premissas.
- **Header/preâmbulo**: para uma classe ou função decorada, o início do cabeçalho é `min(lineno do primeiro decorator, lineno do nó)`; o fim do cabeçalho é `body[0].lineno - 1` (a linha antes do primeiro statement do corpo, incluindo docstring como primeiro statement — mesma semântica de "declaração sem corpo completo" do plano original).
- **Import bindings por arquivo**:
  - `import a.b.c [as x]` → vincula `x` (ou `a`) a `a.b.c`;
  - `from a.b import c [as x]` → vincula `x` (ou `c`) a `a.b.c`, resolvendo depois se `c` é submódulo ou símbolo dentro de `a.b`;
  - `from . import x` / `from .foo import Bar` → resolver `level` (`ImportFrom.level`) contra o qualified name do próprio arquivo para obter o caminho absoluto antes de vincular;
  - `from a.b import *` → registrado como fonte wildcard, mesma semântica de prioridade mais baixa do plano original.
- Diagnóstico de erro de leitura/decodificação e de erro de sintaxe (equivalente a `read_error`/`syntax_error` do adaptador Java), sem interromper a indexação dos demais arquivos.

### Resolução de símbolos (`PySymbolCatalog`, substitui `TypeCatalog`)

Mesma forma — `by_qualified: dict[str, list[node_id]]` — com ordem de resolução adaptada à semântica de import do Python (sem "wildcard de classe" implícito como o Java tem via mesmo pacote; em Python tudo é explícito por `import`):

1. escopo aninhado (classe/função ancestral no mesmo arquivo);
2. binding de import direto do arquivo (`from x import Y` / `import x.Y`);
3. mesmo módulo (arquivo atual);
4. import wildcard (`from x import *`) do arquivo.

Resultado: `resolved` (exatamente um match), `ambiguous` (mais de um — nunca escolher silenciosamente), `unresolved` (nenhum, inclusive nomes de stdlib/terceiros — não gera aresta especulativa).

### Relações de grafo

- `EXTENDS` cobre toda herança Python (`class Foo(Base1, Base2):`) — o Python não distingue classe-base de interface, então a aresta `IMPLEMENTS` do schema não é emitida pelo adaptador Python (permanece definida no `models.py` por compatibilidade com o adaptador Java congelado, mas não utilizada).
- `IMPORTS` para bindings resolvidos internamente ao repositório; imports externos (stdlib/terceiros) não geram aresta, apenas são descartados silenciosamente na resolução (mesma regra do plano original: "referências externas ou ambíguas não criam arestas especulativas").
- `CONTAINS`/`DECLARES` seguem servindo só para localizar ancestrais na seleção, nunca para puxar todos os filhos de um tipo automaticamente.

### Schema, budget e seleção — inalterados na essência, adaptados nos termos

- Evoluir o grafo para schema v3, adicionando `end_line` e `header_end_line` inclusivos aos símbolos (igual ao plano original; a origem do dado muda de Tree-sitter para `ast`).
- Empacotar o JSON Schema no wheel e usar `jsonschema>=4.23,<5` para validação, aplicando defaults durante a normalização.
- Seleção determinística, adaptada aos termos Python:
  1. alvo completo;
  2. preâmbulo do arquivo (docstring de módulo + imports) e cabeçalhos das classes ancestrais;
  3. superclasses diretas (`EXTENDS`);
  4. imports internos diretos;
  5. dependentes diretos e testes conectados pelo grafo, com menor prioridade.
- Para métodos e funções, incluir preâmbulo, cabeçalho da classe proprietária (quando houver) e a função/método completo; para classes-alvo, incluir a classe completa; para arquivos-alvo e testes selecionados, incluir o arquivo completo.
- Mesclar spans sobrepostos, ordenar por prioridade, caminho, linha e ID, e nunca truncar código.
- Estimar tokens como `ceil(bytes_utf8 / 4)`, identificado por `utf8-bytes/4-v1`; o orçamento cobre somente os conteúdos-fonte.
- Se itens obrigatórios excederem o budget, falhar informando o mínimo necessário. Itens opcionais que não couberem serão omitidos e registrados no pacote.
- Validar fingerprint antes e depois da compilação para impedir pacotes formados durante uma alteração concorrente.

### Modelos e indexador

- `models.py`: adicionar `NodeKind.FUNCTION` (função de módulo, distinta de `METHOD`, que permanece para funções dentro de classe). `NodeKind.INTERFACE/ENUM/RECORD` e `EdgeKind.IMPLEMENTS` permanecem definidos (usados pelo adaptador Java congelado), mas não são emitidos pelo adaptador Python.
- `indexer.py`: o alvo de indexação passa a ser arquivos `.py` (não `.java`); a integração com `python_adapter.py` substitui a integração com `java_adapter.py` como caminho padrão. O adaptador Java permanece no repositório, mas fora do caminho de indexação padrão.

### Infra

- Adicionar CI para Python 3.11/3.12 com testes, cobertura de branches mínima de 90%, `compileall`, `pip check` e build de sdist/wheel (igual ao plano original — já cobre este repositório, que é 100% Python).
- Atualizar README, arquitetura e roadmap, marcando IR, validação, seleção por símbolo, estimativa e context package como concluídos; blast radius permanece pendente.

## Testes e aceitação

- Schema: campos obrigatórios, defaults, propriedades extras, IDs inválidos, targets duplicados e budgets inválidos.
- Spans: classes, classes aninhadas, funções e métodos (síncronos e `async def`), decorators, docstrings, e linhas inclusivas corretas via `end_lineno` nativo do `ast`.
- Resolução de import: `import a.b.c`, `from a.b import c`, alias (`as`), imports relativos (`from . import x`, `from ..pkg import y`), wildcard, e o caso de ambiguidade (dois símbolos de mesmo nome resolvidos por caminhos de import diferentes) retornando `ambiguous` em vez de escolher.
- Seleção: alvos, ancestrais, herança, imports, dependentes, testes relacionados, profundidade zero/um e ordenação estável.
- Budget: obrigatório acima do limite, inclusão opcional até o limite, omissões diagnosticadas e ausência de truncamento.
- CLI: arquivo/stdin, stdout, escrita atômica, códigos de saída, índice ausente/obsoleto e alvos inexistentes.
- Determinismo: golden test confirma pacote byte a byte idêntico; mudanças em tarefa ou fingerprint alteram o resultado.
- Executar testes focados após cada grupo e finalizar com suíte completa, cobertura ≥90%, build, `pip check` e `git diff --check`.

## Premissas e não objetivos

- O incremento continua local, **Python-first** (via `ast` da stdlib) e sem invocar modelos ou transmitir código.
- `constraints` e `verification_requirements` não serão executados; isso pertence ao M2.
- Não serão implementados análise de chamadas, arestas `TESTS` automáticas além da heurística de caminho já existente (`_is_test`), blast radius transitivo, tokenizer específico de modelo ou adapters de agentes.
- Funções aninhadas dentro do corpo de outra função (closures locais) não são indexadas — apenas declarações de módulo e de classe (incluindo classes aninhadas).
- "Teste relacionado" significa apenas um arquivo de teste conectado pelas relações estruturais atualmente disponíveis.
- Não se busca paridade de profundidade com Serena ou Aider (LSP completo, múltiplas linguagens) — o indexador Python é deliberadamente mínimo, a serviço da evidência e da seleção de contexto, não um produto de navegação de código.
- O adaptador Java (`java_adapter.py`, PR #1) não é removido nem estendido nesta fase; fica congelado no repositório, fora do caminho de indexação padrão.
- A pasta local não rastreada `.claude/` será preservada e excluída do incremento.
- A implementação partirá da `main` sincronizada; eventuais commits usarão mensagens em Pt-BR.
