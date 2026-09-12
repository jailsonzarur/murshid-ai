# Auditoria: o que precisa virar síncrono para o gevent

Levantamento do que é assíncrono hoje nos dois caminhos que passariam a rodar
sob `--pool gevent`: a fila `chunks` e a fila `summaries`.

## A descoberta que muda o desenho

**Código síncrono roda nos dois pools.** Prefork executa numa processo, gevent
executa num greenlet. A diferença é só quantos cabem ao mesmo tempo.

Isso quer dizer que converter esses caminhos para síncrono **não é porta de uma
via**, e que trocar de pool depois vira mudança de uma variável — sem `if` no
código, sem duas implementações para manter em sincronia.

É o oposto do que fizemos com o pool async, onde a task precisava existir em
duas formas. Aqui uma forma só serve os dois.

## Caminho 1 — `transcribe_chunk` (fila `chunks`)

| peça | hoje | sob gevent | compartilhado com a API? |
|---|---|---|---|
| `AsyncSessionLocal` (4 usos) | SQLAlchemy async + asyncpg | `Session` + psycopg | **sim**, toda a API |
| `get_audio_chunk` | `async def` | `def` | **não** — nenhum uso fora do worker |
| `asyncio.to_thread(bucket.download_to)` | wrapper | **desaparece** | — |
| `transcribe_chunk_path` | `async def` + `to_thread(read_bytes)` | `def` | **não** |
| `transcribe_audio_chunk` → `AsyncOpenAI` | async | `OpenAI` | **sim** — a aula ao vivo usa |

## Caminho 2 — `generate_final_summary` (fila `summaries`)

Confirmado: **só a task chama essa função.** A API não toca nela.

| peça | hoje | sob gevent | compartilhado? |
|---|---|---|---|
| `AsyncSessionLocal` (2 usos) | async | `Session` | **sim** |
| `get_lecture_with_segments` | `async def` | `def` | **sim** (4 usos fora) |
| `get_lecture_by_id` | `async def` | `def` | **sim** (6 usos fora) |
| `asyncio.gather` dos dois agentes | asyncio | `gevent.spawn` + `joinall` | **não** |
| `build_final_summary` → `AsyncOpenAI` | async | `OpenAI` | **não** |
| `build_final_tree` → `AsyncOpenAI` | async | `OpenAI` | **não** |

## Duas coisas que ficam mais simples, não mais difíceis

**O `bucket_service` já é 100% síncrono** — zero `async`/`await` no arquivo
inteiro. É por isso que o pipeline o embrulha em `asyncio.to_thread`. Sob
gevent esses wrappers **somem** e a chamada vira direta; o socket fica
cooperativo pelo monkey-patching. Menos código, não mais.

**O `ffmpeg` não entra nessa conta.** Ele vive no `chunk_audio`, na fila
`audios`, que continua em prefork.

## O nó de verdade: a camada de dados

Tudo acima é troca de biblioteca, exceto uma coisa. O
`AsyncSessionLocal` é global de módulo em `src/database.py` e é usado pela API
inteira. Ele não pode virar síncrono.

Mas repara no tamanho real do problema. As funções de repositório que os dois
caminhos gevent precisam em versão síncrona são **três**:

```
get_audio_chunk              (worker-only, nem precisa manter a versão async)
get_lecture_with_segments    (a API usa, precisa das duas)
get_lecture_by_id            (a API usa, precisa das duas)
```

Nenhuma delas tem mais de cinco linhas. O `add_segment` e as funções de
reivindicação ficam de fora: são usadas por `consolidate_audio` e
`finalize_lecture`, que rodam na fila `audios` e continuam em prefork.

## O que seria escrito

| item | onde | tamanho |
|---|---|---|
| engine e `SessionLocal` síncronos | `src/database.py` | ~10 linhas |
| 3 funções de repositório síncronas | `repository.py` | ~15 linhas |
| cliente `OpenAI` síncrono | `transcription.py` | ~8 linhas |
| cliente `OpenAI` síncrono | `final_summary_agent.py` | ~8 linhas |
| cliente `OpenAI` síncrono | `mindmap_tree_agent.py` | ~8 linhas |
| `transcribe_chunk` síncrona | `import_pipeline.py` | reescrita de ~35 linhas |
| `generate_final_summary` síncrona | `lecture_service.py` | reescrita de ~45 linhas |
| `gather` → `gevent.spawn` | `lecture_service.py` | ~5 linhas |

Algo em torno de **130 linhas**, das quais metade é reescrita de função
existente, não código novo.

A URL do banco muda de esquema: `postgresql+asyncpg://` vira
`postgresql+psycopg://` para o engine síncrono — derivado por substituição de
string a partir da mesma variável, não uma segunda configuração.

## O que fica com duas versões

Só duas coisas, e as duas por motivo legítimo:

**`transcribe_audio_chunk`** — o caminho da aula ao vivo (`process_segment`)
chama por dentro de rota async da API. Precisa do cliente async; o worker
precisa do síncrono.

**`get_lecture_with_segments` e `get_lecture_by_id`** — a API lê aula em rota
async.

Todo o resto passa a existir **só na forma síncrona**, porque só o worker usa.
Isso é o que evita o risco de as duas implementações divergirem no caminho que
gasta dinheiro.

## Riscos

**`psycopg` bloqueia o hub durante a query.** As queries desses caminhos são
três ou quatro, de poucos milissegundos. Com 100 greenlets são centenas de
milissegundos de hub travado por onda — aceitável contra os 30s da chamada que
fica cooperativa. Se incomodar, `psycogreen` resolve.

**O monkey-patching é global do processo.** Ele vale para o worker de gevent
inteiro. Como esse processo só roda essas duas tasks, o raio é conhecido — mas
qualquer import que puxe asyncio nesse worker passa a conviver com o patch.

**Dois engines no mesmo processo do worker gevent.** O `database.py` passaria a
criar os dois na importação. O async ficaria ocioso ali, consumindo só o
objeto, sem conexões — o pool do SQLAlchemy é preguiçoso.

## Ordem sugerida

1. Engine síncrono e as três funções de repositório, sem trocar nada de lugar
2. Clientes `OpenAI` síncronos nos três módulos
3. `transcribe_chunk` síncrona — ainda em prefork, que roda igual
4. `generate_final_summary` síncrona — idem
5. Só então trocar o pool das duas filas para gevent, por variável

Os passos 3 e 4 são verificáveis com o pipeline rodando normalmente, porque
código síncrono roda em prefork. O gevent entra por último e é reversível.
