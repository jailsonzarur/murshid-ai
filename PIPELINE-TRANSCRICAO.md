# Repensar o pipeline de transcrição — plano

Reestruturação do import de aulas em três filas, com o chunk como unidade de
trabalho. Fecha os itens 1, 2, 3 e 4 de `CUSTO-TRANSCRICAO.md`.

## Por que

Hoje o import inteiro é **uma task por arquivo**. `transcribe_import_file_task`
(`src/features/lectures/tasks.py:35`) baixa o áudio, e `transcribe_audio_file`
(`src/features/lectures/ai/transcription.py:79`) corta em pedaços e transcreve
todos com `asyncio.gather` e um semáforo de 3. Se um pedaço falha, o retry
(`tasks.py:48`) recomeça o arquivo inteiro — e paga tudo de novo. Com
`MAX_RETRIES = 3`, um arquivo de 60 min pode custar 4×.

E não existe registro nenhum dos áudios. `dispatch_import_lecture`
(`tasks.py:29`) passa `list[dict]` dentro da mensagem do Celery. O único lugar
que sabe que um import está em andamento é a fila do Redis — por isso as 21
aulas "Carga" ficaram presas em `PROCESSING` sem nada contra o que reconciliar.

## Desenho

Três filas, cada uma com seu perfil de trabalho. A task chama a função de
serviço direto — sem salto HTTP.

```
fila lectures   →  lê os áudios da aula, enfileira 1 task por áudio
fila audios     →  ffmpeg: corta 1 áudio em chunks, sobe, enfileira N tasks
fila chunks     →  transcreve 1 chunk (é aqui que se gasta dinheiro)
```

O `asyncio.gather` e o `WHISPER_CONCURRENCY = 3`
(`transcription.py:18`) desaparecem: a fila passa a ser o paralelismo.

### Filas separadas porque o trabalho é diferente

`audios` roda ffmpeg — CPU, quer poucos workers. `chunks` espera rede — quer
muitos. Hoje os dois disputam o mesmo `worker_concurrency=2`
(`src/core/celery.py`), que é o gargalo de escala atual.

### O encontro dos ramos

Sem chord aninhado. Quem termina por último acende a luz, com transição atômica
para evitar corrida:

```sql
UPDATE lecture_audios SET status = 'DONE'
WHERE id = :id AND status = 'TRANSCRIBING'
  AND NOT EXISTS (SELECT 1 FROM lecture_audio_chunks
                  WHERE audio_id = :id AND transcript IS NULL)
RETURNING id
```

Só um worker recebe a linha de volta; só ele consolida. Mesmo padrão um nível
acima, do áudio para a aula.

## Tabelas

Aditivas. Nada nas tabelas existentes muda.

### `lecture_audios` — um registro por arquivo enviado

| coluna | |
|---|---|
| `id` | uuid |
| `lecture_id` | FK → `lectures.id`, `ON DELETE CASCADE` |
| `sequence` | ordem dentro da aula |
| `object_key` | o arquivo original no MinIO |
| `original_filename` | |
| `duration_seconds` | do upload |
| `status` | ver abaixo |
| `transcribed_seconds` | soma efetivamente enviada ao modelo |
| `model` | modelo usado |
| `last_error` | |
| `created_at` / `updated_at` | |

`unique (lecture_id, sequence)`.

### `lecture_audio_chunks` — um registro por pedaço

| coluna | |
|---|---|
| `id` | uuid |
| `audio_id` | FK → `lecture_audios.id`, `ON DELETE CASCADE` |
| `sequence` | ordem dentro do áudio |
| `object_key` | o pedaço no MinIO |
| `start_seconds` / `duration_seconds` | |
| `transcript` | `Text`, nulo até transcrever |
| `attempts` | |
| `last_error` | |
| `created_at` / `updated_at` | |

**`unique (audio_id, sequence)` é a idempotência.** Antes de chamar a OpenAI, a
task lê a linha: se `transcript` não é nulo, retorna sem chamar. Retry
duplicado, task reentregue pelo Redis, worker morto no meio — nada disso cobra
duas vezes.

