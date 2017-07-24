from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func


Base = declarative_base()


def construct(obj, initial_data, kwargs):
    for dictionary in initial_data:
        for key in dictionary:
            setattr(obj, key, dictionary[key])
    for key in kwargs:
        setattr(obj, key, kwargs[key])


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
        construct(self, initial_data, kwargs)

    def __repr__(self):
        return "Ticker(exchange={}, coin={}, last={}, timestamp={})" \
               .format(self.exchange, self.coin, self.last, self.timestamp)

    @staticmethod
    def peak(sess, coin, start_time=None, now=None):
        query = Ticker.at_time(
            sess.query(func.max(Ticker.last)).filter(Ticker.coin == coin),
            now)
        if start_time:
            query = query.filter(Ticker.timestamp > start_time)
        res = query.first()
        return res[0] if res else None

    @staticmethod
    def current_ask(sess, coin, now=None):
        query = Ticker.at_time(
            sess.query(Ticker.ask)
                .filter(Ticker.coin == coin)
                .order_by(Ticker.timestamp.desc()),
            now)
        ask = query.first()
        return ask[0] if ask else None

    @staticmethod
    def at_time(query, now=None):
        if now is None:
            return query
        return query.filter(Ticker.timestamp <= now)


def create_db(db_string):
    engine = create_engine(db_string)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    return engine


def new_session(db_engine):
    DBSession = sessionmaker(bind=db_engine)
    return DBSession()
