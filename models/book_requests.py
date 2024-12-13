import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import Boolean
from models import base
from sqlalchemy import Column,DateTime, Integer, String,ForeignKey,Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import pytz


class BorrowRequests(base):
    __tablename__ = "borrow_requests"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer,ForeignKey("books.id"))
    requester_id = Column(Integer,ForeignKey("users.id"))
    borrowing_from_date = Column(DateTime)
    borrowing_to_date = Column(DateTime)
    status = Column(String,default="PENDING")
    is_active = Column(Boolean,default=True)
    created_by = Column(String)
    modified_by = Column(String)
    created_date = Column(DateTime(timezone=False), server_default=func.now())
    modified_date = Column(DateTime(timezone=False), onupdate=func.now())
