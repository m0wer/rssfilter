import os

from sqlmodel import create_engine

if not os.path.exists("data"):
    os.makedirs("data")

engine = create_engine("sqlite:///data/db.sqlite", echo=True)
