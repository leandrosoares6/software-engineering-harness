# Recuperação de seed — resultado

Pré-registro: [`PRE_REGISTRATION.md`](PRE_REGISTRATION.md), comitado em `67adf31` **antes** de o
script existir.

## Veredito

**§10.2 do PRD está morto.** O Seed Resolver por histórico Git não recupera o seed certo a partir do
texto do pedido, nos três repositórios, pelos dois critérios pré-registrados, com folga.

E o corte é sobre o **teto**: o prompt usado foi o assunto literal do commit-alvo. Um pedido real é
paráfrase e casa pior.

## Os números

Classe difícil, K = 5, ranqueamento IDF, cooldown 30 dias.

| repositório | classe difícil | oráculo | top-5 | **captura** | recency-5 | **margem** |
|---|---|---|---|---|---|---|
| go-gitea/gitea | 1.238 (32,7%) | 0,50 | 0,04 | **0,10** | 0,00 | **+9,5 pp** |
| scikit-learn | 1.169 (45,3%) | 0,50 | 0,00 | **0,00** | 0,00 | **+0,0 pp** |
| home-assistant | 1.422 (14,0%) | 0,40 | 0,00 | **0,00** | 0,00 | **+0,0 pp** |

Limiares pré-registrados: captura `< 0,30` **ou** margem `< 15 pp` sobre o recency-K ⇒ morto.
**Os três disparam os dois.**

O piso também falha: o pré-registro exigia que o efeito se mantivesse em K = 3, e em K = 3 a captura
é **0,00 nos três**. Só em K = 10 o gitea chega a 0,25 e o scikit-learn a 0,20 — ainda abaixo do
corte, e com K = 10 o "pacote de contexto" já é uma lista de dez mudanças anteriores, que é o
problema que ele deveria resolver.

### A oportunidade existe. A recuperação é que não.

O oráculo na classe difícil é **0,40 a 0,50**: existe, sim, um commit anterior que cobre metade da
região do alvo. A Fase 0.5 já tinha dito isso. O que este experimento acrescenta é que **o texto do
pedido não permite achá-lo** — 10% dessa oportunidade no melhor repositório, 0% nos outros dois.

## A assinatura de "o produto é um grep"

Ela estava pré-registrada como o desfecho a temer, e é exatamente o que apareceu:

| repositório | captura, classe **fácil** | captura, classe **difícil** |
|---|---|---|
| gitea | **0,25** | 0,10 |
| scikit-learn | **0,25** | 0,00 |
| home-assistant | **0,25** | 0,00 |

Idênticos os três na classe fácil, zerados na difícil. O mecanismo funciona **apenas** quando um
termo do pedido já aparece no caminho do arquivo — que é o §10.1, casamento de identificador, e é o
que `grep` faz sem índice, sem grafo e sem produto.

O §5 do PRD justifica o Context Compiler com o caso oposto: *"Renovação de licença caindo em CNH"*,
onde nenhum termo do prompt aparece no código. **É precisamente o caso que não funciona.**

## A previsão: ordem errada, razão certa

Previsto: `home-assistant > gitea > scikit-learn`.
Observado: `gitea > scikit-learn ≈ home-assistant`, com os dois últimos em zero.

A ordem errou. Mas a **sub-previsão registrada junto acertou**, e ela era a que importava:

> *"espero que a vantagem do home-assistant desapareça na classe difícil, porque o nome da
> integração é o nome do diretório"*

O home-assistant tem a **maior classe fácil dos três (86%)** e a menor classe difícil (14%), e sua
captura na classe difícil é zero. A vantagem prevista era casamento de identificador, ela existe, e
ela some exatamente onde deveria sumir. A divisão fácil/difícil — a decisão de desenho que quase não
entrou — é o que tornou isso visível em vez de virar um número alto e falso.

## O qualitativo, que refina o diagnóstico

**Onde funcionou** (gitea, classe difícil): são casos genuínos.

- `Remove redundant Unix timestamp method call` ← `#2302 Replace time.Time with Unix Timestamp`
- `Add rebase with merge commit merge style` ← `Add Pull Request merge options`
- `Fix the bug when getting files changed for pull_request` ← `Support pull_request_target event`

