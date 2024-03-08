import os

from sqlmodel import create_engine

if not os.path.exists("data"):
    os.makedirs("data")


def get_engine():
    return create_engine(
        "sqlite:///data/db.sqlite", connect_args={"check_same_thread": False}, echo=True
    )
