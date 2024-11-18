import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application


ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent
sys.path.append(str(ROOT_DIR / "apps"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

django_application = get_asgi_application()
from utils.other.websocket import websocket_application


async def application(scope, receive, send):
    if scope["type"] == "http":
        await django_application(scope, receive, send)
    elif scope["type"] == "websocket":
        await websocket_application(scope, receive, send)
    else:
        raise NotImplementedError(f"Unknown scope type {scope['type']}")
