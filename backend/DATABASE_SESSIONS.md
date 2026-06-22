# Sessões de Banco — Como Usar `AsyncSessionLocal`

Este guia explica quando e como abrir sessões SQLAlchemy no projeto, com base em
armadilhas reais que já apareceram (e foram corrigidas) no código.

## Contextos

### 1. Rotas FastAPI — use `Depends(get_db)`

Nunca abra sessão manualmente em rotas. O FastAPI já fornece uma via injeção
de dependência:

```python
@router.post("/foo")
async def create_foo(
    payload: FooSchema,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await foo_service.create_foo(db, payload=payload)
```

A sessão dura exatamente a requisição. Se a rota falhar, ela é fechada
automaticamente.

### 2. Celery workers — abra manualmente

Celery vive fora do ciclo de request, então **o entry point da task** precisa
criar a sessão:

```python
from src.database import AsyncSessionLocal

async def _my_task(entity_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        ...  # trabalho com db
```

`async with` garante fechamento mesmo com exceção. Esse é o único padrão
oficial pra abrir sessão fora de uma rota FastAPI.

### 3. Funções de serviço — recebem `db` por parâmetro

Funções dentro de `features/*/services/*.py` **nunca** devem criar suas
próprias sessões. Sempre recebem `db: AsyncSession` por argumento. Exceções
existem (como `generate_final_summary` em `lectures/services/lecture_service.py`),
e estão documentadas abaixo no padrão de fases.

---

## As 4 armadilhas

### Armadilha 1: setar FK em vez de relationship

```python
# RUIM — back_populates não dispara
segment = LectureSegmentModel(lecture_id=lecture.id, ...)
db.add(segment)

# BOM — back_populates dispara, coleção em memória fica sincronizada
segment = LectureSegmentModel(lecture=lecture, ...)
db.add(segment)
```

**Por quê:** o `back_populates="segments"` definido nos modelos é uma ponte
automática entre os dois lados de uma relação. Quando você atribui pelo
*relationship* (`segment.lecture = lecture`), o SQLAlchemy executa
automaticamente `lecture.segments.append(segment)`.

Setar a coluna FK direto (`segment.lecture_id = lecture.id`) **não** dispara
essa ponte — pra coluna FK ele é só um número. Resultado: `lecture.segments`
em memória continua desatualizado, mesmo depois do INSERT.

**Quando isso quebra:** se a mesma função (ou outra função na mesma sessão)
ler `lecture.segments` depois, vai pegar a lista stale.

### Armadilha 2: reutilizar sessão depois de commit

```python
# RUIM — identity map devolve dados stale após o commit
async with AsyncSessionLocal() as db:
    entity = await get_entity_with_children(db, entity_id)
    # ... insere children, commit ...
    await db.commit()
    
    # entity.children pode estar stale aqui
    await long_running_function(db, entity_id)  # chamada de outra fase
```

**Por quê:** o projeto usa `expire_on_commit=False` em `database.py`. Isso
significa que objetos **não** são invalidados após `db.commit()`. Combinado
com o *identity map* (uma sessão = uma instância por PK), um segundo
`SELECT` na mesma sessão devolve o objeto em cache, sem refresh.

**Como evitar:** se você precisa de uma fase isolada depois de um commit,
**abra uma sessão nova**:

```python
# BOM
async with AsyncSessionLocal() as db:
    # fase 1: insere, commit
    await db.commit()

async with AsyncSessionLocal() as db:  # sessão nova, identity map vazio
    # fase 2: lê fresco do banco
```

### Armadilha 3: segurar sessão durante operação demorada

```python
# RUIM — conexão do pool fica presa esperando HTTP externo
async with AsyncSessionLocal() as db:
    data = await get_something(db)
    result = await call_openai(data)  # ← 30s segurando uma conexão à toa
    await save_result(db, result)
```

**Por quê:** cada `AsyncSession` reserva uma conexão do pool. Enquanto a
sessão está aberta, a conexão **não pode** atender outras requisições.
Segurar uma conexão durante HTTP request externa esgota o pool sob
concorrência.

