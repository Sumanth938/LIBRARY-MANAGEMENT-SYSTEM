from fastapi import APIRouter,Depends,status, Request,HTTPException,Form,status,File,UploadFile
from sqlalchemy.orm import session
from fastapi import FastAPI,Depends,status,HTTPException,Query
from sqlalchemy.orm import session
from pydantic import BaseModel,Field, ValidationError
from fastapi.responses import JSONResponse,StreamingResponse
from pydantic import BaseModel
from sqlalchemy import or_
from fastapi.responses import StreamingResponse
import csv
from io import StringIO

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
from validators.borrow_requests import CreateBorrowRequest

error_logger = Logger.get_logger('error', logging.ERROR)
info_logger = Logger.get_logger('info', logging.INFO)

# models.Base.metadata.create_all(bind=engine)


router = APIRouter(
    prefix="/borrow_requests",
    tags=["Borrow Requests"],
    responses={401: {"user": "Not authorized"}}
)

def get_db():
    try:
        db = Session()
        yield db
    finally:
        db.close()

def get_book_details_by_id(id):
    session = None
    try:
        session = Session()
        query = session.query(Books).filter(Books.is_active == True,Books.id == id).first()
        return query
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))
    finally:
        if session:
            session.close()

def get_user_details_by_id(id):
    session = None
    try:
        session = Session()
        query = session.query(User).filter(User.is_active == True,User.id == id).first()
        return query
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))
    finally:
        if session:
            session.close()

def is_book_available(book_id: int, from_date: datetime, to_date: datetime):
    """
    Check if a book is available for borrowing within the specified date range.
    
    Args:
        db (Session): The SQLAlchemy database session.
        book_id (int): The ID of the book to check.
        from_date (datetime): The start date of the borrowing range.
        to_date (datetime): The end date of the borrowing range.

    Returns:
        bool: True if the book is available, False otherwise.
    """
    session = None
    try:
        session = Session()
        # Query to check for overlapping approved requests
        overlapping_requests = (
            session.query(BorrowRequests)
            .filter(
                BorrowRequests.book_id == book_id,
                BorrowRequests.status == "APPROVED",
                BorrowRequests.is_active == True,
                or_(
                    BorrowRequests.borrowing_from_date <= to_date,
                    BorrowRequests.borrowing_to_date >= from_date
                )
            )
            .all()
        )
        # If no overlapping requests, the book is available
        return len(overlapping_requests) == 0

    except Exception as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))
    finally:
        if session:
            session.close()      

