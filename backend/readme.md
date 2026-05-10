# API v2

API minimal com FastAPI, SQLAlchemy async, Alembic, JWT e gerenciamento de usuarios.

## Comandos principais

```bash
uv sync
make test
make docker-up
make up
make dev
```

O projeto nao usa Redis. Refresh tokens sao JWTs assinados com expiracao propria.
