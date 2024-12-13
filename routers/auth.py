from fastapi import APIRouter,Depends,HTTPException,status,UploadFile,File,Form
from pydantic import BaseModel
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr, constr
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.security import HTTPBasic, HTTPBasicCredentials

#models
from models import Session
from models.users import User

#single imports
from typing import Optional,Annotated
from datetime import datetime, timedelta,date
import logging,random,string,base64,pytz,secrets,os

#otherimports
from fastapi.responses import JSONResponse
import utilities.logger as Logger
from utilities import constants
from validators.users import UserRequest




error_logger = Logger.get_logger('error', logging.ERROR)
info_logger = Logger.get_logger('info', logging.INFO)

security = HTTPBasic()


# models.Base.metadata.create_all(bind=engine)
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
    responses={401: {"user": "Not authorized"}}
)

def get_db():
    try:
        db = Session()
        yield db
    finally:
        db.close()

def get_current_username(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = b"FotoOwlAI@2024"
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = b"libraryManagement@task"
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def get_current_time():
    # Define IST timezone
    ist = pytz.timezone('Asia/Kolkata')

    # Get current time in UTC and convert to IST
    current_time_utc = datetime.now(pytz.utc)
    current_time_ist = current_time_utc.astimezone(ist)

    return current_time_ist

def encode_otp(otp):
    today = date.today()
    # Extract year, month, and day
    year = today.year
    month = today.month
    day = today.day
    key = int(year) + int(month) + int(day)
    encypted = (int(otp)+key) % 10000

    return encypted

def encrypt_api_key(api_key):
    # Encode API key to bytes and then Base64 encode it
    encrypted_bytes = base64.b64encode(api_key.encode('utf-8'))
    # Convert bytes back to string (optional, depending on your needs)
    encrypted_str = encrypted_bytes.decode('utf-8')
    return encrypted_str


def decrypt_api_key(encrypted_api_key: str):
    # Decode the Base64 encoded API key
    try:
        decoded_bytes = base64.b64decode(encrypted_api_key)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        return None

def get_password_hash(password):
    return bcrypt_context.hash(password)
def verify_password(plain_password,hashed_password):
    return bcrypt_context.verify(plain_password,hashed_password)


def authenticate_user(username: str, password: str, db):


    user = db.query(User)\
        .filter(User.is_active == True, (User.email == username) | (User.phone_number == username))\
        .first()
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

def create_access_token(username: str, user_id: int,user_email:str,role:str,
                        expires_delta: Optional[timedelta] = None):
    encode = {"user": username, "user_id": user_id,"email":user_email,"role":role}

    if expires_delta:
        expire = datetime.utcnow()+expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    encode.update({"exp": expire})
    return jwt.encode(encode, constants.JWT_SECRET_KEY, algorithm=constants.JWT_ENCODING_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_bearer)):

    try:
        db = Session()
        payload = jwt.decode(token, constants.JWT_SECRET_KEY, algorithms=constants.JWT_ENCODING_ALGORITHM)
        user_email :str = payload.get("email")
        username: str = payload.get("user")
        user_id: int = payload.get("user_id")
        user_role:str = payload.get("role") 

        if user_email is None:
            raise get_user_exception()

        if user_id is None:
            user = db.query(User).filter(User.is_active == True,User.email == user_email).first()

            if not user:
                raise get_user_exception()
            user_id = user.id


        user_details = db.query(User).filter(User.is_active == True,User.id == user_id).first()
        return {'username': user_details.name, 'user_id': user_details.id,'email':user_details.email,"role":user_details.role}

    except Exception as e:
        return JSONResponse({"detail":"Erorr in decoding jwt token","error":str(e)},status_code=500)

    finally:
        if db:
            db.close()

