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

## Passo 1 — Busca isolada e validação

Antes de qualquer prompt. É o passo 3b do `RESUMO-GUIADO.md`.

**Repository**, em `subjects/repository.py`:

```python
def search_subject_chunks_sync(
    db, subject_id, embedding, *, limit=3, max_distance
) -> list[tuple[SubjectDocumentChunkModel, float]]
```

Devolve o chunk e a distância, ordenado, já filtrado por matéria. O limiar fica no
chamador, para a auditoria conseguir gravar também os rejeitados.

**Comando de validação**, nos moldes do `make inspect`:

```
make search subject="Teste 1" q="fagocitose por neutrófilos"
```

Imprime os trechos com distância, `heading_path` e página. É o que permite calibrar o
limiar olhando resultado real antes de escrever prompt.

**Critério para seguir:** rodar 10 consultas tiradas de um resumo real e conferir na mão se
os trechos do Murray fazem sentido. Se não fizerem, o problema é a recuperação, e nenhum
prompt conserta.

## Passo 2 — Schema

Na `LectureModel`:

```
guided_summary   text, nullable
guided_status    NONE | REQUESTED | PROCESSING | DONE | FAILED
```

Mais a tabela `lecture_guided_citations` descrita acima.

## Passo 3 — Agente dos tópicos

`lectures/ai/guided_topics_agent.py`. Lê o resumo, devolve tópicos com query, em saída
estruturada — mesmo padrão de `json_schema` que o `mindmap_tree_agent` já usa.

Pedir junto uma frase literal da transcrição onde o tópico começa. Não é usada na
alternativa 1, mas fica gravada: se um dia a alternativa 3 for implementada, a âncora já
existe e não precisa reprocessar.

## Passo 4 — Agente do resumo guiado

`lectures/ai/guided_summary_agent.py`. Recebe transcrição, tópicos e trechos numerados;
devolve markdown com `[[n]]`.

O prompt precisa carregar:

- citar inline ao afirmar algo vindo de um trecho
- separar o que a aula disse do que o livro diz
- quando divergirem, apresentar como **divergência encontrada** com os dois lados, sem
  arbitrar
- tópico sem trecho: explicar a partir da aula e marcar como não verificado

## Passo 5 — Serviço e task

Orquestra: lê resumo → tópicos → embeda queries → busca → monta contexto numerado → chama
o agente → **valida os `[[n]]` contra os números enviados** → grava resumo e citações.

Task na fila `summaries`, claim atômico em `guided_status`, rota `POST
/lectures/{id}/guided-summary`. Mesmo desenho do mapa mental, que já está testado.

## Passo 6 — Frontend

Botão sob demanda, polling por `guided_status`, e o renderizador que troca `[[n]]` por
badge com painel lateral. O painel mostra trecho, `heading_path`, página e a figura quando
houver.

## Verificação

Custo real medido no `usage`, incluindo `cached_tokens` para confirmar se o caching vale no
luna. E a leitura do resultado numa aula real do Murray — se a alternativa 1 entregar bem,
as outras duas podem nem ser necessárias.
