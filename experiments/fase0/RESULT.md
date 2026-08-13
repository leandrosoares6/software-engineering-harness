# Fase 0 — resultado

Pré-registro: [`PRE_REGISTRATION.md`](PRE_REGISTRATION.md), comitado em `2062132` **antes**
da primeira sessão. Contrato: §16 de
[`../../docs/CONTEXT_COMPILER_PRD.md`](../../docs/CONTEXT_COMPILER_PRD.md).

## Veredito

**B vence.** Segue para a Fase 1.

| métrica | Arm A | Arm B | mediana A | mediana B | B/A |
| --- | --- | --- | --- | --- | --- |
| tool_uses | 36, 56, 52 | 15, 21, 16 | 52 | 16 | **30,8%** |
| tokens | 81.398, 146.332, 148.197 | 65.126, 83.970, 65.084 | 146.332 | 65.126 | 44,5% |
| segundos | 293, 521, 567 | 148, 255, 166 | 521 | 166 | 31,9% |

- Limiar pré-registrado `≤ 50%`: **satisfeito** (30,8%).
- Piso — nenhuma repetição de B pior que a mediana de A (52): **satisfeito** (pior B = 21).
- Oráculo de localização: **6/6** sessões editaram dentro do conjunto declarado.
- Não-regressão: **6/6** em 450 passed.
- Controle de escopo: **nenhuma** repetição excluída.

Os diffs e as suítes foram verificados contra a árvore pai pristina, não aceitos dos
agentes.

## Cobertura do conjunto declarado

O conjunto-oráculo tinha dois arquivos. Cinco das seis sessões alteraram apenas
`orchestrator.py`; só `b2` alterou também `whatsapp_flows.py`.

Isso **não** conta contra o resultado — o oráculo pré-registrado é a primeira edição
dentro do conjunto, e a cobertura foi declarada secundária, não decisória. Mas registra
que a maioria considerou o segundo arquivo desnecessário, e duas sessões justificaram por
quê: o caminho de seleção numérica de menu atribui uma variável que não usa, e o outro
ponto já passa pelo auto-refresh por outra rota.

## O achado qualitativo, que vale mais que a razão

**Os dois arms convergiram para a mesma solução.** Seis sessões, sem exceção: um helper
que delega para `auto_refresh_token_if_needed` no canal push e mantém
`verify_authentication()` nos demais. É o mesmo padrão que o probe da fase anterior
observou, quando os arms produziram wiring byte-idêntico.

O pacote de contexto não está comprando **correção**. Está comprando o **caminho até
ela**. É exatamente a distinção que o §3 do PRD alega, e agora tem medição em vez de
argumento.

## Desvio do pré-registro, declarado

A métrica pré-registrada era **tool calls até a primeira edição no conjunto declarado**.
Ela **não foi medível como especificada**, e o veredito acima usa o `tool_uses` total da
sessão, que vem da telemetria do harness.

O motivo: "até a primeira edição" só existia por auto-relato dos agentes, e o auto-relato
divergiu da telemetria de forma **diferencial entre os arms**:

| run | auto-relato (total) | telemetria | subnotificação |
| --- | --- | --- | --- |
| b3 | 16 | 16 | 0% |
| b2 | 20 | 21 | 5% |
| b1 | 12 | 15 | 20% |
| a2 | 54 | 56 | 4% |
| a3 | 50 | 52 | 4% |
| a1 | 20 | **36** | **44%** |

O viés é maior no Arm A, ou seja, na direção que **estreitaria** a diferença entre os
arms. Usar o auto-relato favoreceria o resultado que já obtivemos, o que é razão
suficiente para não usá-lo.

A substituição é **mais conservadora**: o total inclui trabalho posterior à primeira
edição, que não favorece nenhum arm em particular, e vem de instrumentação que os sujeitos
não controlam.

**Lição transferível:** se for medir agentes, não peça que eles se contem.

## Segundo desvio: os hooks do harness inflam a contagem

Cinco das seis sessões relataram uma tentativa de `Edit` bloqueada por um gate que exige
apresentar fatos antes de escrever, mais as buscas que o gate então exigiu. São invocações
que não são exploração.

Afeta os dois arms, então é ruído em modo comum — mas não é zero, e não estava previsto no
pré-registro.

## O que este resultado estabelece

Que **um pacote de contexto com seed perfeito, montado à mão, reduz exploração em ~3×**
numa tarefa real de localização entre camadas, num repositório bem documentado
(`AGENTS.md`, `copilot-instructions.md`, 61 arquivos em `docs/`).

Esse é o **teto** do produto.

## O que ele não estabelece

- **Nada sobre o Seed Resolver.** Ele foi contornado de propósito. O teto é 30,8%; quanto
  disso um resolver determinístico captura é a pergunta da Fase 1, e é onde o produto
  ainda pode morrer.
- **Nada sobre correção.** O oráculo é localização. Um agente que editasse o arquivo certo
  com conteúdo errado marcaria ponto. Que os seis tenham convergido para a mesma solução é
  evidência lateral, não o que foi medido.
- **Nada sobre generalização.** Uma tarefa, um repositório, um modelo, `R = 3`. É probe,
  não benchmark.
- **O `context.md` foi montado por quem formulou a hipótese.** Ameaça declarada no
  pré-registro: um B vencedor mede o melhor caso, não o produto. Por isso o resultado
  informativo desta fase seria o negativo — e ele não veio.
