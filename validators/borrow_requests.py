from pydantic import BaseModel
from pydantic import BaseModel,Field, ValidationError
from datetime import date,datetime

class CreateBorrowRequest(BaseModel):
    book_id: int = Field(..., description="The ID of the book to be borrowed")
    borrowing_from_date: datetime = Field(..., description="The start date of the borrowing period")
    borrowing_to_date: datetime = Field(..., description="The end date of the borrowing period")
    
    class Config:
        json_schema_extra = {
            "example": {
                "book_id": 1,
                "borrowing_from_date": "2024-12-01T10:00:00",
                "borrowing_to_date": "2024-12-15T10:00:00",
            }
        }