**Como evitar:** dividir em fases — abrir sessão só pra DB, fechar antes
da operação externa, reabrir depois:

```python
# BOM
async def generate_final_summary(lecture_id: UUID) -> None:
    # Fase 1: leitura rápida
    async with AsyncSessionLocal() as db:
        lecture = await get_lecture_with_segments(db, lecture_id)
        full_transcript = "\n\n".join(s.transcript for s in lecture.segments)
        # extrai pra variáveis locais o que vai precisar depois
    # ↑ conexão devolvida ao pool

    # Fase 2: operação externa demorada — NENHUMA conexão segurada
    summary_result = await build_final_summary(full_transcript, ...)

    # Fase 3: gravação rápida
    async with AsyncSessionLocal() as db:
        lecture = await get_lecture_by_id(db, lecture_id)
        lecture.summary = summary_result
        await db.commit()
```

### Armadilha 4: compartilhar sessão entre corrotinas paralelas

```python
# RUIM — AsyncSession NÃO é seguro pra concorrência
async with AsyncSessionLocal() as db:
    await asyncio.gather(
        query_a(db),
        query_b(db),
    )
```

`AsyncSession` é stateful e single-thread por design. Compartilhar a mesma
`db` entre coroutinas em `asyncio.gather` corrompe o estado interno.

**Como evitar:** cada corrotina abre sua própria sessão, **ou** as operações
DB rodam sequencialmente fora do `gather`.

```python
# BOM — só as operações externas (sem DB) rodam em paralelo
async with AsyncSessionLocal() as db:
    data = await get_data(db)

results = await asyncio.gather(
    external_call_a(data),
    external_call_b(data),
)

async with AsyncSessionLocal() as db:
    await save_all(db, results)
```

---

## Padrão recomendado: tasks Celery com fase externa

O padrão usado em `lectures/services/lecture_service.py:generate_final_summary`
e `lectures/tasks.py:_process_imported_lecture_task` resolve as 4 armadilhas
simultaneamente:

```python
async def my_task(entity_id: UUID) -> None:
    # Fase 1: leitura rápida (sessão A)
    async with AsyncSessionLocal() as db:
        entity = await get_entity(db, entity_id)
        # ... extrai dados pra variáveis locais ...

    # Fase 2: trabalho externo sem DB (HTTP, IA, etc.)
    result = await call_external_service(...)

    # Fase 3: gravação rápida (sessão B, isolada da A)
    async with AsyncSessionLocal() as db:
        entity = await get_entity(db, entity_id)
        entity.field = result
        await db.commit()
```

**Garantias do padrão:**
- Cada sessão dura segundos no máximo (só queries rápidas).
- Nenhuma conexão presa durante chamadas externas.
- A fase 3 lê o estado mais fresco do banco — sem cache stale.
- Cada fase tem transação isolada.

---

## Resumo prático

| Onde você está | O que fazer |
|---|---|
| Rota FastAPI | `db: Annotated[AsyncSession, Depends(get_db)]` |
| Função de serviço | Recebe `db: AsyncSession` por parâmetro |
| Entry point de task Celery | Abre `async with AsyncSessionLocal() as db:` |
| Função longa com chamada externa | Divide em fases, cada fase com sessão própria |

| Operação | Use |
|---|---|
| Criar filho de uma relação | `Child(parent=parent, ...)` (não `parent_id=parent.id`) |
| Re-fetchar entity após commit | Sessão nova (`async with AsyncSessionLocal() as db:`) |
| Operação externa demorada | Feche a sessão antes, abra outra depois |
| Operações paralelas | Só em código sem DB; ou uma sessão por coroutina |

---

## Referências no código

- `database.py:24` — `AsyncSessionLocal = async_sessionmaker(..., expire_on_commit=False)`
- `database.py:51` — `get_db()`, usado por `Depends(get_db)` nas rotas
- `lectures/services/lecture_service.py:generate_final_summary` — padrão de 3 fases
- `lectures/tasks.py:_process_imported_lecture_task` — task Celery com duas sessões sequenciais
