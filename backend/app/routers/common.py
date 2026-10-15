from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..db import Base


def get_or_404[ModelT: Base](db: Session, model: type[ModelT], item_id: int) -> ModelT:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} {item_id} not found")
    return item


def conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)
