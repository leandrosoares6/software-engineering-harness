# Encerramento

**Status: encerrado como produto em 2026-08-17.** Não foi abandonado no meio — três hipóteses foram
testadas até o fim, com pré-registro e critério de morte fixados antes de cada uma. As três
fecharam. Este documento é o registro do que ficou sabido.

Se você chegou aqui sem contexto, leia [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md) primeiro — ele conta o
que o projeto tentou ser, em linguagem simples e sem o vocabulário daqui.

---

## O que o projeto tentou

Reduzir o desperdício de LLM no desenvolvimento, movendo para código determinístico o trabalho que
não precisa de raciocínio: navegação de repositório, verificação, e operações de engenharia
repetidas.

Três teses foram testadas, nesta ordem. Cada uma foi a resposta ao fracasso da anterior.

## As três teses, e como cada uma fechou

### 1. Reuso de edição — *capabilities*

**Hipótese:** procedimentos recorrentes do projeto podem ser capturados uma vez e reexecutados sem
inferência.

**Veredito: morto por economia.** Varredura de campo em 654 commits, 15 meses, 5 autores: o
procedimento recorrente que existia recorreu **3 vezes em 5 meses**, sua parte mecânica eram
**4 linhas em 1242 inserções**, e os três primitivos que ele exigiria não existiam. Break-even em
anos.

A máquina foi construída e **funciona** — quatro gates, ancoragem em proveniência, edição que
preserva a fonte. O que a matou não foi defeito técnico, foi frequência.

Registro: [`PHASE0_FINDINGS.md`](PHASE0_FINDINGS.md), §2 do [PRD](CONTEXT_COMPILER_PRD.md).

### 2. Compilação de contexto — *Context Compiler*

**Hipótese:** entregar ao agente um pacote de contexto pequeno e ancorado evita que ele redescubra o
repositório.

**A metade positiva, e ela é real.** Seis sessões frias, pré-registro comitado antes da primeira:
**52 → 16 tool calls** de mediana, tokens caindo pela metade, limiar de ≤50% satisfeito com 30,8%. E
o achado qualitativo vale mais que a razão — os seis agentes convergiram para a **mesma solução**. O
pacote não comprou correção, comprou o **caminho até ela**.

**Veredito: mecanismo principal refutado.** O pacote da Fase 0 foi montado à mão por quem sabia a
resposta. Produzi-lo automaticamente exige achar o seed a partir do texto do pedido, e isso não
funciona: na classe que justifica o produto — pedido cujos termos não aparecem nos caminhos dos
arquivos — a captura foi **0,10 / 0,00 / 0,00** contra corte pré-registrado de 0,30, e a margem
sobre "olhe os 5 commits mais recentes" foi de 9,5 pp onde 15 eram exigidos. Onde o termo já aparece
no caminho, os três repositórios deram **0,25 idêntico**, que é `grep`.

E o corte foi sobre o **teto**: o prompt usado foi o assunto literal do commit-alvo. Pedido real é
paráfrase e casa pior.

Registro: [`../experiments/fase0/RESULT.md`](../experiments/fase0/RESULT.md),
[`../experiments/seed_retrieval/RESULT.md`](../experiments/seed_retrieval/RESULT.md).

### 3. Exposição de operações mecânicas

**Hipótese:** o agente desperdiça esforço em trabalho braçal que um language server faz exato —
renomear símbolo, mudar assinatura, achar referências.

**Veredito: a hipótese está certa e a posição está ocupada.** Serena expõe rename, move, inline,
safe delete e replace symbol body via LSP em 40+ linguagens. MCP Code Intelligence cobre change
signature em Java/Kotlin. RefactorMCP e roslyn-codelens-mcp cobrem extract method com preview em
diff. Os ganhos de token que o projeto queria capturar já estão publicados por terceiros: 30–84%
menos tokens, 5–34× em respostas estruturadas contra grep/read.

A única lacuna encontrada foi **verificação** — nenhuma delas aplica, verifica e reverte
atomicamente. O SEH tem isso construído e testado. É uma feature de uma semana para quem já tem o
resto, não uma posição.

**Esta checagem deveria ter sido a primeira coisa do projeto, e foi a última.** É a lição mais cara
daqui.

## O que ficou sabido, e é verdade

