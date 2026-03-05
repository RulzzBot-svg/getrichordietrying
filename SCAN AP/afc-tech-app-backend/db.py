from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase



class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base, engine_options={"pool_pre_ping":True, "pool_recycle":300,})
