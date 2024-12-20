# Library  Management FastAPI Application

This is a task of Library Management  API built using FastAPI. Admin user can add new book and user , Admin can update or delete the book , can see the user borrowing history ,can see all borrow requests and update the status of the requests. Users can see the all books and request it for borrowing. The project includes input validation, user authentication, and database integration.

# Features
    1.Crud operations on book by Admin User
    2.Role based access.
    3.Validations for input feilds.
    4.SQLAlchemy integration with PostgreSQL.
    5.Downloading borrow history as CSV file.

# APIS 
    # Librarian APIs
        Create a new library user with an email and password.
        View all book borrow requests.
        Approve or deny a borrow request.
        View a user’s book borrow history.

    # Library User APIs:
        Get list of books
        Submit a request to borrow a book for specific dates (date1 to date2).
        View personal book borrow history.


# Requirements

Ensure the following software is installed on your machine:
    -> Python (>=3.8)
    -> PostgreSQL
    -> Pip (Python package installer)
    -> Git (for cloning the repository)

# Setup Instructions
1. Clone the Repository:
    git clone <repository-url>
    cd LIBRARY-MANAGEMENT-SYSTEM

2. Set Up a Virtual Environment
Create and activate a virtual environment for Python dependencies.

    On Linux/Mac:
        python3 -m venv env
        source env/bin/activate

    On Windows:
        python -m venv env
        env\Scripts\activate

3. Install Dependencies
Use pip to install the required Python packages.
    pip install -r requirements.txt

4. Start the Application
Run the FastAPI application:
    uvicorn main:app --reload
By default, the server will start on http://127.0.0.1:8000.
Go to This route : Swagger UI: http://127.0.0.1:8000/docs 
You will have all APIs Here


# API Documentation
FastAPI automatically generates interactive API documentation at the following endpoints:

Swagger UI: http://127.0.0.1:8000/docs
ReDoc: http://127.0.0.1:8000/redoc

# How to Test
1. Create an Admin User

    To create an admin user, use the create_admin_user API. The basic authentication credentials are:

    Username: FotoOwlAI@2024

    Password: libraryManagement@task

This API allows you to set up the administrator who will have full control over managing books, users, and borrow requests.

2. Add Users and Books

    # Add Users:

    Use the create_user API to add library users. These users can request books for borrowing.

    # Add Books:

    Use the add_book API to add new books to the library. Provide details like title, author, and availability status.

3. Test Features

    # Test as Admin:

        Use the get_all_books API to retrieve the list of all books in the library.

        Use the get_book_by_id API to view details of a specific book.

        View all borrow requests using the get_borrow_requests API.

        Approve or reject borrow requests using the update_request_status API.

    # Test as User:

        Use the get_all_books API to view available books.

        Submit a borrow request for a specific book using the request_book API.

        View personal borrowing history using the get_user_borrow_history API.

# Example Usage


    Test Admin APIs

        Create an admin user using the create_admin_user API.

        Add some books to the library.

    Add library users.

        Test managing borrow requests and downloading borrowing history.

    Test User APIs:

        Use a user account to view available books.

        Request a book for borrowing.

        View borrowing history to confirm the request is logged.

        By following these steps, you can verify all the features of the Library Management System.





