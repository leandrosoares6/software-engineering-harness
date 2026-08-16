# Fase 0.5 — resultado da seleção open source

Pré-registro: [`OSS_PRE_REGISTRATION.md`](OSS_PRE_REGISTRATION.md), comitado em `f3c243b` **antes**
de clonar qualquer repositório. Grandeza e limiares: [`README.md`](README.md).

## Veredito

**A previsão falhou e o instrumento não discrimina.** Pelo desfecho que o pré-registro chama de
"os três altos": **o número do repositório de campo não deve ser lido pelos limiares do
`README.md`.** A medida precisa de conserto antes de fundar ou matar qualquer coisa.

Isso **não** é um resultado negativo sobre o produto. É um resultado negativo sobre a régua.

## Os números

Estatística primária, cooldown decisório de 30 dias.

| repositório | previsão | elegíveis | alvos | **fração ≥ 0.50** | hot-k | margem |
|---|---|---|---|---|---|---|
| go-gitea/gitea | mais alta | 12.366 | 12.269 | **79,2%** | 3,6% | 75,6 pp |
| scikit-learn | intermediária | 24.261 | 23.904 | **82,0%** | 0,8% | 81,2 pp |
| home-assistant/core | mais baixa | 45.486 | 45.015 | **79,4%** | 1,6% | 77,8 pp |

Ordem prevista: `gitea > scikit-learn > home-assistant`.
Ordem observada: `scikit-learn > home-assistant > gitea`, dentro de uma faixa de **2,8 pontos**.

A previsão não erra por pouco na ordem — ela erra por os três serem **o mesmo número**. O
repositório escolhido como falsificador não falsificou.

### Sensibilidade ao cooldown

| repositório | 7 dias | 14 dias | 30 dias |
|---|---|---|---|
| gitea | 83,1% | 81,7% | 79,2% |
| scikit-learn | 87,9% | 85,6% | 82,0% |
| home-assistant | 84,6% | 82,4% | 79,4% |

Monotônico e suave nos três, sem colapso. O cooldown está funcionando — não é adjacência de
trabalho em curso. Mas ele também não separa nada.

## O diagnóstico, e ele é pós-hoc

**Declarado como pós-hoc de propósito.** O null que explica o resultado foi adicionado *depois* de
ver os números, e por isso não pode ser lido como confirmação de nada. Ele serve para dizer o que
consertar.

O confundidor previsto era arquivo quente, e o hot-k o teria pego. Ele está em **0,8% a 3,6%** nos
três: não é isso.

O confundidor real é outro. Foi acrescentado o null **`reachable`** — a fração dos arquivos do alvo
que *qualquer* commit anterior já tocou, sem limite de quantos:

| repositório | mediana `reachable` |
|---|---|
| gitea | **1,00** |
| scikit-learn | **1,00** |
| home-assistant | **1,00** |

Em repositório maduro, **praticamente todo arquivo de qualquer commit já foi tocado antes**. Com 12
a 45 mil anteriores no pool, o máximo sobre todos eles quase sempre acha um que cobre o alvo — e
para commit de 1 arquivo, que é 39% dos alvos no gitea e 38% no home-assistant, o resultado é 1,00
por construção.

A pergunta que a medida faz — *"esta região já foi visitada?"* — tem resposta "sim" quase sempre.
Uma pergunta cuja resposta é sempre sim não informa decisão.

### A grandeza melhor, que também não discrimina

`cohesion = melhor anterior ÷ reachable`: quanto da parte já visitada **um único** commit captura.
É contra isso que um registro de caminho realmente compete.

Mediana de `cohesion` por tamanho de alvo:

| arquivos no alvo | gitea | scikit-learn | home-assistant |
|---|---|---|---|
| 1 | 1,00 | 1,00 | 1,00 |
| 2–3 | 1,00 | 1,00 | 1,00 |
| 4–7 | 0,75 | 0,75 | 0,80 |
| 8–15 | 0,57 | 0,50 | 0,67 |
| 16+ | 0,43 | 0,38 | 0,34 |

