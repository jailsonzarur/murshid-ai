# Resumo Guiado — busca e geração

Continuação do `RESUMO-GUIADO.md` (passos 3b e 4) e do `PLANO-CHUNKING.md`, que já entregou
os chunks do livro embedados e ligados à matéria.

## O que já está pronto

- chunks do livro embedados, com `heading_path`, páginas e figuras vinculadas
- `subject_id` desnormalizado no chunk, então filtrar por matéria é índice, não join
- índice HNSW com distância de cosseno, validado
- `LectureModel.subject_id` liga a aula à matéria, logo à bibliografia

O SQL da busca é praticamente uma linha:

```sql
SELECT text, heading_path, page_start
FROM subject_document_chunks
WHERE subject_id = :materia
ORDER BY embedding <=> :vetor
LIMIT :k
```

## Decisões tomadas

**Os tópicos vêm do resumo, numa chamada só.** O resumo da aula já sai seccionado. Uma
única chamada lê o resumo e devolve os tópicos com suas queries.

**A query é o próprio texto da seção.** Busca vetorial não precisa de pergunta bem
formulada, precisa de texto parecido — e o que está indexado é heading mais corpo, o mesmo
formato. Só vale gerar query com LLM se a busca simples se mostrar ruim.

**Quantos trechos: os que passarem do limiar, com teto de 3.** Sem limiar a busca devolve
os K mais próximos mesmo quando nenhum tem a ver, e o modelo "embasa" a explicação em
material errado.

**Tópico sem trecho entra mesmo assim**, explicado a partir da aula, marcado como sem
respaldo na bibliografia. O aluno precisa distinguir o que foi verificado do que não foi.

**Convive com o resumo normal.** Campo novo `guided_summary`, não substitui. O resumo
normal é instantâneo e não depende de a matéria ter bibliografia.

**Sob demanda**, mesmo padrão do mapa mental: `guided_status`, claim atômico, botão.

**Enquadramento: "divergência encontrada", não "a professora errou".** Quando a recuperação
trouxer o trecho errado — e vai —, "divergência encontrada" continua sendo verdade. É o
risco 2 do `RESUMO-GUIADO.md`.

**Validar a recuperação antes de escrever prompt.** É o motivo de o `RESUMO-GUIADO.md`
separar os passos 3 e 4: se o resultado vier ruim, saber se o problema é a busca ou o
prompt.

## Citações inline

O objetivo é o que o NotebookLM faz: um badge no meio do texto que, ao ser clicado, abre o
trecho do livro.

Não tem mágica. Os trechos vão numerados para o prompt:

```
[1] Murray > Bactérias > Parede Celular (p. 287)
    "A parede celular das Gram-positivas..."
```

O modelo cita inline ao afirmar algo vindo dali:

```
A parede das Gram-positivas é espessa e rica em peptidoglicano [[1]].
```

O frontend acha os `[[n]]`, troca por badge, e ao clicar abre o painel com o trecho, o
`heading_path` e a página. O modelo só copia o número que recebeu — todo o trabalho de
resolver a referência é do lado de fora.

Três cuidados:

- **o modelo inventa número**: vai citar `[[7]]` com 5 trechos no contexto. Validar contra
  os números enviados e descartar os inválidos antes de gravar
- **o marcador tem que sobreviver ao markdown**: `[1]` seguido de parêntese vira link, por
  isso `[[n]]`
- **a numeração é por geração, não global**: reprocessar muda os números, então a tabela
  guarda a numeração junto

Bônus: os chunks já carregam figuras vinculadas. Se o trecho citado tiver figura, o painel
pode mostrar a imagem do livro junto.

## A tabela de auditoria é a tabela de citações

A auditoria pedida (query + trechos retornados) é exatamente o mapa de número → chunk que o
frontend precisa para resolver o badge.

```sql
CREATE TABLE lecture_guided_citations (
    id          uuid PRIMARY KEY,
    lecture_id  uuid NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    topic       text NOT NULL,
    query       text NOT NULL,
    results     jsonb NOT NULL,
    created_at  timestamptz NOT NULL
);
```

Uma linha por query. O `results` guarda todos os trechos retornados, inclusive os
rejeitados:

```json
[
  {"n": 1, "chunk_id": "...", "distance": 0.21, "heading_path": "...",
   "page_start": 287, "text": "...", "used": true},
  {"n": null, "chunk_id": "...", "distance": 0.61, "used": false}
]
```

Gravar também os que ficaram **abaixo** do limiar, com a distância. É o dado que permite
calibrar o threshold depois, olhando o que foi rejeitado e não deveria.

