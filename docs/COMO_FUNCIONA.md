# Como funciona, em linguagem simples

Este documento existe porque o resto da pasta `docs/` não é legível sem contexto. Os outros
arquivos usam vocabulário próprio, criado para separar coisas que estavam sendo confundidas —
precisão que cobra caro na leitura, principalmente ao voltar ao projeto depois de um tempo.

Aqui não tem nenhum termo do projeto. Só a história, com um caso fictício, assumindo que tudo
funciona. Os termos aparecem no final, num decoder.

> **Nada aqui é promessa de resultado.** O cenário abaixo é o produto funcionando. O que já foi
> medido, e o que continua em aberto, está em [O que é verdade hoje](#o-que-é-verdade-hoje), no fim.

---

## O time e o problema

Um app de delivery. Backend em Python, frontend em React. Cinco pessoas, dois anos de código.

**Hoje, sem a ferramenta.** Você pede pro agente: *"cliente com plano assinante tem que ter frete
grátis no checkout"*.

O agente faz o que qualquer um faria: procura por "frete". Acha uma pasta `shipping/`, lê três
arquivos, entende que ali só se calcula distância. Procura "assinante", acha o módulo de planos,
lê mais quatro arquivos. Tenta editar `shipping/calculator.py` — lugar errado. Volta, procura
"checkout", lê o fluxo inteiro. Uns 40 comandos depois, descobre que desconto de frete não mora em
nenhum desses lugares: mora em `checkout/pricing.py`, numa função chamada `apply_discounts`.

Ninguém adivinharia isso pela palavra "frete". O código está em inglês, pensado por preço; o
pedido está em português, pensado por entrega.

Aí ele começa a trabalhar de verdade — com metade da janela de contexto já gasta lendo arquivo que
não interessava.

## O que a ferramenta é, em uma frase

**Um caderninho que o repositório escreve sobre si mesmo, sozinho, toda vez que um trabalho é
aceito.**

Não é documentação — ninguém escreve. Não é busca — não procura na hora. É anotação prévia.

## Cena 1 — janeiro, o caderno aprende

Alguém do time entrega uma tarefa diferente: *"cupom de desconto no checkout"*. Faz o PR, é
revisado, é mergeado. Trabalho normal, ninguém fez nada de especial.

No merge, a ferramenta anota sozinha:

```text
Registro anotado: "cupom de desconto no checkout"
  api/promotions/models.py           → Coupon, CouponRule
  api/checkout/pricing.py:214        → apply_discounts
  web/src/checkout/OrderSummary.tsx  → OrderSummary
  tests/test_pricing.py              → test_discount_applied
```

Custo: zero. Ninguém digitou isso. A ferramenta olhou o que o commit mudou e anotou os arquivos, as
funções e o título que o desenvolvedor já tinha escrito em português.

Isso se repete a cada merge. Em três meses o caderno tem umas 80 anotações.

## Cena 2 — abril, o caderno é usado

Volta o pedido do frete grátis. Agora o agente roda um comando antes de começar:

```bash
seh compile "cliente assinante tem que ter frete grátis no checkout"
```

E recebe um papel de meia página:

```markdown
# Tarefa
cliente assinante tem que ter frete grátis no checkout

## Por onde começar
- api/checkout/pricing.py:214 → apply_discounts()
  porque: em janeiro, "cupom de desconto no checkout" mexeu exatamente aqui
- web/src/checkout/OrderSummary.tsx → OrderSummary
  porque: mesma mudança de janeiro
- tests/test_pricing.py → test_discount_applied
  porque: é o teste que cobre essa função

## Também pode importar
- api/plans/models.py → Subscription
  porque: é onde "assinante" existe no código

## Não encontrei
- "frete grátis" não aparece em nenhum lugar do código

## Este papel vale para o commit 7b3e9a2
```

O agente lê isso e vai direto pro `pricing.py`. Não procurou "frete". Não leu `shipping/`.

## O pulo do gato

**A tarefa de abril não é a mesma de janeiro.** Cupom e frete grátis são coisas diferentes,
escritas por pessoas diferentes, com regras diferentes.

Mas **é o mesmo bairro do código**. E é isso que a ferramenta aposta: não que o trabalho se repita,
mas que ele **caia perto de onde alguém já esteve**.

Essa é a diferença entre isto e a versão anterior do projeto. A antiga tentava guardar *a receita* —
e receita idêntica se repete raríssimo, foi o que a medição de campo mostrou. Esta guarda só *o
endereço*. Endereço se repete muito mais.

Se essa aposta está certa é a pergunta que ainda não tem resposta, e está medida em
[`experiments/region_recurrence/`](../experiments/region_recurrence/README.md).

## As quatro coisas que ela não faz

- **Não escreve o código.** Diz onde, não o quê. A regra do frete grátis é sua.
- **Não garante que está certo.** Ela acerta o bairro; errar a casa ainda é possível.
- **Não substitui o repositório.** O agente continua com acesso total ao código. O papel é um chute
  bom, não uma cerca — se o chute estiver errado, ele procura como sempre procurou.
- **Não envelhece calada.** Se alguém mover o `pricing.py`, a anotação avisa que está velha e se
  recusa a valer. Uma anotação errada é pior que anotação nenhuma, então ela falha alto.

## O que é verdade hoje

Separado de propósito, porque o cenário acima é o produto pronto e o projeto não está lá.

**Já medido, e positivo.** Numa tarefa real, num repositório real, com o papel montado à mão: o
agente saiu de **52 comandos para 16** antes de chegar ao lugar certo, e os tokens caíram pela
metade. Seis sessões, três de cada lado.

Teve um detalhe que vale mais que o número: **os dois lados chegaram na mesma solução**. O papel não
deixou o agente mais inteligente. Deixou ele mais inteligente *mais cedo*, porque não gastou meia
janela de contexto se localizando.

**Já medido, e negativo.** A versão anterior do projeto — guardar a receita em vez do endereço — não
se paga. Numa varredura de 654 commits ao longo de 15 meses, o procedimento repetido que existia
recorreu 3 vezes em 5 meses, e a parte mecânica dele eram 4 linhas em 1242. Anos para se pagar.

**Medido depois, e é o que encerrou o projeto.** As duas perguntas que faltavam foram respondidas:

1. *Com que frequência uma tarefa nova cai num bairro já visitado?* **Quase sempre** — e por isso a
   pergunta não ajuda. Em repositório maduro, praticamente todo arquivo já foi tocado antes.
2. *O programa acha a anotação certa a partir do pedido?* **Não.** Quando os termos do pedido não
   aparecem nos nomes dos arquivos — que é justamente o caso que justifica a ferramenta existir — ele
   erra quase sempre. Quando aparecem, ele acerta um pouco, mas aí `grep` faz igual.

O número de 52 → 16 era **o melhor caso possível**, com o papel montado à mão por quem já sabia a
resposta. Ele continua verdadeiro, e continua sendo um teto que ninguém conseguiu alcançar
automaticamente.

O projeto foi encerrado como produto. O registro completo está em
[`ENCERRAMENTO.md`](ENCERRAMENTO.md), e a Cena 2 acima continua valendo como descrição do que teria
sido — não do que existe.

---

## Decoder do vocabulário

Ao topar com esses termos no resto da `docs/`:

| o que o projeto escreve | o que quer dizer |
|---|---|
| *context package*, `context.md` | o papel de meia página da Cena 2 |
| *registro de caminho* | a anotação da Cena 1 |
| *seed* | o primeiro arquivo certo, o ponto de partida |
| *Seed Resolver* | a parte que casa o pedido em português com a anotação certa |
| *containment*, recorrência de região | quanto do "bairro" da tarefa nova já tinha sido visitado |
| *proveniência* | o papel saber de qual versão do código veio, e recusar se mudou |
| *staleness* | o papel estar velho porque o código mudou embaixo dele |
| *capability* | a ideia antiga de guardar a receita, abandonada por medição |
| *gate* | uma verificação que precisa passar, senão o trabalho é recusado |
| *Fase 0* | o experimento que mediu 52 → 16 |
| *pré-registro* | fixar o critério de sucesso por escrito **antes** de rodar, para não ler o resultado depois e chamar de vitória |
| *oráculo* | a regra automática que decide se a tarefa foi cumprida, sem humano opinando |
| *arm A / arm B* | os dois grupos de um experimento: sem tratamento e com tratamento |
| *null model* | uma alternativa boba de comparação. Se a coisa cara não vence a boba, ela não vale |

## Onde ler o resto

| documento | o que é |
|---|---|
| [`CONTEXT_COMPILER_PRD.md`](CONTEXT_COMPILER_PRD.md) | o produto atual, com o que foi medido separado do que é suposição |
| [`../experiments/fase0/RESULT.md`](../experiments/fase0/RESULT.md) | o experimento do 52 → 16, com os desvios declarados |
| [`../experiments/region_recurrence/README.md`](../experiments/region_recurrence/README.md) | a próxima medição, com os limiares já fixados |
| [`PHASE0_FINDINGS.md`](PHASE0_FINDINGS.md) | lições da versão antiga que continuam valendo |
| [`ROADMAP.md`](ROADMAP.md) | histórico. Está marcado como superado, e está mesmo |
