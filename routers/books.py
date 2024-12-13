from fastapi import APIRouter,Depends,status, Request,HTTPException,Form,status,File,UploadFile
from sqlalchemy.orm import session
from fastapi import FastAPI,Depends,status,HTTPException,Query
from sqlalchemy.orm import session
from pydantic import BaseModel,Field, ValidationError
from fastapi.responses import JSONResponse,StreamingResponse
from pydantic import BaseModel

#models impors
from models.users import  User
from models.books import Books
from models.book_requests import BorrowRequests
from  models import Session

#single imports
import os,pytz,logging,io
from typing import List,Optional,Annotated
from datetime import datetime,date

#other imports
from .auth  import get_current_user
import utilities.logger as Logger
from routers.auth import get_password_hash,get_current_username
from validators.books import  CreateBookRequest

error_logger = Logger.get_logger('error', logging.ERROR)
info_logger = Logger.get_logger('info', logging.INFO)

# models.Base.metadata.create_all(bind=engine)


router = APIRouter(
    prefix="/books",
    tags=["Books"],
    responses={401: {"user": "Not authorized"}}
)

def get_db():
    try:
        db = Session()
        yield db
    finally:
        db.close()

@router.get("/get_all_books")
async def get_all_books(user: Annotated[str, Depends(get_current_username)],sort_by: Optional[int] = None,page: Optional[int] = 1, size: Optional[int] = 20):
    """
    Retrieve all active books with optional sorting and pagination.

    Parameters:
    ----------
    sort_by : Optional[int] - Sort books by ID (1 for ascending, 2 for descending). Defaults to None.\n
    page : Optional[int] - The page number to retrieve. Defaults to 1.\n
    size : Optional[int]- Number of books per page. Defaults to 20.\n

    Returns:
    -------
    JSONResponse - A JSON response containing book data, status, and pagination details.
    """
    session = None
    try:
        session = Session()

        page = page - 1

        query = session.query(Books).filter(Books.is_active == True)

        if sort_by:
            if sort_by != 1 and sort_by != 2:
                return JSONResponse({"detail":"SORT BY MUST EITHER 1 OR 2"},status_code=403)

        if sort_by:
            if sort_by == 1:
                query = query.order_by(Books.id.asc())
            elif sort_by == 2:
                query = query.order_by(Books.id.desc())

        # Get total number of items
        total_items = query.count()

        # Calculate total pages
        total_pages = (total_items + size - 1) // size

        books = query.offset(page*size).limit(size).all()
        
        response = {
            "message": "SUCCESSFUL",
            "data": books,
            "status": 200,
            "pagination": {
                "current_page": page + 1,
                "items_per_page": size,
                "total_pages": total_pages,
                "total_items": total_items
            }
        }

        info_logger.info("Successfully fetched all books data  from database")
        return response
    except Exception as error:
        error_logger.exception(f"Error occurred in /GET_books/ API.Error:{error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))

    finally:
        if session:
            session.close()

@router.get("/{id}")
def get_book_by_id(user: Annotated[str, Depends(get_current_username)],id):
    """
    Retrieve a specific book by its ID if it is active.

    Parameters:
    ----------
    id : int - The ID of the book to retrieve.\n

    Returns:
    -------
    dict -  A dictionary containing the book details if found, along with a success message and status code.\n
    JSONResponse - A JSON response with an error message and a 404 status code if the book is not found.
    """
    session = None
    try:
        session = Session()
        book = session.query(Books).filter(Books.is_active == True,Books.id == id).first()

        if book:
            info_logger.info("Sucessfully fetched book details sucessfully")
            return {"message": "SUCCESSFUL","data":book,"status_code":200}
        
        return JSONResponse({"detail": "INVALID ID,BOOK NOT FOUND"}, status_code=404)
    except Exception as error:
        error_logger.exception(f"Error occurred in /GET_books_by_id/ API.Error:{error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))
    finally:
        if session:
            session.close()

@router.post("/")
def create_new_book(request:CreateBookRequest,user: dict = Depends(get_current_user)):
    """
    Creates a new book in the system for the authenticated user.

    Validates the input and associates the book with the authenticated user.
    If successful, returns a 201 response with a success message. 
    If validation fails or other errors occur, appropriate error responses are returned.

    Parameters:
    - request (CreateBookRequest): The book details (name, author, price, no_of_pages).
    - user (dict): The authenticated user, injected by `Depends(get_current_user)`.
    - db (Session): The database session, injected by `Depends(get_db)`.

    Returns:
    - JSONResponse: A JSON response with a success or error message and an HTTP status code.
    """
    session = None
    try:
        session = Session()
        book = session.query(Books).filter(Books.is_active == True).first()

        if not user:
            return {"message":"USER NOT FOUND", "status":status.HTTP_404_NOT_FOUND }
        
        if user.get("role") != "Admin":
            return JSONResponse({"detail":"Only Admin have access to add new book"},status_code=403)
        
        info_logger.info(f"user with email {user.get('email')} has accessed the /POST_create_new_book_status API")


        book = Books(
            name=request.name,
            author=request.author,
            price=request.price,
            no_of_pages=request.no_of_pages,
            created_by=user.get("email")
        )

        session.add(book)
        session.commit()

        info_logger.info(f"Admin sucessfulyy added a new book ID:{book.id}")
        return JSONResponse({"detail":"ADMIN SUCESSFULLY ADDED NEW BOOK"},status_code=201)
    
    except Exception as error:
        error_logger.exception(f"Error occurred in /POST_create_new_book_status API.Error:{error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))
    finally:
        if session:
            session.close()

@router.put("/{id}")
def update_book(id: int, request: CreateBookRequest, user: dict = Depends(get_current_user)):
    """
    Updates an existing book for the authenticated user.

    Validates if the book exists, is owned by the user, and is active.
    Updates the book's name, author, price, and number of pages, then returns a success response.
    If any validation fails, appropriate error responses are returned.

    Parameters:
    - id (int): The ID of the book to be updated.
    - request (CreateBookRequest): The updated book details (name, author, price, no_of_pages).
    - user (dict): The authenticated user, injected by `Depends(get_current_user)`.
    - db (Session): The database session, injected by `Depends(get_db)`.

    Returns:
    - JSONResponse: A JSON response with a success or error message and an HTTP status code:
        - HTTP 200 if the book is successfully updated.
        - HTTP 404 if the book is not found or not owned by the user.
        - HTTP 500 if an internal error occurs.
    """
    session = None
    try:
        session = Session()

        # Check if user exists
        if not user:
            return {"message": "USER NOT FOUND", "status": status.HTTP_404_NOT_FOUND}
        
        if user.get("role") != "Admin":
            return JSONResponse({"detail":"Only Admin have access to update book"},status_code=403)

        info_logger.info(f"user with email {user.get('email')} is accessing the /PUT_update_book API for book ID {id}")

        # Find the book by ID and ownership
        book = session.query(Books).filter(Books.id == id, Books.is_active == True).first()

        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")

         # Update book fields
        book.name = request.name
        book.author = request.author
        book.price = request.price
        book.no_of_pages = request.no_of_pages
        book.modified_by = user.get("email")

        session.commit()

        info_logger.info(f"Admin successfully updated book ID: {id}")
        return JSONResponse({"detail": "ADMIN  SUCCESSFULLY UPDATED THE BOOK"}, status_code=200)

    except Exception as exc:
        error_logger.exception(f"Error occurred in /PUT_update_book API. Error: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    finally:
        if session:
            session.close()

@router.delete("/{id}")
def delete_book_by_id(id,user: dict = Depends(get_current_user)):
    """
    Delete a specific book by ID if the user is the owner.

    Parameters:
    ----------
    id : int\n
        The ID of the book to delete.
    user : dict
        The current user (retrieved from authentication).

    Returns:
    -------
    JSONResponse\n
        A success or error message based on the result.
    """
    session = None
    try:
        session = Session()
        book = session.query(Books).filter(Books.is_active == True,Books.id == id).first()

        if not user:
            return {"message":"user not found", "status":status.HTTP_404_NOT_FOUND }
        
        if user.get("role") != "Admin":
            return JSONResponse({"detail":"Only Admin have access to delete book"},status_code=403)
        
        if not book:
            return JSONResponse({"detail": "INVALID ID,book NOT FOUND"}, status_code=404)
        
        info_logger.info(f"user with email {user.get('email')} has accessed the /DELETE_book_by_id API")
        
        book.is_active = False
        session.commit()

        info_logger.info(f"User Sucessfully deleted the book ID:{id}")
        return JSONResponse({"detail": "USER SUCCESSFULY DELTED THE book"},status_code=204)
        
        
    except Exception as error:
        error_logger.exception(f"Error occurred in /DELETE_book_by_id/ API.Error:{error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))
    finally:
        if session:
            session.close()