### Estados

`lecture_audios.status`: `PENDING` → `CHUNKING` → `TRANSCRIBING` → `DONE` | `FAILED`

A reivindicação e a gravação do segment commitam juntas, então não existe estado
intermediário observável: uma queda no meio faz rollback e o áudio volta para
`TRANSCRIBING`, pronto para a reentrega retomar.

O chunk não precisa de coluna de status: `transcript IS NULL` já diz tudo, e
`last_error` guarda o motivo da última falha.

`LectureStatus` (`src/features/lectures/models.py:19`) não muda.

## Ciclo de vida do chunk

Chunk é **estado de trabalho**, não dado. Em regime normal a tabela fica vazia.

1. A task de áudio corta, sobe os pedaços e insere as linhas com `transcript`
   nulo. Chaves determinísticas — `lectures/{lecture_id}/chunks/{audio_id}/{sequence:04d}.ogg`
   — e upsert em `(audio_id, sequence)`, para que reprocessar o chunking seja seguro.
2. Cada task de chunk grava seu `transcript`.
3. Na consolidação: concatena na ordem de `sequence` → grava **uma** linha em
   `lecture_segments` → soma `transcribed_seconds` no áudio → apaga os objetos
   do MinIO → apaga as linhas de chunk.

Duas regras:

**Apagar só no sucesso.** Se o áudio falhou de vez, as linhas ficam: são a
evidência e o ponto de retomada.

**A ordem importa.** Segment primeiro (commit), depois objetos, depois linhas.
Qualquer queda no meio deixa estado recuperável — o transcript já está salvo e
sobra no máximo lixo apagável. Na ordem inversa, uma queda deixa objeto órfão
no MinIO sem nada apontando para ele.

**O total sobe de nível antes da limpeza.** `transcribed_seconds` e `model` vão
para `lecture_audios` na consolidação. A auditoria de custo vira um número
permanente, e não N linhas efêmeras.

## Classificação de erro

Item 2 do documento de custo. Faz parte desta reestruturação porque é a lógica
de retry que está sendo reescrita de qualquer jeito.

**Definitivo — falha na primeira, sem retry:**
`RateLimitError` com código `insufficient_quota`, `AuthenticationError`,
`PermissionDeniedError`, `BadRequestError` (formato rejeitado).

**Transitório — retry com backoff:**
`APITimeoutError`, `APIConnectionError`, `InternalServerError`, `RateLimitError`
por throughput.

Foram 18 retries na janela do rombo, e os que mais dispararam eram
`insufficient_quota` — quatro tentativas de algo que não tinha como passar.

## Teto de minutos no import

Item 3. Validação em `start_import_lecture`
(`src/features/lectures/services/lecture_service.py:294`), que já recebe
`duration` de cada item. Os limites atuais são 200 MB por arquivo e 10 arquivos
— nenhum dos dois é o que se paga.

Teto por aula, configurável por env. Teto por usuário/dia fica de fora por
enquanto: exige agregação e não é o que evita o acidente típico.

## Passos

Cada um é um commit que fecha sozinho.

**1. Tabelas e migration.** Modelos e migration aditiva. Nenhuma mudança de
comportamento. Aulas existentes não precisam de backfill — as 15 `COMPLETED` já
têm seus segments.

**2. Popular `lecture_audios` no import.** `start_import_lecture` passa a
gravar uma linha por arquivo depois do upload. O chord antigo continua rodando
e ignorando a tabela. Passo seguro e reversível.

**3. Fila de chunks.** A task que transcreve um chunk, com a checagem de
idempotência e a classificação de erro. Ainda não é chamada por ninguém —
testável isoladamente.

**4. Fila de áudios.** Move o chunking para fora de `transcribe_audio_file`:
corta, sobe, insere as linhas, enfileira. Mais a consolidação e a limpeza.

