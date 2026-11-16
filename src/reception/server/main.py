"""ASGI entry point: ``uvicorn reception.server.main:app``."""

import os

from reception.app_factory import build_assistant
from reception.server.app import create_app

app = create_app(lambda: build_assistant(offline=os.environ.get("RECEPTION_OFFLINE") == "1"))
