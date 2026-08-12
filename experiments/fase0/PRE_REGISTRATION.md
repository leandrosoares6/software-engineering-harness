# Fase 0 — pré-registro

Contrato: §16 de [`../../docs/CONTEXT_COMPILER_PRD.md`](../../docs/CONTEXT_COMPILER_PRD.md).

Escrito **antes** da primeira sessão. Um valor que mude depois invalida o experimento em
vez de emendá-lo, pela mesma razão do manifesto do M2: depois do fato, um critério
ajustado é indistinguível de um critério medido.

Não confundir com `../phase0/`, que é a Fase 0 do produto anterior — nome colidente,
assunto distinto.

## A pergunta

> Um pacote de contexto feito à mão, com o seed perfeito escolhido por um humano, reduz
> tool calls em relação ao agente usando apenas a documentação que o repositório já tem?

O seed é escolhido a mão de propósito. Isso remove o Seed Resolver do experimento, e o
que sobra é o **teto** do produto. Teto ruim é conclusivo.

## Repositório e alvo

Repositório de trabalho privado, referenciado sem identificação: 654 commits, 15 meses,
5 autores, Python, suíte de 450 testes na árvore pai.

| | |
| --- | --- |
| commit-alvo | `b2e647f0` — *"Corrige retomada de auth no menu do WhatsApp"* |
| árvore da sessão | `b2e647f0^` = `bebffa5` |
| escopo do commit | 4 arquivos, 116 inserções |
| suíte pré-existente no pai | 450 passed |

O alvo foi escolhido por **filtragem mecânica** de 12 candidatos, não por inspeção. Os
rejeitados e o motivo de cada um estão no §16 do PRD.

## Controle de vazamento

A árvore está em `b2e647f0^`. O agente **não alcança** o alvo nem nada posterior a ele.
Cada sessão recebe uma cópia própria; nenhuma escreve no repositório original.

Foi assim que o probe da fase anterior se estragou: seu Arm A encontrou o pacote da
capacidade e recebeu o tratamento sem que ninguém notasse.

## O prompt

Idêntico nos dois arms. Redigido como **relato de sintoma**, não como a descrição que o
autor do fix deu — o corpo do commit nomeia "o orquestrador" e "o handler do WhatsApp", e
reproduzir isso entregaria a localização, que é justamente o que se mede.

```text
No menu do WhatsApp, sessões cujo access token já expirou mas que ainda têm um
refresh_token válido estão sendo tratadas como deslogadas. O usuário é jogado no
fluxo de login em vez de ter a sessão renovada automaticamente.

Corrige isso.
```

## Arms

| arm | tratamento |
| --- | --- |
| A | prompt + acesso raw à árvore, com todo o `AGENTS.md`, o `copilot-instructions.md` e os 61 arquivos de `docs/` que ela já tem |
| B | prompt + `context.md` anexado, mesmo acesso raw |

`R = 3` sessões frias por arm, seis no total. A repetição mede **não-determinismo do
modelo**, não variância de tarefa — a tarefa é a mesma. Foi a fraqueza declarada do probe
anterior (`n = 1`, sem controle algum).

## Oráculo

Localização, conforme §16. Conjunto de arquivos-fonte declarado, derivado do commit:

```text
app/agent/nodes/orchestrator.py
app/agent/nodes/autoservice/whatsapp_flows.py
```

A edição conta quando seu caminho está nesse conjunto. Os dois arquivos de teste que o
commit também tocou ficam **fora** do conjunto: o prompt não pede testes, e contá-los
premiaria um agente que começasse escrevendo teste.

Não-regressão: a suíte pré-existente continua em 450 passed depois da sessão.

## Métrica

**Tool calls até a primeira edição no conjunto declarado.** Conta toda invocação de
ferramenta desde o início da sessão, incluindo edições em arquivos fora do conjunto —
editar o arquivo errado é custo real.

Registrados, não decisórios: arquivos distintos lidos, cobertura do conjunto ao final da
sessão, tokens, tempo de parede.

## Controle de escopo

Refatoração adjacente não solicitada é registrada e **exclui a repetição**. No probe
anterior um arm refatorou outro módulo de brinde, +97 linhas, e o delta virou mistura de
dois efeitos.

## Limiar

| mediana de B ÷ mediana de A | leitura |
| --- | --- |
| ≤ 50% | vence. Segue para a Fase 1, sabendo o teto |
| 50%–90% | inconclusivo. Não paga 2–4 semanas no melhor caso possível |
| > 90% | morto. O projeto termina aqui, sem código |

Piso: **nenhuma repetição de B pode ser pior que a mediana de A.** Ganho que só aparece na
média não é o efeito que o produto promete.

O corte em 50% é aproximadamente o que a prosa contaminada já entregou no probe anterior
(54 → 27 tool calls). Um pacote com seed perfeito, montado a mão, precisa bater isso.

## Ameaças declaradas

- **Uma tarefa, um repositório, um modelo.** Nada aqui generaliza; é probe, não benchmark.
- **O oráculo não verifica correção.** Um agente que edite o arquivo certo com conteúdo
  errado marca ponto. Declarado no §16 e aceito nesta fase.
- **O `context.md` é montado por quem formulou a hipótese.** É o teto por construção, e
  por isso o resultado só é informativo quando **negativo**. Um B vencedor mede o melhor
  caso, não o produto.
- **`R = 3` é pequeno** para caracterizar dispersão. Serve para tornar a dispersão
  visível, não para estimá-la.
