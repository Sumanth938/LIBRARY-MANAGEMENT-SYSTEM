from pydantic import BaseModel
from pydantic import BaseModel,Field, ValidationError
from datetime import date

class UserRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=30, description="The email of the user")
    password: str = Field(..., min_length=8, max_length=20, description="The password for the user")
    name: str = Field(...,min_length=5, max_length=20, description="name of the user")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "johndoe@gmail.com",
                "password": "john@password"
            }
        }