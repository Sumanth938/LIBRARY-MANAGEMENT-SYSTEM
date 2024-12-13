import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import sessionmaker

from utilities.constants import POSTGRES_DATABASE_URL

try:
    
    db_string = create_engine(POSTGRES_DATABASE_URL)
    Session = sessionmaker(bind=db_string)
    base = declarative_base()


    def create_database_tables():
        base.metadata.create_all(bind=db_string)


except Exception as err:
    raise Exception(f'{err}')


class SessionHandler:
    def __init__(self):
        self.session_obj = None

        try:
            self.session_obj = Session()
            self.session_obj.begin()
            return
        except Exception as err:
            raise Exception(f'Unable to create Session : {err}')

    def get_active_session(self):
        return self.session_obj

    def begin(self, subtransactions=False, nested=False):
        if not self.session_obj.is_active:
            self.session_obj.begin()

    def commit(self):
        if self.session_obj.is_active:
            self.session_obj.commit()

    def rollback(self):
        self.session_obj.rollback()

    def close(self):
        self.session_obj.close()
