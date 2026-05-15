from __future__ import annotations

import asyncio
from typing import Any, TypeVar

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


async def invoke_structured_llm(
    llm: Any,
    messages: list[Any],
    schema: type[SchemaT],
) -> SchemaT:
    if hasattr(llm, "ainvoke"):
        result = await llm.ainvoke(messages)
    else:
        result = await asyncio.to_thread(llm.invoke, messages)

    if isinstance(result, schema):
        return result

    if isinstance(result, BaseModel):
        return schema.model_validate(result.model_dump())

    return schema.model_validate(result)
