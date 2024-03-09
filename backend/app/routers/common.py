import os

from sqlmodel import create_engine
from fastapi_cache import Coder
from fastapi import Response
from fastapi.responses import RedirectResponse
from typing import Any

if not os.path.exists("data"):
    os.makedirs("data")


def get_engine():
    return create_engine(
        "sqlite:///data/db.sqlite", connect_args={"check_same_thread": False}, echo=True
    )


class XMLCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> bytes:
        return value.body

    @classmethod
    def decode(cls, value: bytes) -> Any:
        return Response(content=value, media_type="application/xml")


class RedirectResponseCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> bytes:
        return value.headers["location"].encode()

    @classmethod
    def decode(cls, value: bytes) -> Any:
        return RedirectResponse(value.decode())
