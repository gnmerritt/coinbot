from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime, Index
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
            now
        )
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

    @staticmethod
    def coins(sess):
        return [t[0] for t in sess.query(Ticker.coin).distinct().all()]


class Balance(Base):
    __tablename__ = "balances"
    __table_args__ = (
        Index("uniq_coins", "name", "coin", "exchange", unique=True),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(12))

    exchange = Column(String(20))
    coin = Column(String(10))

    opened = Column(DateTime)
    last_updated = Column(DateTime)
    balance = Column(Float)

    def __init__(self, *initial_data, **kwargs):
        construct(self, initial_data, kwargs)

    def __repr__(self):
        return "Balance(name={}, coin={}, exchange={}, balance={})" \
               .format(self.name, self.coin, self.exchange, self.balance)

    @staticmethod
    def upsert(sess, balance, **kwargs):
        existing = sess.query(Balance).filter_by(**kwargs).one_or_none()
        now = datetime.utcnow()
        if existing is None:
            existing = Balance(**kwargs)
            existing.opened = now
        existing.balance = balance
        existing.last_updated = now
        sess.add(existing)
        return existing

    @staticmethod
    def remove(sess, **kwargs):
        existing = sess.query(Balance).filter_by(**kwargs).one_or_none()
        if existing:
            sess.delete(existing)


def create_db(db_string):
    engine = create_engine(db_string)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    return engine


def new_session(db_engine):
    DBSession = sessionmaker(bind=db_engine)
    return DBSession()
