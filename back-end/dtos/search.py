from pydantic import BaseModel
from typing import List

class SearchResultItem(BaseModel):
    id: int
    title: str
    category: str

class SearchResponse(BaseModel):
    status: str
    query: str
    results: List[SearchResultItem]