O mecanismo não é aleatório. Quando o vocabulário do domínio se repete entre dois assuntos, ele
acha. Só que isso é raro o bastante para a mediana ser 0,10.

**Onde falhou:** as falhas não são aleatórias, e isso é um achado.

- `Enforce trailing comma in JS on multiline` — 47 arquivos
- `Use querySelector over alternative DOM methods` — 46 arquivos
- `enable staticcheck QFxxxx rules` — 46 arquivos
- `migrate from com.* to alternatives` — 46 arquivos

São **varreduras transversais**: mudanças mecânicas sobre dezenas de arquivos que não têm região
nenhuma. Nenhuma recuperação as acha, porque não há o que achar — e o oráculo delas também é baixo
(0,07 a 0,44).

**Observação pós-hoc, declarada como tal:** a classe difícil mistura duas coisas — tradução
domínio→código genuína, e varredura sem região. A segunda puxa a mediana para baixo. Isso **não
reverte o veredito**: a distância até o corte de 0,30 é grande, e em K = 3 a captura é zero mesmo
no gitea. Mas registra que uma fatia melhor da classe difícil existiria, e que testá-la exigiria
**novo pré-registro** — não reanálise em cima deste resultado.

## O que isto mata, e o que sobrevive

**Morto:**

- §10.2, o mecanismo principal do PRD;
- o Seed Resolver determinístico, e com ele o Context Compiler **como desenhado**;
- a Fase 1 do §16, que não deve ser construída.

**Vivo, e não é pouco:**

- **O resultado da Fase 0 continua de pé.** Um pacote de contexto *correto* corta exploração em ~3×
  (52 → 16 tool calls), e os seis agentes convergiram para a mesma solução. O valor é real e está
  medido.

O que este experimento mostra é que **não existe caminho determinístico barato até aquele pacote**.
O valor existe; o atalho não.

## A consequência estratégica, que o §20 torna desconfortável

Se o pacote vale e a rota determinística não chega nele, sobram três rotas — e o §20 do PRD
**proíbe as duas primeiras por decisão de escopo**:

| rota | status no PRD |
|---|---|
| LLM interpreta a task e escolhe o seed | §20: *"não usaremos LLM para interpretar a task"* |
| embeddings como mecanismo principal | §20: *"não usaremos embeddings como mecanismo principal"* |
| humano escreve o pacote | não é ferramenta; é convenção de time |

A medição não diz que o §20 estava errado. Diz que **as exclusões dele eliminaram o espaço de
soluções que restou**, e que manter as duas primeiras proibições equivale a encerrar o produto.

E há a consequência que fecha o círculo com a pergunta que abriu esta linha de trabalho: uma vez
admitidos LLM ou embeddings na recuperação, o que se está construindo é o que Aider, Cursor e Cody
já fazem. O desconforto inicial — *"existem libs que já fazem isso"* — estava certo, e agora tem
evidência em vez de intuição.

## Reprodução

```bash
git clone --filter=blob:none --no-checkout https://github.com/go-gitea/gitea.git
python experiments/seed_retrieval/measure.py --repo ./gitea
```

8s (gitea), 12s (scikit-learn), 39s (home-assistant, com `--since="4 years ago"`).
Parâmetros idênticos aos do pré-registro em todas as rodadas.

## Rodar no repositório de campo ainda vale

A previsão registrada é que ele fique **acima do gitea na classe difícil**, por ter assunto em
português na linguagem do negócio — a propriedade que o §5 alega ser o mecanismo. Os três open
source são fracos justamente nessa propriedade.

É a única forma de o veredito mudar, a previsão está escrita, e custa um comando:

```bash
python experiments/seed_retrieval/measure.py --repo /caminho/do/repo-de-campo
```

Para reverter, ele precisaria de captura `≥ 0,30` na classe difícil **e** margem `≥ 15 pp` sobre o
recency-5, com o efeito se mantendo em K = 3. O gitea, melhor dos três, entregou 0,10 / +9,5 pp /
0,00. A distância é grande, e a previsão honesta é que o repositório de campo a reduza sem fechá-la.
