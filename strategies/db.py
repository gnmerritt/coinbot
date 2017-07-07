from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


Base = declarative_base()


class Ticker(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True)

    exchange = Column(String(20))
    coin = Column(String(10))

    timestamp = Column(DateTime)
    bid = Column(Float)
    ask = Column(Float)
    last = Column(Float)
    volume = Column(Float)

    def __init__(self, *initial_data, **kwargs):
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __repr__(self):
        return "Ticker(exchange={}, coin={}, last={}, timestamp={})" \
               .format(self.exchange, self.coin, self.last, self.timestamp)


def create_db(db_string):
    engine = create_engine(db_string)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    return engine


def new_session(db_engine):
    DBSession = sessionmaker(bind=db_engine)
    return DBSession()