## As três alternativas a testar

Ordem de grandeza para uma aula de 1h com ~10 tópicos. Transcrição ~10 mil tokens, resumo
~5 mil, 3 trechos de livro por tópico.

### 1. Uma chamada só, com a transcrição — a primeira a implementar

```
system prompt + transcrição inteira + todos os tópicos + todos os trechos
→ 1 chamada,  ~26 mil tokens de entrada
```

Menos peça móvel: sem caching para acertar ordem de prefixo, sem orquestrar 10 chamadas,
sem tabela nova de chunks. Tem precedente direto — o `final_summary_agent` já lê a
transcrição inteira e devolve documento seccionado.

O modelo divide atenção entre 10 tópicos e 30 trechos.

### 2. Uma chamada por tópico, com o resumo

```
prefixo (cacheado):  system prompt + resumo inteiro
por chamada:         o tópico + seus trechos do livro
→ 10 chamadas
```

Cada tópico com atenção inteira, rodando em paralelo. O prefixo repetido ativa caching.

**Perde as palavras da professora**: o resumo já filtrou. Se ela disse algo que o resumo
cortou e o livro contradiz, a divergência passa batido.

### 3. Como a 2, mais RAG na transcrição

```
prefixo (cacheado):  system prompt
por chamada:         o tópico + trecho do livro + trecho da transcrição
→ 10 chamadas
```

Cada tópico recebe os dois lados. Embedar a transcrição custa ~$0,0002 e ocupa 129 KB.

Em aberto: tabela `lecture_chunks` separada (misturar polui a busca no livro); chunking por
tamanho, já que transcrição não tem estrutura tipográfica; **não citar literalmente**,
porque é o texto sujo do Whisper — "carocitar os patóticos" exibido cru destrói a confiança
no material; e duas buscas para depurar em vez de uma.

## Custo não é o critério

| | entrada | custo aproximado |
|---|---|---|
| 1 | ~26 mil tokens | ~$0,015 |
| 2 | ~24 mil (com cache) | ~$0,015 |
| 3 | ~20 mil | ~$0,014 |

As três caem na mesma faixa, em torno de 35% do custo atual de uma aula ($0,0398). **O que
separa as alternativas é qualidade, não preço.**

## Prompt caching

Automático, sem configuração, a partir de 1.024 tokens de prefixo. Desconto documentado
entre 50% e 90%, conforme o modelo.

- **a ordem importa**: o que se repete vem primeiro; o específico do tópico, por último
- **não disparar as 10 em paralelo**: a primeira precisa terminar para popular o cache
- **o cache dura 5 a 10 minutos**, folgado para o nosso caso

Ressalva: os números são documentados para a família GPT-4o. Não foi confirmado que o
`gpt-5.6-luna` tem o mesmo desconto — a resposta da API traz `cached_tokens` no `usage`.

---

# Plano de implementação — alternativa 1

Espelha o fluxo do mapa mental, que já está em produção e testado: um campo de conteúdo,
um campo de status com claim atômico, uma task na fila `summaries`, uma rota `POST`, e um
botão com polling no frontend.

## Medições que fundamentam

Feitas contra a matéria "Microbiologia" (Murray 3.094 chunks + Tortora 3.235) usando as 9
seções reais do resumo da aula Teste 33 como consulta.

| | distância |
|---|---|
| 9 seções de microbiologia | 0,1598 – 0,3251 |
| 7 seções de imunologia | 0,1921 – 0,2731 |
| 3 controles fora do domínio | 0,5913 – 0,6343 |

Todas as 9 recuperaram material correto, conferido por conteúdo e não por distância. O vão
entre coberto e não coberto é de 0,2662.

**Limiar: 0,45.** Fica no meio do vão, com 0,12 de folga para cada lado.

Ressalva: os controles fora do domínio são textos sintéticos, escritos por falta de seção
real de outro assunto. O piso de 0,59 é estimativa, não medição de dado real.

## Passo 1 — Schema

Na `LectureModel`, espelhando `mindmap_data` / `mindmap_status`:

```
guided_summary   text, nullable
guided_status    NONE | REQUESTED | PROCESSING | DONE | FAILED
```

A tabela de citações, que é também a auditoria:

```sql
CREATE TABLE lecture_guided_citations (
    id          uuid PRIMARY KEY,
    lecture_id  uuid NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    topic       text NOT NULL,
    query       text NOT NULL,
    results     jsonb NOT NULL,
    created_at  timestamptz NOT NULL
);
```

