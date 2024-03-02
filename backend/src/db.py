from sqlmodel import create_engine

engine = create_engine("sqlite:///db.sqlite", echo=True)
