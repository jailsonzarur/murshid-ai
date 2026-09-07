from typing import Annotated

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    page: Annotated[int, Field(description="Página atual")]
    items_per_page: Annotated[int, Field(description="Itens por página")]
    total_items: Annotated[int, Field(description="Total de itens")]
    total_pages: Annotated[int, Field(description="Total de páginas")]


def build_meta(page: int, items_per_page: int, total_items: int) -> PaginationMeta:
    total_pages = -(-total_items // items_per_page) if total_items else 0
    return PaginationMeta(
        page=page,
        items_per_page=items_per_page,
        total_items=total_items,
        total_pages=total_pages,
    )