1. **Um pacote de contexto correto vale ~3× em exploração.** Medido, pré-registrado, com desvios
   declarados. É o resultado positivo do projeto e ele sobrevive ao encerramento.
2. **O valor está no caminho, não na resposta.** Os seis agentes chegaram à mesma solução; o pacote
   só encurtou o percurso.
3. **Reuso de procedimento não se paga na frequência real.** 3 eventos em 5 meses, 4 linhas em 1242.
4. **A oportunidade de recorrência é abundante e inútil sozinha.** Em repositório maduro, a fração
   dos arquivos de um commit que algum anterior já tocou tem mediana **1,00**. "Essa região já foi
   visitada?" é pergunta cuja resposta é quase sempre sim.
5. **Casamento lexical entre pedido e histórico é ruído.** A vantagem sobre "pegue os mais recentes"
   desaparece conforme K cresce, e chega a se inverter.

## O que é transferível, e vale mais que o produto

Estas lições não dependem do SEH ter dado certo, e nenhuma delas é óbvia antes de custar caro:

1. **Não peça que agentes se contem.** O auto-relato subnotificou até **44%** num arm e 0% em outro
   — viés **diferencial**, na direção que estreitaria a diferença medida. Quem benchmarka agente com
   auto-relato está publicando número errado e não sabe.
2. **Null model não é enfeite, é o que separa medir de se enganar.** Sem o `hot-k` e sem o
   `reachable`, este projeto teria reportado 79% e 0,25 como sucesso — duas vezes, e as duas erradas.
3. **Pré-registre a *previsão*, não só o limiar.** Foi a ordem prevista entre repositórios, e não o
   número, que revelou que o instrumento estava quebrado. Um limiar sozinho não teria pego.
4. **Meça o teto primeiro, com o melhor caso montado à mão.** Se o teto não paga, nenhuma engenharia
   salva — o resolver só pode se aproximar dele, nunca ultrapassá-lo.
5. **Um gate vale no máximo o que vale a referência contra a qual ele mede.** Uma capability passou
   quatro gates alegando algo que o commit aceito contradizia, porque a validação não lia os commits.
6. **Repetição é evento, não estrutura parecida.** E a forma temporal disso: commits consecutivos do
   mesmo trabalho não são recorrência.
7. **Quando a ferramenta não expressa parte da mudança aceita, a parte excluída é o achado.** Ajustar
   a referência para caber na ferramenta transforma limitação conhecida em alegação falsa, sem
   ninguém decidir mentir.
8. **Cheque o que já existe antes de construir.** Custou três teses aprender.

## O que fica utilizável no repositório

Nada aqui é abandonado por estar quebrado. A suíte passa (179 testes).

| peça | estado |
|---|---|
| `seh index` / `inspect` / `neighbors` | funciona; grafo AST em SQLite, só Python |
| `seh capability` (validate/install/run/capture/show) | funciona, testado; aplica, verifica e reverte atomicamente |
| `experiments/region_recurrence/measure.py` | roda em qualquer repo com `git log`; mede sobreposição de região com nulls |
| `experiments/seed_retrieval/measure.py` | roda em qualquer repo; mede se o texto do pedido acha o anterior certo |

Os dois scripts de medição não dependem de nada do SEH e continuam úteis isolados.

## O que reabriria isto

Uma coisa, e ela nunca rodou: o **repositório de campo**, cujos assuntos de commit são escritos em
português na linguagem do negócio — a propriedade que os três open source são fracos, e que o §5 do
PRD alega ser o mecanismo. A previsão registrada é que ele fique acima do gitea na classe difícil e
**não feche** a distância até 0,30.

```bash
python experiments/seed_retrieval/measure.py --repo /caminho/do/repo-de-campo
```

Para reabrir, precisaria de captura ≥ 0,30 na classe difícil **e** margem ≥ 15 pp sobre o recency-5,
mantendo o efeito em K = 3. O melhor dos três open source entregou 0,10 / +9,5 pp / 0,00.

## Nota final

O projeto não fracassou por execução. Cada tese foi construída até dar para medir, medida com
critério fixado antes, e encerrada quando o número disse para encerrar. Duas morreram por economia
real e uma por já estar ocupada.

O que ele produziu de mais sólido foram resultados negativos — e o método que os tornou confiáveis o
bastante para agir sobre eles.
