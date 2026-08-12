# Experimento de utilidade do SEH — `poc-cli`

Este diretório contém um experimento end-to-end que replica o workflow proposto pelo SEH em um repositório Python-alvo separado.

**Objetivo:** verificar se a ideia de "capturar uma capability uma vez e reutilizá-la" se prova útil na prática, com números honestos.

---

## O cenário

Um CLI argparse (`src/poc_cli/main.py`) com um padrão recorrente: **adicionar um novo subcomando** envolve sempre as mesmas duas edições estruturais:

1. criar `def cmd_<name>(args: argparse.Namespace) -> int`;
2. registrar o comando no `build_parser()` com `subcommands.add_parser(...)`.

Isso é exatamente o tipo de mudança que o SEH chama de *capability*.

---

## O que foi feito

### 1. Cold path — implementação manual do primeiro comando

Estado inicial do `main.py`: comandos `add` e `list`.

A primeira ocorrência (`status`) foi implementada manualmente e commitada:

```bash
# tempo de edição manual: ~1 minuto (8 linhas de boilerplate)
git log --oneline
# 0d7610b feat: adiciona comando status
```

### 2. Capture e autoragem da capability

A partir do commit aceito, gerou-se o esqueleto da candidate:

```bash
seh capability capture \
  --id poc.add-cli-command \
  --baseline HEAD~1 \
  --file src/poc_cli/main.py \
  --output ./candidate
```

Foram então autorados manualmente:

- `candidate/templates/handler.py.tmpl`
- `candidate/templates/parser-registration.py.tmpl`
- `candidate/capability.yaml` (preconditions, steps, verification)
- `candidate/examples/generalization/case.yaml` (segundo caso aprovado: `report`)
- ajustes nos patches de `expected.patch` / `accepted.patch`

A validação passou nos quatro portões:

```text
Capability poc.add-cli-command
  PASS fidelity: patch and verification match
  PASS generalization: patch and verification match
  PASS idempotency: second application refused explicitly
  PASS safe_refusal: precondition failed: 'def cmd_add(' already exists in src/poc_cli/main.py
```

E a capability foi instalada:

```bash
seh capability install ./candidate --allow-verification
```

### 3. Warm path — reutilização

Depois de instalada, dois novos comandos foram adicionados sem reabrir o arquivo manualmente:

```bash
seh capability run poc.add-cli-command --param name=report --apply --allow-verification
# Applied poc.add-cli-command v1 to 1 file(s), verified, in 67ms

seh capability run poc.add-cli-command --param name=purge --apply --allow-verification
# Applied poc.add-cli-command v1 to 1 file(s), verified, in 68ms
```

Tentativa de duplicação foi recusada:

```bash
seh capability run poc.add-cli-command --param name=report --apply --allow-verification
# error: precondition failed: 'def cmd_report(' already exists in src/poc_cli/main.py
```

O CLI final contém `{add,list,status,report,purge}`.

---

## Números brutos

| Etapa | Medida observada |
|---|---|
| Edição manual do 1º comando (`status`) | ~8 linhas, ~60 s |
| Autoragem da capability (templates + patches + validação) | ~15 min |
| `seh capability validate` | ~1 s |
| `seh capability install` | ~1 s |
| `seh capability run ... --apply` | ~68 ms |
| Operações subsequentes sem reabrir arquivo | 2 (report, purge) |

---

## Análise de utilidade

### Onde a capability se provou

1. **Repetições são instantâneas e determinísticas.** Adicionar `report` ou `purge` levou ~68 ms e produziu exatamente o mesmo formato do comando original.
2. **Segurança mecânica.** A recusa idempotente evita duplicação silenciosa; em um projeto real, isso evita regressões.
3. **O patch é reviewável.** Antes de aplicar, `seh capability run` mostra o diff exato.
4. **Não há inferência no caminho quente.** A operação não chama modelo.

### Onde os números são desfavoráveis

1. **O custo de autoragem é alto para poucas repetições.** Gastaram-se ~15 min para criar a capability. Cada execução manual futura levaria ~30–60 s. O ponto de equilíbrio está em torno de **15–30 novos comandos** antes de o tempo de setup se pagar.
2. **A capability é estreita.** Ela só sabe adicionar comandos argparse com exatamente esse formato. Se o CLI mudar para Click, Typer, adicionar argumentos ou imports, a capability quebra em vez de adaptar.
3. **O trabalho cognitivo não desaparece — muda de lugar.** Quem autorar a capability ainda precisa entender AST, offsets, templates, e ainda precisa garantir que `expected.patch` contenha apenas o subconjunto estrutural.
4. **Generalização exige um segundo caso real.** Sem um segundo comando para validar, a capability é apenas memorização. No experimento, o segundo caso (`report`) foi inventado, não uma ocorrência real.

### Veredito honesto

Para este padrão específico, em um projeto pequeno, **o SEH ainda não é economicamente vantajoso**. A economia só aparece quando **pelo menos uma destas condições** é verdadeira:

- o padrão ocorre dezenas de vezes (catálogo de subcomandos, handlers de eventos, endpoints);
- o setup é amortizado por muitos desenvolvedores/repositórios;
- o custo cognitivo de relembrar o padrão a cada vez é alto (projetos grandes, onboarding);
- o agente externo fornecer a maior parte da autoragem (templates, segunda caso), reduzindo o custo humano.

No estado atual do SEH (Phase 0, vocabulário fechado, sem MCP), o produto é **tecnicamente viável, mas economicamente justificável só em projetos com padrões de alta recorrência**.

---

## Reprodução

```bash
cd experiments/poc-utilidade/poc-cli

# cold path
git checkout 0d7610b

# warm path
seh capability run poc.add-cli-command --param name=foo --apply --allow-verification
```

A capability instalada está em `.seh-capabilities/poc.add-cli-command/`.