Índice em `lecture_id`. Regerar apaga as linhas da aula antes de inserir, como o
`clear_document_index_sync` faz com os chunks.

## Passo 2 — Repository

Em `lectures/repository.py`, no mesmo formato de `claim_lecture_mindmap`:

```python
async def claim_lecture_guided_summary(db, lecture_id) -> bool
def set_lecture_guided_status_sync(db, lecture_id, value) -> None
def clear_guided_citations_sync(db, lecture_id) -> None
def add_guided_citation_sync(db, citation) -> None
```

A busca vetorial já existe: `search_subject_chunks_sync` em `subjects/repository.py`.

## Passo 3 — Agente dos tópicos

`lectures/ai/guided_topics_agent.py`, no padrão de saída estruturada do
`mindmap_tree_agent`. Lê o resumo, devolve por tópico:

```
titulo    o título da seção
query     o texto da seção, que é o que vai ser embedado
ancora    uma frase literal da transcrição onde o tópico começa
```

A `ancora` não é usada na alternativa 1. Fica gravada porque, se a alternativa 3 for
implementada, ela já existe e não exige reprocessar nada.

Modelo e reasoning por env, como os outros agentes.

## Passo 4 — Agente do resumo guiado

`lectures/ai/guided_summary_agent.py`. Recebe transcrição, tópicos e trechos numerados;
devolve markdown com `[[n]]`.

O prompt precisa carregar:

- citar inline ao afirmar algo vindo de um trecho
- separar o que a aula disse do que o livro diz
- ao divergirem, apresentar como **divergência encontrada** com os dois lados, sem arbitrar
- tópico sem trecho: explicar a partir da aula e marcar como não verificado

## Passo 5 — Serviço

Em `lecture_service.py`, espelhando `request_mindmap` / `generate_mindmap`:

```python
async def request_guided_summary(db, lecture_id, user_id) -> None
def generate_guided_summary(lecture_id) -> None      # com stage()
```

Guardas do `request`, na ordem do mapa mental:

1. aula não é do usuário → 404
2. `guided_summary` já existe → retorna sem fazer nada
3. sem `summary` → 400, "O resumo da aula ainda não está pronto."
4. sem `subject_id` → 400, "A aula precisa de uma matéria com bibliografia."
5. claim atômico; se não ganhou, retorna

O corpo da geração:

```
resumo → agente de tópicos → embeda as queries em lote
       → busca por tópico, teto de 3 acima do limiar
       → grava as citações, inclusive as rejeitadas com a distância
       → monta o contexto numerado
       → agente do resumo guiado
       → valida os [[n]] contra os números enviados
       → grava guided_summary e marca DONE
```

Uma task só, como o mapa mental. São duas chamadas de LLM mais um lote de embeddings,
sequenciais e da ordem de dois minutos — bem dentro do `task_soft_time_limit` de 5400s.

Fechar os mesmos buracos do mapa mental: saída vazia marca `FAILED`, exceção marca `FAILED`
e propaga, e sair cedo porque já existe marca `DONE` — senão o status fica preso em
`REQUESTED` e o spinner não sai.

## Passo 6 — Task e rota

```python
@celery_app.task(name="generate_lecture_guided_summary_task")   # fila summaries
```

`POST /lectures/{lecture_id}/guided-summary`, status 202, `SuccessResponse[None]`. O
cliente já sabe lidar com `data: null` desde a correção do `allowNullData`.

## Passo 7 — Frontend

Mesmo desenho do mapa mental:

```js
const isBuildingGuided = lecture?.guided_status === 'REQUESTED'
```

Botão sob demanda, update otimista para `REQUESTED`, polling de 3s enquanto estiver nesse
estado, e `FAILED` devolve o botão com a mensagem. O `guided_status` entra no
`LectureDetailSchema`.

Renderizador que troca `[[n]]` por badge, com painel lateral mostrando trecho,
`heading_path`, página e a figura quando houver.

## Verificação

- custo real no `usage`, incluindo `cached_tokens`
- a auditoria permite reler, para cada tópico, o que foi recuperado e o que foi rejeitado
- leitura do resultado na Teste 33, que é a aula já validada na recuperação

## Pendência conhecida

O `heading_path` do Tortora melhorou com o filtro de mobília, mas ainda mistura título de
box lateral com título de capítulo no mesmo tamanho de fonte. A citação vai nomear um
assunto plausível, nem sempre o capítulo correto. Reindexar o Tortora aplica o filtro já
implementado; separar box de capítulo é trabalho adicional ainda não feito.
