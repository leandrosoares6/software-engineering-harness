# Recorrência de região — pré-registro

**Status:** pré-registro. Nenhum número de campo foi produzido ainda.
**Contrato:** este arquivo é fixado **antes** da primeira execução no repositório de campo.
Um limiar que mude depois invalida a medição em vez de emendá-la — mesma disciplina de
[`../fase0/PRE_REGISTRATION.md`](../fase0/PRE_REGISTRATION.md) e do `m2_pilot/manifest.yaml`.

---

## A pergunta

O resultado negativo que matou as capabilities mediu **identidade de procedimento**: o mesmo
wiring mecânico recorrendo. Encontrou 3 eventos em 5 meses, 4 linhas em 1242 inserções,
break-even em anos (§2 do [PRD](../../docs/CONTEXT_COMPILER_PRD.md)).

Um registro de caminho — o que o Context Compiler acumularia — precisa de algo mais fraco:
que uma mudança nova caia numa **região** que alguma mudança anterior já visitou. Não precisa
ser o mesmo procedimento. Precisa ser a mesma vizinhança.

> **Com que frequência o conjunto de arquivos de um commit já foi coberto por um commit anterior?**

Isso é fato histórico, mensurável direto do `git log`, e não depende de nenhum resolver existir.

## A grandeza

Para cada commit-alvo `A`, sobre os commits anteriores elegíveis `B`:

```text
containment(A) = max_B  |A ∩ B| / |A|
```

"Quanto da região desta mudança já tinha sido visitada por uma mudança anterior?" É a fração
que um registro escrito depois de `B` teria apontado.

Containment, e não Jaccard, de propósito: o denominador é o alvo. Um commit anterior grande que
cobre o alvo inteiro é exatamente o caso favorável ao produto, e o Jaccard o penalizaria.

## Os controles, e por que cada um existe

| controle | parâmetro | ameaça que remove |
|---|---|---|
| **cooldown** | `--cooldown-days` | commits consecutivos do mesmo trabalho não são recorrência. É a forma temporal do achado *"repetition means events, not similar structures"* de [`PHASE0_FINDINGS.md`](../../docs/PHASE0_FINDINGS.md) |
| **teto de arquivos** | `--max-files 50` | um rename de repositório inteiro conteria trivialmente todo commit posterior. Excluído como alvo **e** como candidato |
| **null hot-k** | automático | se uma lista estática dos arquivos mais tocados pontua igual, o sinal é "existem arquivos quentes", não recorrência |
| **null aleatório** | automático | o piso |
| **prefixo apenas** | automático | `hot-k` e candidatos são calculados só com o passado do alvo. É o controle de vazamento do §15 do PRD, na forma temporal |

Os dois nulls são o coração. Sem eles a medida sobe sozinha em qualquer repositório com um
`urls.py` e um `settings.py`.

## Execução decisória

```bash
python experiments/region_recurrence/measure.py \
  --repo /caminho/do/repo-de-campo \
  --cooldown-days 30 \
  --json resultado.json
```

O repositório de campo é o mesmo da varredura do §2 do PRD — 654 commits, 15 meses, 5 autores —
para que o número converse com o resultado negativo em vez de correr ao lado dele.

**Cooldown decisório: 30 dias.** Escolhido antes de rodar, e não por conveniência: o procedimento
recorrente encontrado na varredura recorreu 3 vezes em 5 meses, ou seja, com intervalos da ordem
de 50 dias. Um cooldown menor mediria follow-up da mesma feature e não seria comparável ao número
que matou as capabilities.

Sensibilidade obrigatória, reportada junto: **7 e 14 dias**. Se o resultado colapsa de 7 para 30,
o que foi medido foi adjacência de trabalho em curso, e o veredito é o de 30.

## Os limiares, fixados agora

Estatística primária: **fração de alvos com `containment ≥ 0.50` pelo melhor commit anterior**,
em cooldown 30, e a **margem dessa fração sobre o null hot-k**.

