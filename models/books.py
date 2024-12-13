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


class Books(base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    author = Column(String)
    price = Column(Float)
    no_of_pages  = Column(Integer)
    is_active = Column(Boolean,default=True)
    created_by = Column(String)
    modified_by = Column(String)
    created_date = Column(DateTime(timezone=False), server_default=func.now())
    modified_date = Column(DateTime(timezone=False), onupdate=func.now())