**5. Fila de aulas e corte.** A task de aula, `dispatch_import_lecture` passa a
enfileirar nela, e saem `transcribe_import_file_task`,
`finalize_import_lecture_task` e o `gather` de `transcribe_audio_file`.

**6. Roteamento e workers.** `task_routes` em `src/core/celery.py`, e três
processos worker num único container, sob supervisord:

```
worker_media       -Q celery,lectures,audios   prefork -c 2   (ffmpeg)
worker_transcribe  -Q chunks                   prefork -c 6   (rede)
worker_summary     -Q summaries                prefork -c 2   (rede)
```

Um container em vez de três serviços no compose, para não mudar a infraestrutura
de deploy — é o padrão que os outros repositórios já usam. `stopwaitsecs` do
supervisord fica abaixo do `stop_grace_period` do Docker, senão a saída graciosa
é interrompida no meio.

**7. Teto de minutos.** Independente dos anteriores; pode vir antes se você
quiser fechar a torneira logo.

## Testes

`test_import_chord.py` some junto com o chord. Entram:

- **Idempotência**: chunk com `transcript` preenchido não chama a OpenAI.
- **Erro definitivo**: `insufficient_quota` falha na primeira, sem retry.
- **Consolidação única**: dois chunks terminando ao mesmo tempo consolidam uma
  vez só.
- **Limpeza**: sucesso apaga objetos e linhas; falha preserva.
- **Chunking idempotente**: rodar duas vezes não duplica linha nem objeto.

`test_audio_chunking.py` continua valendo — `prepare_audio_for_whisper` muda de
chamador, não de contrato.

## Fora de escopo

- **Reconciliação.** Sua decisão. Aula presa em `PROCESSING` continua sendo
  conserto manual, e as 21 atuais seguem precisando de uma decisão.
- **As 21 aulas "Carga".** O áudio já foi apagado; não dá para reprocessar.
  Apagar ou marcar `FAILED`.
- **Endpoints HTTP no meio do pipeline.** Avaliado e descartado: ffmpeg dentro
  do processo da API, perda do freio de concorrência, e dois tradutores de erro
  a mais justamente onde a classificação de erro precisa ser confiável.
- **Trocar o modelo.** Tentado e revertido em `459c88f` por alucinação.
- **`run_async`.** Continua, uma linha por task. Removê-lo exigiria um engine
  síncrono em paralelo ao de `src/database.py:19`.

## Ficam mais fáceis depois

- **`CHUNK_TARGET_SECONDS`** (hoje 600s, `audio_chunking.py:12`) passa a ser o
  custo de um retry: 10 min ≈ US$ 0,06. Baixar dá granularidade mais fina ao
  preço de mais requisições — decisão que só faz sentido com chunk como unidade.
## Decidido durante a execução

**`task_acks_late` foi ligado**, com `visibility_timeout: 7200` junto. É o que
faz a mensagem voltar para a fila quando o worker morre no meio; sem ele, o
broker confirma a entrega antes de executar e o trabalho evapora. Só é seguro
por causa da idempotência por `(audio_id, sequence)`.

**A consolidação commita numa transação só.** A reivindicação e a gravação do
segment vão juntas, então uma queda no meio faz rollback e o áudio volta para
`TRANSCRIBING`, pronto para a reentrega retomar. Em transações separadas ele
ficaria preso em um estado que a reivindicação não aceita de volta.

**O resumo ganhou fila própria** (`summaries`) porque disputava os dois slots do
ffmpeg. Medido em produção: 88s para uma aula de 58 minutos.

**Pool async foi avaliado e descartado.** O `celery-aio-pool` serializa por
construção (`self.limit = 1` no construtor), então `--concurrency` não tem
efeito. O caminho nativo para mais densidade é `--pool threads`, medido em 100
tarefas simultâneas por ~96 MiB contra 6 por ~425 MiB do prefork — mas exige
tornar thread-local o event loop de `celery_async.py`, os clientes OpenAI e o
engine do SQLAlchemy, porque conexões asyncpg ficam presas ao loop que as criou.
