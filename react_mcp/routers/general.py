from typing import Union
from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["general"])
def read_root():
    return {"Hello": "World"}


@router.get("/items/{item_id}", tags=["general"])
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q} 