| fração ≥ 0.50 | margem sobre hot-k | leitura |
|---|---|---|
| **≥ 50%** | **≥ 15 pp** | **funda a Fase 1.** Metade das mudanças cai em região já visitada, e a recorrência carrega informação que uma lista estática não tem |
| ≥ 50% | < 15 pp | o sinal é arquivo quente. O produto barato é uma lista estática de arquivos quentes, não um resolver — e ela custa uma tarde |
| 25%–50% | ≥ 15 pp | inconclusivo. O registro ajuda uma minoria; decide-se pela distribuição de lag e pelo tamanho dos alvos |
| **< 25%** | qualquer | **morto.** Região recorre raro demais para pagar, mesmo veredito das capabilities, e pelo mesmo motivo |

Condição de piso, análoga à da Fase 0: **a mediana do melhor-anterior tem que superar a mediana
do hot-k em todos os três cooldowns.** Um ganho que só aparece na janela mais permissiva é
adjacência disfarçada.

## Leitura qualitativa obrigatória, antes das tabelas

O relatório imprime as 10 recorrências mais fortes com assunto do alvo e do anterior. **Elas se
leem primeiro.** Um containment de 1.00 construído sobre `__init__.py` mais um módulo de settings
não é uma região que um registro teria descrito de forma útil, e nenhuma tabela mostra isso.

Se as 10 mais fortes forem infraestrutura compartilhada, o número está certo e a interpretação
está errada — e o achado é esse.

## O que este experimento estabelece

O **teto de frequência** dos registros de caminho: com que frequência a oportunidade existe.

Ele é o par do que a Fase 0 já estabeleceu. A Fase 0 mediu o **teto de valor** com um seed perfeito
montado à mão (52 → 16 tool calls, B/A = 30,8%). Este mede o **teto de frequência** com um
"resolver" oráculo que sempre escolhe o melhor commit anterior possível. Payback precisa dos dois,
e nenhum dos dois precisa de código de produto para ser medido.

## O que ele não estabelece

- **Nada sobre recuperação.** O máximo sobre todos os anteriores é um oráculo: assume que o
  registro certo seria encontrado. Achar o registro certo a partir do prompt é o problema do
  Seed Resolver, e continua não testado. Este número é o teto dele, não a medida dele.
- **Nada sobre autoria.** Assume que um registro teria sido escrito após cada commit. Se escrever
  o registro custar caro ou for esquecido, a frequência efetiva é menor.
- **Nada sobre utilidade.** Sobreposição de região não é sobreposição de *conhecimento*. Dois
  commits podem tocar o mesmo arquivo por razões sem relação. É a mesma limitação que o oráculo de
  localização da Fase 0 declarou: mede o lugar, não o conteúdo.
- **Nada sobre generalização.** Um repositório. Rodar em outros é barato e deve ser feito antes de
  qualquer alegação pública.

## Vieses conhecidos, com direção declarada

- `--no-renames`: um arquivo renomeado vira caminho novo e **subestima** a recorrência. Conservador.
- Data de autor, não de commit: rebase preserva a de autor, que é quando o trabalho aconteceu.
  Direção do viés sobre o cooldown: indeterminada, provavelmente pequena.
- Filtro de extensões: o padrão mantém só fonte. Docs e configuração ficam de fora, o que
  **subestima** a recorrência num repositório onde a mudança atravessa documentação. Rodar também
  com `--extensions ""` e reportar os dois.
- O `hot-k` é dimensionado pela mediana de tamanho dos commits anteriores, ou seja, recebe o mesmo
  orçamento de arquivos que um registro. É a comparação justa; um `hot-k` fixo e grande venceria
  por tamanho, não por qualidade.

## Custo

Uma tarde, contra 2–4 semanas da Fase 1 do PRD. É a mesma razão que justificou a Fase 0 no §2:
*o erro anterior não foi escolher a hipótese errada, foi construir semanas antes de testá-la.*