@router.post("/borrow/")
def request_borrow_book(request: CreateBorrowRequest, user: dict = Depends(get_current_user)):
    """
    Handles a book borrow request.
    
    Validates if:
    - The book exists and is active.
    - The requested dates do not overlap with existing approved or pending requests.
    - The user is authenticated.

    Parameters:
    - request (CreateBorrowRequest): The borrow request payload.
    - user (dict): The authenticated user, injected via dependency.
    - db (Session): The database session, injected via dependency.

    Returns:
    - dict: Success or error message with the appropriate status code.
    """
    session = None
    try:

        session = Session()

        if not user:
            return {"message":"USER NOT FOUND", "status":status.HTTP_404_NOT_FOUND }
        
        # Fetch the book
        book = session.query(Books).filter(Books.id == request.book_id, Books.is_active == True).first()

        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found ")
        
        if not is_book_available(request.book_id,request.borrowing_from_date,request.borrowing_to_date):
            return JSONResponse({"detail":" Failed to create borrow request,The book is not availbe in the requested date range"},status_code = 403)
        
         # Create the borrow request
        new_request = BorrowRequests(
            book_id=request.book_id,
            requester_id=user.get("user_id"),
            borrowing_from_date=request.borrowing_from_date,
            borrowing_to_date=request.borrowing_to_date,
            created_by=user.get("email")
        )

        session.add(new_request)
        session.commit()
        session.refresh(new_request)

        info_logger.info(f"User {user.get('email')} requested to borrow book ID {request.book_id} from {request.borrowing_from_date} to {request.borrowing_to_date}")
        return {"message": "Borrow request created successfully", "status": status.HTTP_201_CREATED}

    except Exception as error:
        error_logger.exception(f"Error occurred in /POST_borrow_request status API.Error:{error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))
    finally:
        if session:
            session.close()

@router.put("/update_borrow_request_status/", response_model=dict)
def update_borrow_request_status(
    request_id: int, 
    action: int, 
    user: dict = Depends(get_current_user)):
    """
    Approve or reject a borrow request.
    
    Parameters:
    - request_id (int): The ID of the borrow request to be updated.
    - action (int): The action to perform, either 1 for "approve" or 0 for"reject".
    - user (dict): The authenticated  user, injected via dependency.
    
    Returns:
    - dict: Success or error message with the appropriate status code.
    """
    session = None
    try:

        session = Session()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")

        if user.get("role") != "Admin":
            return JSONResponse({"detail":"Only Admin have access to this API"},status_code=403)

        # Fetch the borrow request
        borrow_request = session.query(BorrowRequests).filter(
            BorrowRequests.id == request_id,
            BorrowRequests.is_active == True
        ).first()

        if not borrow_request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrow request not found")

        if borrow_request.status != "PENDING":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending requests can be updated")
        
        if not is_book_available(borrow_request.book_id,borrow_request.borrowing_from_date,borrow_request.borrowing_to_date):
            return JSONResponse({"detail":" Failed to update borrow request,The book is not availbe in the requested date range"},status_code = 403)

        # Update the status based on the action
        if action ==  1:
            borrow_request.status = "APPROVED"
        elif action == 0:
            borrow_request.status = "REJECTED"
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action. Use  1 for 'approve' or 0 for 'reject'.")

        borrow_request.modified_by = user.get("email")
        session.commit()

        info_logger.info(f"Admin updated  borrow request ID {request_id}")
        return {"message": f"Borrow request updated successfully", "status": status.HTTP_200_OK}

    except HTTPException as http_exc:
        error_logger.error(f"HTTP error occurred: {http_exc.detail}")
        raise http_exc
    except Exception as exc:
        error_logger.exception(f"An unexpected error occurred: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error:{str(exc)}")
    finally:
        if session:
            session.close()

@router.get("/user_borrowing_history")
async def user_borrowing_history(sort_by: Optional[int] = None,
        status: Optional[int] = None ,
        page: Optional[int] = 1,
        size: Optional[int] = 20,
        user: dict = Depends(get_current_user)):
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

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")

        page = page - 1

        query = session.query(BorrowRequests).filter(BorrowRequests.is_active == True,BorrowRequests.requester_id == user.get("user_id"))

        if status is not None:
            if status == 0:
                query = query.filter(BorrowRequests.status == "PENDING")
            elif status == 1:
                query = query.filter(BorrowRequests.status == "APPROVED")
            elif status == 2:
                query = query.filter(BorrowRequests.status == "REJECTED")

        if sort_by:
            if sort_by != 1 and sort_by != 2:
                return JSONResponse({"detail":"SORT BY MUST EITHER 1 OR 2"},status_code=403)

        if sort_by:
            if sort_by == 1:
                query = query.order_by(BorrowRequests.id.asc())
            elif sort_by == 2:
                query = query.order_by(BorrowRequests.id.desc())

        # Get total number of items
        total_items = query.count()

        # Calculate total pages
        total_pages = (total_items + size - 1) // size

        requests = query.offset(page*size).limit(size).all()

        content = [
            {   "request_details":request,
                "book_details":get_book_details_by_id(request.book_id)
            } for request in requests
        ]
        
        response = {
            "message": "SUCCESSFUL",
            "data": content,
            "status": 200,
            "pagination": {
                "current_page": page + 1,
                "items_per_page": size,
                "total_pages": total_pages,
                "total_items": total_items
            }
        }

        info_logger.info("Successfully fetched user borrowing history  from database")
        return response
    except Exception as error:
        error_logger.exception(f"Error occurred in /GET_user_borrowing_history/ API.Error:{error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))

    finally:
        if session:
            session.close()

@router.get("/download_borrowing_history_as_csv_file")
async def user_borrowing_history_csv(
    sort_by: Optional[int] = None,
    status: Optional[int] = None,
    page: Optional[int] = 1,
    size: Optional[int] = 20,
    user: dict = Depends(get_current_user)
):
    """
    Retrieve all active books with optional sorting and pagination and return the data as a CSV file.

    Parameters:
    ----------
    sort_by : Optional[int] - Sort books by ID (1 for ascending, 2 for descending). Defaults to None.\n
    page : Optional[int] - The page number to retrieve. Defaults to 1.\n
    size : Optional[int]- Number of books per page. Defaults to 20.\n

    Returns:
    -------
    StreamingResponse - A response streaming the borrowing history as a CSV file.
    """
    session = None
    try:
        session = Session()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")

        page = page - 1

        query = session.query(BorrowRequests).filter(
            BorrowRequests.is_active == True,
            BorrowRequests.requester_id == user.get("user_id")
        )

        if status is not None:
            if status == 0:
                query = query.filter(BorrowRequests.status == "PENDING")
            elif status == 1:
                query = query.filter(BorrowRequests.status == "APPROVED")
            elif status == 2:
                query = query.filter(BorrowRequests.status == "REJECTED")

        if sort_by:
            if sort_by != 1 and sort_by != 2:
                return JSONResponse({"detail": "SORT BY MUST EITHER 1 OR 2"}, status_code=403)

            if sort_by == 1:
                query = query.order_by(BorrowRequests.id.asc())
            elif sort_by == 2:
                query = query.order_by(BorrowRequests.id.desc())

        requests = query.offset(page * size).limit(size).all()

        # Prepare CSV data
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["Request ID", "Book ID", "Book Name","Book Author","No of Pages","Status", "Request Date", "Request FromDate","Request toDate"])

        for request in requests:
            book_details = get_book_details_by_id(request.book_id)
            csv_writer.writerow([
                request.id,
                request.book_id,
                book_details.name,
                book_details.author,
                book_details.no_of_pages,
                request.status,
                request.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                request.borrowing_from_date.strftime("%Y-%m-%d %H:%M:%S"),
                request.borrowing_to_date.strftime("%Y-%m-%d %H:%M:%S")
            ])

        csv_file.seek(0)

        # Streaming the CSV file as a response
        return StreamingResponse(
            iter([csv_file.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=user_borrowing_history.csv"}
        )

    except Exception as error:
        error_logger.exception(f"Error occurred in /GET_user_borrowing_history_csv/ API. Error: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error))

    finally:
        if session:
            session.close()

@router.get("/get_all_borrow_requests")
async def get_all_borrow_requests(sort_by: Optional[int] = None,
        status: Optional[int] = None ,
        page: Optional[int] = 1,
        size: Optional[int] = 20,
        user: dict = Depends(get_current_user)):
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

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")
        
        if user.get("role") != "Admin":
            return JSONResponse({"detail":"Only Admin have access to this API"},status_code=403)

        page = page - 1

        query = session.query(BorrowRequests).filter(BorrowRequests.is_active == True)

        if status is not None:
            if status == 0:
                query = query.filter(BorrowRequests.status == "PENDING")
            elif status == 1:
                query = query.filter(BorrowRequests.status == "APPROVED")
            elif status == 2:
                query = query.filter(BorrowRequests.status == "REJECTED")

        if sort_by:
            if sort_by != 1 and sort_by != 2:
                return JSONResponse({"detail":"SORT BY MUST EITHER 1 OR 2"},status_code=403)

        if sort_by:
            if sort_by == 1:
                query = query.order_by(BorrowRequests.id.asc())
            elif sort_by == 2:
                query = query.order_by(BorrowRequests.id.desc())

        # Get total number of items
        total_items = query.count()

        # Calculate total pages
        total_pages = (total_items + size - 1) // size

        requests = query.offset(page*size).limit(size).all()

        content = [
            {
                "request_details":request,
                "book_details":get_book_details_by_id(request.book_id),
                "requester_details":get_user_details_by_id(request.requester_id)
            } for request in requests
        ]
        
        response = {
            "message": "SUCCESSFUL",
            "data": content,
            "status": 200,
            "pagination": {
                "current_page": page + 1,
                "items_per_page": size,
                "total_pages": total_pages,
                "total_items": total_items
            }
        }

        info_logger.info("Successfully fetched all borrow requests data  from database")
        return response
    except Exception as error:
        error_logger.exception(f"Error occurred in /GET_get_all_borrow_requests/ API.Error:{error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))

    finally:
        if session:
            session.close()

@router.get("/user_borrowing_history_of_specific_user")
async def user_borrowing_history_of_specific_user(user_id : int,sort_by: Optional[int] = None,
        status: Optional[int] = None ,
        page: Optional[int] = 1,
        size: Optional[int] = 20,
        user: dict = Depends(get_current_user)
        ):
    """
    Retrieve all active books with optional sorting and pagination.

    Parameters:
    ----------
    sort_by : Optional[int] - Sort books by ID (1 for ascending, 2 for descending). Defaults to None.\n
    page : Optional[int] - The page number to retrieve. Defaults to 1.\n
    size : Optional[int]- Number of books per page. Defaults to 20.\n
    user_id : int - Id of the specific user to see borrowing history

    Returns:
    -------
    JSONResponse - A JSON response containing book data, status, and pagination details.
    """
    session = None
    try:
        session = Session()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")
        
        if user.get("role") != "Admin":
            return JSONResponse({"detail":"Only Admin have access to this API"},status_code=403)
        
        db_user = session.query(User).filter(User.is_active == True,User.id == user_id).first()

        if not db_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")

        page = page - 1

        query = session.query(BorrowRequests).filter(BorrowRequests.is_active == True,BorrowRequests.requester_id == user_id)

        if status is not None:
            if status == 0:
                query = query.filter(BorrowRequests.status == "PENDING")
            elif status == 1:
                query = query.filter(BorrowRequests.status == "APPROVED")
            elif status == 2:
                query = query.filter(BorrowRequests.status == "REJECTED")

        if sort_by:
            if sort_by != 1 and sort_by != 2:
                return JSONResponse({"detail":"SORT BY MUST EITHER 1 OR 2"},status_code=403)

        if sort_by:
            if sort_by == 1:
                query = query.order_by(BorrowRequests.id.asc())
            elif sort_by == 2:
                query = query.order_by(BorrowRequests.id.desc())

        # Get total number of items
        total_items = query.count()

        # Calculate total pages
        total_pages = (total_items + size - 1) // size

        requests = query.offset(page*size).limit(size).all()

        content = [
            {   "request_details":request,
                "book_details":get_book_details_by_id(request.book_id)
            } for request in requests
        ]
        
        response = {
            "message": "SUCCESSFUL",
            "data": content,
            "status": 200,
            "pagination": {
                "current_page": page + 1,
                "items_per_page": size,
                "total_pages": total_pages,
                "total_items": total_items
            }
        }

        info_logger.info("Successfully fetched user borrowing history  from database")
        return response
    except Exception as error:
        error_logger.exception(f"Error occurred in /GET_user_borrowing_history_of_specific_user/ API.Error:{error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))

    finally:
        if session:
            session.close()