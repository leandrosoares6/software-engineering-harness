# Recuperação de seed — pré-registro

**Status:** fixado antes de escrever o script e antes de qualquer execução.
**Antecedente:** [`../region_recurrence/OSS_RESULT.md`](../region_recurrence/OSS_RESULT.md), que
falhou como instrumento e apontou este experimento como a correção.
**Mede:** o §10.2 do [PRD](../../docs/CONTEXT_COMPILER_PRD.md) — o mecanismo principal do produto.

---

## Por que este experimento é o decisivo

A Fase 0.5 mediu que `reachable` tem mediana **1,00**: quase todo arquivo de quase todo commit já
foi tocado antes. A oportunidade é abundante, e por isso não é o gargalo.

Sobra uma pergunta, e todo o risco do produto está nela:

> **O texto do pedido permite achar qual visita anterior importa?**

Se sim, a Fase 1 é execução com risco conhecido. Se não, o Seed Resolver por histórico Git está
morto, e com ele o Context Compiler como desenhado.

## O desenho

Para cada commit-alvo `A` elegível:

1. **prompt** = o assunto literal de `A`;
2. **pool** = commits anteriores a `A`, fora do cooldown — o índice nunca vê `A` nem nada posterior
   (controle de vazamento do §15);
3. **ranqueia** o pool por similaridade lexical entre o assunto do prompt e o assunto do anterior;
4. **top-K** entra no pacote hipotético;
5. **mede** quanto da região de `A` o melhor desses K cobre.

### Por que o assunto literal, e não uma paráfrase

De propósito, e é o mesmo movimento da Fase 0: **isto mede o teto.** Um pedido real é paráfrase e
casa pior que o texto original. Se o teto já falhar, nenhuma paráfrase salva, e o §10.2 morre sem
precisar ser implementado.

Um teto que passa **não** é o produto — é licença para construir e medir de verdade.

## A divisão que decide de verdade: caso fácil e caso difícil

Fixada antes de rodar, porque sem ela o experimento se auto-engana.

O §5 do PRD justifica o produto com um caso específico: *"Renovação de licença caindo em CNH"* onde
nenhum termo do prompt aparece nos identificadores. Se o mecanismo só funcionar quando o termo do
prompt **está** no caminho do arquivo, o produto é um `grep` com passos extras.

Cada alvo é classificado, deterministicamente, antes de qualquer estatística:

| classe | definição |
|---|---|
| **fácil** | algum termo do assunto de `A` aparece em algum caminho de arquivo de `A` |
| **difícil** | nenhum termo aparece — a tradução domínio→código é obrigatória |

**As duas classes são reportadas separadamente, e a classe difícil é a que decide o produto.** Um
resultado bom só no fácil é lido como resultado negativo.

## Parâmetros, fixados

- **K decisivo = 5.** Sensibilidade reportada em K = 1, 3, 10.
- **Alvos:** ≥ 4 arquivos e ≤ 50 arquivos. O corte inferior vem do defeito da Fase 0.5 — alvo de 1
  arquivo acerta por construção e era 39% da amostra.
- **Cooldown 30 dias**, mesmo valor e mesmo motivo da Fase 0.5: commit de acompanhamento casa
  lexicalmente com o que ele acompanha, e isso não é recuperação.
- **Elegibilidade e filtro de caminho idênticos** aos da Fase 0.5 — o script importa as funções, em
  vez de reimplementá-las, para que os números sejam comparáveis.
- `--seed 0`.

### Normalização e ranqueamento, declarados

Tokenização do assunto: minúsculas, remoção de acentos por NFKD, corte em não-alfanumérico,
descarte de tokens com menos de 3 caracteres.

Descartados como ruído, porque casam com tudo e não carregam domínio:

- prefixos de conventional commit: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`,
  `build`, `ci`, `style`, `revert`;
- tags de projeto observadas nos repositórios da amostra: `maint`, `mnt`, `enh`, `tst`, `bug`,
  `doc`, `mrg`, `api`, `wip`;
- números de PR (`#12345`);
- stopwords curtas de português e inglês.

**Ranqueamento primário: sobreposição ponderada por IDF**, com o IDF calculado **apenas sobre o
prefixo** — sem olhar o futuro. Termo raro carrega sinal; `add`, `update` e `remove` não carregam.

**Ranqueamento secundário, também pré-registrado: contagem simples de termos em comum.** Reportado
junto, para que se saiba se o IDF fez diferença ou se é enfeite.

