# Rombo de US$ 17 no Whisper — diagnóstico e plano

Investigação do consumo inesperado de Whisper em 04–05/09/2026, e o que precisa
mudar para que não se repita.

## O que aconteceu

Não foi uma aula. Foi o **teste de carga**.

Os logs do worker mostram arquivos `01_aula_60min.mp3`, `02_aula_60min.mp3` e
`03_aula_60min.mp3` — áudios de 60 minutos — importados em 21 aulas chamadas
"Carga 0" a "Carga 4", entre 04/09 00:38 e 05/09 19:42.

```
44 transcrições completaram  ×  60 min  =  44 horas  →  US$ 15,84
```

O resto até os US$ 17 veio de tentativas anteriores à janela que o Docker ainda
retinha. O teste parou sozinho quando o crédito acabou: os logs terminam cheios
de `credit_balance_exhausted`.

### Por que o banco parece inocente

As 21 aulas ficaram em `PROCESSING` com **zero segmentos**. A transcrição foi
paga e nada foi persistido, porque a task desistiu antes de gravar. Somando
tudo que está no banco hoje dá 0,58 hora de áudio — cerca de US$ 0,21.

## O amplificador de custo

Em `src/features/lectures/tasks.py`, o retry chama `_transcribe_import_file`
de novo, que **re-transcreve o arquivo inteiro**:

```python
except Exception as exc:
    if self.request.retries >= MAX_RETRIES:
        ...
        return None
    raise self.retry(exc=exc, countdown=10 * 2**self.request.retries)
```

Se o chunk 6 de um áudio de 60 min falha, os 60 minutos já foram pagos — e o
retry paga outros 60. Com `MAX_RETRIES = 3`, um único arquivo pode custar **4×**.
Foram 18 retries só na janela observada.

Pior: os retries que mais dispararam foram `RateLimitError` de
`insufficient_quota` — crédito esgotado. Quatro tentativas de algo que não
tinha como passar.

## Correções, em ordem de retorno

### 1. Retry por chunk, não por arquivo

A que economiza dinheiro. Persistir cada chunk transcrito e retomar de onde
parou, em vez de recomeçar o arquivo. Um chunk que falha custa um chunk.

Implica guardar estado intermediário — provavelmente uma tabela de chunks por
import, ou o resultado parcial no Redis.

### 2. Não dar retry no que não pode passar

`insufficient_quota`, chave inválida e arquivo rejeitado por formato são
definitivos. Devem falhar na primeira tentativa. Só erros transitórios
(timeout, 5xx, rate limit por throughput) merecem retry.

### 3. Teto de duração no import

Hoje nada impede subir 10 arquivos de 200 MB numa aula. O limite atual é por
tamanho de arquivo (200 MB) e por quantidade (10), mas não por **minutos de
áudio**, que é o que se paga. Um teto por aula e por usuário/dia evita que um
teste vire conta.

### 4. Registrar minutos enviados

Não existe nenhum registro de quanto áudio foi ao Whisper. Foi preciso inferir
dos logs do Docker, que rotacionam. Persistir minutos e modelo por aula torna
o custo auditável depois do fato.

### 5. Trocar o modelo

Ver seção abaixo. Mudança de uma linha com efeito direto na conta.

## Onde debugar quando acontecer de novo

1. **`platform.openai.com/usage`** — fonte autoritativa, filtra por dia e
   modelo, mostra minutos de áudio.
2. **Logs do worker**:
   ```bash
   docker compose logs worker | grep -E "transcribe_import_file_task.*(received|retry|succeeded|gave up)"
   ```
   Rotacionam; não conte com histórico longo.
3. **Fila do Celery**, para saber se ainda está sangrando:
   ```bash
   docker compose exec redis redis-cli LLEN celery
   ```

## Pendência operacional

As 21 aulas "Carga" seguem presas em `PROCESSING` e não saem sozinhas. Decidir
entre apagá-las ou marcá-las como `FAILED`.

## Configuração que vale revisar

`task_time_limit` está em 7200s (2h) enquanto o `visibility_timeout` padrão do
broker Redis é 3600s (1h). Com `task_acks_late` no padrão (`False`) isso não
causa reentrega hoje, mas se um dia `acks_late` for ligado — recomendação comum
para tarefas longas — a combinação passa a reentregar tarefas que passem de uma
hora, e cada reentrega paga a transcrição de novo. Se ligar `acks_late`,
configurar `broker_transport_options={"visibility_timeout": 7200}` junto.
