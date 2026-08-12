# O que este POC prova, e onde

Retido porque quatro alegações neste repositório se apoiam nele. Um achado cuja prova
não está na árvore é um achado que terá de ser retirado depois — este projeto já
cometeu esse erro uma vez, quando um adaptador foi apagado e três documentos seguiram
afirmando o que a evidência dele mostrava.

O `README.md` ao lado é o relatório do desenvolvedor: custo de autoria, tempos de
cold e warm path, e o veredito econômico honesto. Este arquivo registra o que o POC
acabou provando **sobre o SEH**, que não é aquilo para que foi construído.

## O histórico está em `poc-cli-history.bundle`

A cópia de trabalho de `poc-cli/` deliberadamente **não** é comitada: um repositório
Git aninhado entraria nesta árvore como um gitlink inútil, apontando para lugar
nenhum. O histórico completo viaja como bundle, 6.7K, que `git bundle verify` reporta
como completo.

```bash
git clone experiments/poc-utilidade/poc-cli-history.bundle poc-cli
```

Os commits **são** a evidência, então precisam ser alcançáveis e não descritos. É o
mesmo padrão que as âncoras de proveniência impõem a um pacote de capacidade.

| commit | o que estabelece |
|---|---|
| `43f6664` | estado inicial |
| `597bc2a` | CLI inicial — o **baseline** da captura |
| `0d7610b` | comando `status`. Diz `help="show status"`. É a mudança realmente aceita |
| `a7ab9da` | warm path: `report` e `purge` gerados pela capacidade desonesta, que shipou `help="TODO"` para dentro de `src/poc_cli/main.py` |
| `73761c6` | a recaptura honesta, com `help` como `text_line` e proveniência `verified` contra `597bc2a..0d7610b` |

`a7ab9da` e `73761c6` coexistem de propósito. O primeiro é o defeito, o segundo é a
correção. Apagar o primeiro apagaria a prova.

## O defeito que ele expôs no SEH

A capacidade em `a7ab9da` passava **os quatro gates** enquanto sua fixture de
fidelidade alegava que o desenvolvedor havia aceito `help="TODO"`. O commit `0d7610b`
diz `help="show status"`.

Os dois patches — `expected.patch` e `accepted.patch` — tinham sido ajustados juntos
para caber numa limitação dos templates. A checagem que deveria pegar isso comparava
`expected ⊆ accepted`: dois arquivos escritos pelo autor, verificados um contra o
outro e contra nada mais. O `scope.yaml` gravava, uma linha acima, os dois commits que
exporiam a contradição, e nenhum código os lia.

O defeito não era do POC. `capture` não escrevia digests e a validação não resolvia
commits, então o produto disponibilizava uma alegação infalsificável, e um autor
razoável a tomou.

## As alegações que dependem disto

- [`docs/PHASE0_FINDINGS.md`](../../docs/PHASE0_FINDINGS.md) — *"A gate is worth no
  more than the reference it measures against"*, incluindo o desenho descartado de
  comparar bytes contra um renderizador.
- [`docs/CAPABILITY_MODEL.md`](../../docs/CAPABILITY_MODEL.md) — as duas âncoras de
  proveniência agora normativas, e a **ameaça declarada** do `text_line`, cuja
  evidência de admissão é precisamente a ocorrência única registrada aqui.

## O que este POC *não* prova

Ele nunca testou a tese econômica, e não podia. Seus comandos são `print("<nome>")` —
wiring ratio alto sobre denominador vazio — e nenhum agente participou. As medições do
`README.md` são de **minutos humanos**, não de tool calls nem de contexto de sessão.

A ameaça do `text_line` já registra a consequência: nada construído sobre ele pode ser
citado a favor dele, e a capacidade daqui passando os quatro gates é consequência da
admissão, não apoio a ela.

O resultado que de fato fechou o produto de capabilities veio depois, da varredura de
campo: 3 ocorrências em 5 meses, 4 linhas de wiring em 1242 inserções, três primitivos
inexistentes. Está no §2 de
[`docs/CONTEXT_COMPILER_PRD.md`](../../docs/CONTEXT_COMPILER_PRD.md).
