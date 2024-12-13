from pydantic import BaseModel
from pydantic import BaseModel,Field, ValidationError
from datetime import date

class CreateBookRequest(BaseModel):
    name: str = Field(..., min_length=5, max_length=30, description="The name of the book")
    author: str = Field(..., min_length=5, max_length=20, description="The author's name of the book")
    price: float = Field(..., gt=0, description="The price of the book")
    no_of_pages: int = Field(..., gt=0, description="The number of pages in the book")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "The Great Adventure",
                "author": "John Smith",
                "price": 19.99,
                "no_of_pages": 320
            }
        }
