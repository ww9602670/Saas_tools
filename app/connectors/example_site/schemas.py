from pydantic import BaseModel
class FetchProfileIn(BaseModel): uid: str
class FetchProfileOut(BaseModel):
    uid: str; name: str; level: int