## As referências

| referência | o que é |
|---|---|
| **oráculo** | máximo sobre **todos** os anteriores elegíveis. É o teto da Fase 0.5, ~1,00 |
| **recency-K** | os K anteriores mais recentes. Se "olhe os últimos 5 commits" empata, o resolver é inútil |
| **random-K** | K anteriores sorteados. O piso |

O `recency-K` é o null que mais importa aqui, e é novo. Ele é a versão barata do produto: não
precisa de índice, de prompt, nem de nada.

## A grandeza primária

```text
captura = containment(top-K) ÷ containment(oráculo)
```

Quanto da oportunidade disponível a recuperação lexical realmente captura. Reportada como mediana,
separada por classe fácil/difícil.

## Os limiares, fixados agora

Sobre a **classe difícil**, K = 5, cooldown 30:

| mediana da captura | margem sobre recency-K e random-K | leitura |
|---|---|---|
| **≥ 0,60** | **≥ 15 pp** | o mecanismo funciona. Funda a Fase 1 |
| 0,30 – 0,60 | ≥ 15 pp | fraco. Só justifica seguir se a classe difícil for pequena no repositório de campo |
| **< 0,30** | qualquer | **§10.2 morto** |
| qualquer | **< 15 pp** | **§10.2 morto** — não separa do "olhe os últimos commits" |

Piso: o resultado tem que se manter em K = 3. Um efeito que só existe em K = 10 é o pacote
inteiro virando lista de tudo.

## A previsão, escrita antes de rodar

**Entre os três open source:**

```text
home-assistant  >  gitea  >  scikit-learn
```

Razões, para que a previsão seja falsificável e não só um chute:

- **home-assistant** deve vencer por um motivo que é meio armadilha: o assunto quase sempre nomeia a
  integração (`Tuya`, `MQTT`, `unifiprotect`), e o nome da integração **é o nome do diretório**.
  Isso é casamento de identificador, o caso fácil do §10.1 — não a tradução que justifica o produto.
  Por isso a divisão fácil/difícil existe, e por isso espero que a vantagem do home-assistant
  **desapareça na classe difícil**;
- **gitea** tem assunto que descreve feature em linguagem de produto (`Store webhook event in
  database`), que é o caso alvo;
- **scikit-learn** deve ir pior: assunto dominado por tag e por vocabulário de API
  (`MAINT Clean up deprecations for 1.5`), com pouca linguagem de domínio.

**Sobre o repositório de campo**, que não roda aqui: previsto **acima do gitea na classe difícil**,
porque tem assunto em português na linguagem do negócio, que é a propriedade que o §5 alega ser o
mecanismo. Esta é a previsão que mais interessa e a única que testa a hipótese central do PRD.

**Previsão adicional, sobre a forma do resultado:** espero que a classe difícil seja uma minoria dos
alvos nos três repositórios open source. Se ela for menor que 15% da amostra, a estatística
principal fica ruidosa e isso precisa ser dito no resultado em vez de escondido.

## Ameaças declaradas

1. **O assunto literal é otimista.** Declarado acima: mede o teto, não o produto.
2. **A classificação fácil/difícil é lexical e grosseira.** Um assunto que diz "checkout" e um
   arquivo chamado `checkout.py` caem em "fácil" mesmo que a mudança real esteja em `pricing.py`.
   Isso empurra alvos para a classe fácil e **encolhe** a classe difícil. Direção: conservadora
   para a classe que decide, mas reduz a amostra dela.
3. **Assunto de squash merge concentra várias intenções**, o que ajuda o casamento lexical
   artificialmente. Direção: otimista. Sem controle nesta rodada; registrado.
4. **A previsão foi escrita por quem formulou a hipótese.** Mesma ameaça da Fase 0 e da Fase 0.5. A
   proteção é ser falsificável e estar escrita antes — na Fase 0.5 foi ela que impediu ler 79% como
   sucesso.
5. **Três repositórios não são amostra.** Servem para testar o mecanismo, não para generalizar.

## Ordem de execução

1. Comitar este arquivo.
2. Escrever `measure.py`, importando elegibilidade e parsing da Fase 0.5.
3. Rodar nos três open source. Reportar em `RESULT.md`, sem editar este arquivo.
4. O repositório de campo é rodado pelo autor, com o mesmo script e os mesmos parâmetros.
