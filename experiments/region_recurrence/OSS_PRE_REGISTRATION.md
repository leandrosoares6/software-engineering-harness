# Fase 0.5 — seleção open source, pré-registro

**Status:** fixado antes de clonar qualquer repositório e antes de rodar qualquer medição.
**Complementa:** [`README.md`](README.md), que fixa a grandeza, os controles e os limiares.

Este arquivo fixa **quais** repositórios, **por que esses**, e — o item que carrega o peso — **qual
resultado é esperado em cada um, antes de olhar**.

---

## Por que rodar em open source se o veredito é do repositório de campo

Não é para aumentar amostra. É para responder uma pergunta diferente, e mais básica:

> **A medida discrimina, ou ela devolve "tem recorrência" em qualquer repositório?**

Uma medida que nunca volta baixa não mede nada, e o número de campo herdaria essa inutilidade sem
que ninguém percebesse. O `README.md` já protege contra o confundidor *dentro* de um repositório —
o null de arquivos quentes. Isto protege contra o confundidor *entre* repositórios.

O repositório de campo continua sendo o que decide o produto. Estes três decidem se o instrumento
serve.

## O eixo escolhido

A hipótese sobre *por que* região recorre:

> Trabalho de feature recorre em região quando a arquitetura é estável e cada mudança atravessa as
> mesmas camadas. Ela **não** recorre quando o repositório cresce por adição de partes
> independentes, onde trabalho novo significa diretório novo.

Os três repositórios são escolhidos para varrer esse eixo de ponta a ponta, não para representar
"software open source".

## Os três, e a previsão

| # | repositório | forma | previsão |
|---|---|---|---|
| 1 | **go-gitea/gitea** | monorepo full-stack de produto: backend Go, templates e frontend TS na mesma árvore. Uma feature costuma atravessar model → serviço → rota → template → JS | **mais alta** |
| 2 | **scikit-learn/scikit-learn** | biblioteca: estimadores semi-independentes sobre um núcleo muito compartilhado (`utils/`, `base.py`) | **intermediária** |
| 3 | **home-assistant/core** | milhares de integrações independentes, cada uma em seu diretório. Trabalho novo em geral é diretório novo | **mais baixa** |

**Previsão registrada, na estatística primária (fração com `containment ≥ 0.50`, cooldown 30):**

```text
gitea  >  scikit-learn  >  home-assistant
```

O gitea entra por ser o mais próximo do repositório de campo *e* do cenário-alvo: mudança que
atravessa backend e frontend na mesma árvore. O home-assistant entra como **repositório de
falsificação** — se ele voltar alto, o instrumento está quebrado, e é melhor descobrir isso aqui do
que no número que decide o produto.

O scikit-learn é o mais informativo dos três para o null: um núcleo compartilhado deveria fazer o
melhor-commit-anterior parecer bom **pelo motivo errado**. Se o melhor-anterior vencer o hot-k
**ali**, é o sinal mais forte que esta fase pode produzir de que a recorrência não é só arquivo
quente.

## Como cada desfecho é lido

Fixado agora, para não ser escolhido depois:

| desfecho | leitura |
|---|---|
| ordem prevista se confirma | o instrumento discrimina. O número de campo pode ser lido pelos limiares do `README.md` |
| **os três altos** | o instrumento está medindo infraestrutura compartilhada, não recorrência. O número de campo **não** deve ser usado, e a medida precisa de conserto antes de qualquer decisão |
| **os três baixos** | ou `0.50` é exigente demais como corte, ou recorrência de região não existe na forma suposta. Distinguir pela quebra por tamanho de alvo antes de concluir |
| ordem invertida | a medida talvez funcione, mas a **teoria** do eixo está errada: concentração de camadas não é o que produz recorrência. Nesse caso o número de campo é lido, mas nada é generalizado a partir dele |

Um resultado que confirma a ordem prevista **não** prova que o produto funciona. Prova só que a
régua não está quebrada.

## Parâmetros, fixados

Iguais aos do `README.md`, sem exceção por repositório:

- cooldown decisório **30 dias**; sensibilidade reportada em **7 e 14**;
- `--max-files 50`, `--min-files 1`, `--union-depth 3`, `--seed 0`;
- rodada primária com o allowlist de extensões padrão; rodada secundária com `--extensions ""`,
  ambas reportadas;
- `--since` **não é usado** no gitea nem no scikit-learn.

### A exceção, declarada porque muda a amostra

`home-assistant/core` tem histórico grande demais para o custo do script, que cresce com o quadrado
do número de commits elegíveis. Ele roda com **`--since="4 years ago"`**, fixado agora e não
ajustado depois.

Direção do viés: recortar a janela **reduz** o número de anteriores disponíveis e portanto
**subestima** a recorrência dele. Como a previsão para o home-assistant já é "mais baixa", o viés
anda a favor da previsão — o que enfraquece o teste de falsificação em vez de fortalecê-lo. Fica
registrado como limite real: um home-assistant baixo é evidência mais fraca do que seria com o
histórico inteiro.

## Ameaças conhecidas nesta seleção

1. **Convenção de commit difere de time de produto.** Squash merge concentra uma feature inteira em
   um commit, o que **aumenta** o tamanho do alvo e tende a **reduzir** o containment. Direção:
   conservadora.
2. **Bots.** Commits de dependabot, tradução e CI existem nos três. O allowlist de extensões e o
   `--max-files 50` removem a maior parte, mas não todos. Se bots dominarem a lista qualitativa das
   10 recorrências mais fortes, **isso é o achado**, e um filtro de autor seria adicionado e
   **re-registrado** antes de qualquer nova leitura — nunca aplicado em cima do resultado já visto.
3. **Três repositórios não são uma amostra.** São três pontos escolhidos a dedo num eixo declarado.
   Servem para testar a régua, e não sustentam nenhuma alegação sobre "repositórios em geral".
4. **A previsão foi escrita por quem formulou a hipótese.** Mesma ameaça declarada na Fase 0. A
   proteção aqui é que a previsão é falsificável e está escrita antes, não que quem a escreveu seja
   neutro.

## Ordem de execução

1. Comitar este arquivo.
2. Clonar os três com `--filter=blob:none --no-checkout` — só metadados e nomes de arquivo são
   necessários, blob nenhum é lido.
3. Rodar, reportar em `OSS_RESULT.md`, sem editar este arquivo.