@router.post("/create_admin_user")
def create_new_user(
    user: Annotated[str, Depends(get_current_username)],
    email: str = Form(...),
    password: str = Form(...),
    name:str =Form(...),
    phone_number : str = Form(...),
    db: Session = Depends(get_db)):

    try:

         # Check if user with the same username or email already exists
        db_user = db.query(User).filter(User.is_active == True,User.email == email.strip()).first()
        
        if len(name) <6 :
            return JSONResponse({"detail":"NAME MUST BE GREATER THAN 5 CHARECTERS"},status_code=400)

        if db_user and db_user.email == email:
            return JSONResponse({"detail":"Invalid email,email already registered"},status_code=400)

        # Create a new user instance
        new_user = User(
            name=name,
            email=email,
            password=get_password_hash(password),
            phone_number = phone_number,
            created_by = email,
            role = "Admin" 
        )

        db.add(new_user)
        db.commit()

        info_logger.info(f'Admin User created successfully.Email :{email} ')
        return {"message": "Admin User created successfully", "status_code": status.HTTP_201_CREATED}

    except Exception as error:
        error_logger.exception(f'Exception occured in create_admin_user. Error: {error}')
        return JSONResponse({"detail":str(error)},status_code=500)

    finally:
        if db:
            db.close()

@router.post("/create_normal_user")
def create_new_user(request:UserRequest,user: dict = Depends(get_current_user)):
    db=None
    try:

        db = Session()
        if not user :
            return {"message":"user not found", "status":status.HTTP_404_NOT_FOUND }

        if user.get("role") != "Admin":
            return JSONResponse({"detail":"Only Admin have access to create user"},status_code=403)

         # Check if user with the same username or email already exists
        db_user = db.query(User).filter(User.is_active == True,User.email == request.email.strip()).first()
        
        if len(request.name) <6 :
            return JSONResponse({"detail":"NAME MUST BE GREATER THAN 5 CHARECTERS"},status_code=400)

        if db_user and db_user.email == request.email:
            return JSONResponse({"detail":"Invalid email,email already registered"},status_code=400)
        

        # Create a new user instance
        new_user = User(
            name = request.name,
            email = request.email,
            password = get_password_hash(request.password),
            created_by = request.email,
            role = "Normal_user" 
        )

        db.add(new_user)
        db.commit()

        info_logger.info(f'Normal User created successfully.Email :{request.email} ')
        return {"message": "Normal User created successfully", "status_code": status.HTTP_201_CREATED}

    except Exception as error:
        error_logger.exception(f'Exception occured in create_normal_user. Error: {error}')
        return JSONResponse({"detail":str(error)},status_code=500)

    finally:
        if db:
            db.close()

@router.post("/token")
def login_for_access_token(form_data : OAuth2PasswordRequestForm = Depends(),
                            db: Session = Depends(get_db)):

    try:

        db_user = db.query(User).filter(User.is_active == True,User.email == form_data.username).first()
        user = authenticate_user(form_data.username, form_data.password,db)

        if not db_user:
            return JSONResponse({"detail":"INVALID EMAIL"},status_code=401)


        if not user:
            return JSONResponse({"detail":"INCORRECT PASSWORD"},status_code =401)

        info_logger.info(f"user with email {user.email} has accessed the get_token API")

        token_expires = timedelta(40)
        token = create_access_token(user.name, user.id, user.email,user.role,expires_delta=token_expires)

        if token:
            return {"access_token": token, "token_type":"Bearer"}

    except Exception as error:
        error_logger.exception(f"Error occurred in get_access_token API.Error:{error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="token not genrated")

    finally:
        if db:
            db.close()

@router.get("/logined_user")
async def logined_user(user: dict = Depends(get_current_user)):

    try:
        db= Session()
        if user is None:
            return {"message":"user not found", "status":status.HTTP_404_NOT_FOUND }
        
        info_logger.info(f"user with email {user.get('email')} has accessed the get_logined_user API")
        db_user = db.query(User).filter(User.is_active == True, User.id == user.get("user_id")).first()

        info_logger.info(f'Successfully fetched user details from database')
        return {"message": "successful",
                "data":{
                "user_details":db_user
                },
                "status":status.HTTP_200_OK }

    except Exception as error:
        error_logger.exception(f"Error occurred in get_logined_user API.Error:{error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(error))

    finally:
        if db:
            db.close()
            
#Exceptions
def get_user_exception():
    credentials_exception = HTTPException(
        status_code=401,
        details = "Could not validate credentials",
        headers = {"WWW-Authenticate" : "Bearer"}
        )
    return credentials_exception
def token_exception():
    token_exception_reponse = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"}

    )
    return token_exception_reponse
