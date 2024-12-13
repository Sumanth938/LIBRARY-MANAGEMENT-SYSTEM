#fastapi imports
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

#single imports
import os,uvicorn
from models import create_database_tables

#other imports
from routers import auth,books,borrow_requests

create_database_tables()

app = FastAPI(debug=True)

#env specific

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(borrow_requests.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8030, log_level="debug")