Tem estrutura real: coesão decai com o tamanho do commit, e decai **da mesma forma nos três**. A
leitura mais provável é que isso seja propriedade de **como pessoas commitam** — um commit de 4
arquivos costuma ser um trabalho coeso, um de 20 é uma varredura — e não propriedade do
repositório. O que explica por que não separa.

## O qualitativo, que é onde a surpresa está

O pré-registro manda ler as 10 recorrências mais fortes antes das tabelas. Elas passam no teste nos
três, inclusive no que deveria falhar.

**gitea** — regiões de domínio genuínas, com lag mediano de 74 dias:

- `Store webhook event in database` ← `Restructure webhook module`, 431 dias, 24 arquivos
- `Fix Matrix and MSTeams nil dereference` ← `Webhook for Wiki changes`, 439 dias
- `Refactor to use optional.Option for issue index` ← `Refactor and enhance issue indexer`, 226 dias

**home-assistant**, escolhido como falsificador por crescer em integrações independentes:

- `Set PARALLEL_UPDATES = 0 for MQTT components` ← `Rename mqtt mixins module to entity.py`, 63 dias
- `Store runtime data inside the config entry in Tuya` ← `Migrate Tuya to new sharing SDK`, 99 dias
- `Simplify PLATFORMS patching in Tuya test` ← `Drop Tuya compatibility code`, 209 dias

**A teoria do eixo estava errada.** Integrações independentes não são escritas uma vez e
esquecidas: `mqtt`, `tuya` e `unifiprotect` são revisitadas por anos. Não existia, nesta seleção, o
repositório de baixa recorrência que o desenho pressupunha.

Isso deixa duas explicações vivas, e a medida **não distingue entre elas**:

1. recorrência de região é genuinamente universal — o que seria boa notícia para o produto;
2. a medida é frouxa o bastante para dar alto em qualquer lugar — o que a torna inútil.

Conflacionar as duas é exatamente o defeito.

## O que isto muda

- A **Fase 0.5 não fundou a Fase 1**, e também não a matou. Ficou inconclusiva por defeito de
  instrumento.
- O número do repositório de campo, quando rodado, **não** deve ser lido pelos limiares do
  `README.md`. Rodá-lo agora produziria ~80% como os outros três, e esse número não significaria
  nada.
- O `README.md` e o `OSS_PRE_REGISTRATION.md` ficam como estão. Não se emenda pré-registro depois
  do resultado — o que se faz é registrar o próximo.

## O redesenho proposto, a ser re-registrado antes de rodar

O defeito é o tamanho do pool de candidatos: o máximo sobre 45 mil anteriores é um oráculo que
nenhuma recuperação real teria. A correção é restringir o pool ao que uma recuperação plausível
traria à tona.

**Proposta:** ranquear os anteriores por sobreposição lexical entre o assunto do alvo e o assunto
do anterior — ambos em linguagem de domínio, que é o mecanismo do §10.2 do PRD — e medir containment
apenas contra os **top-K**, com K pequeno e fixado.

Isso muda a pergunta de *"esta região já foi visitada?"*, que é sempre sim, para *"o texto do
pedido permite achar qual visita anterior importa?"* — que é o que o produto precisa saber, pode
voltar negativa, e continua custando um script.

Duas mudanças de escopo que vêm junto, e pelo mesmo motivo:

- **alvos com menos de 4 arquivos saem da estatística primária.** Eles são 39% a 38% da amostra e
  acertam 1,00 por construção;
- **`reachable` vira o denominador declarado**, não um null acrescentado depois.

O custo disso é reconhecer que a Fase 0.5 não conseguiu evitar a pergunta do Seed Resolver. O
atalho barato não separou do null, e essa é a informação que esta rodada comprou.

## Reprodução

```bash
git clone --filter=blob:none --no-checkout https://github.com/go-gitea/gitea.git
python experiments/region_recurrence/measure.py --repo ./gitea --cooldown-days 30
```

Tempo de análise: 8s (gitea), 9s (scikit-learn), 76s (home-assistant, com `--since="4 years ago"`).
`--seed 0`, extensões padrão, `--max-files 50`, `--union-depth 3` em todos.
