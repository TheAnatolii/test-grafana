from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram
from contextlib import asynccontextmanager
import logging
import sys
import json

from app.api import ping, notes
from app.db import engine, metadata, database

# Настройка логирования
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'level': record.levelname,
            'time': self.formatTime(record, self.datefmt),
            'message': record.getMessage(),
            'name': record.name,
        }
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)
        return json.dumps(log_record)

logger = logging.getLogger("app")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.setLevel(logging.INFO)
logger.addHandler(handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()

metadata.create_all(engine)

app = FastAPI(lifespan=lifespan)
Instrumentator().instrument(app).expose(app)

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5173",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["DELETE", "GET", "POST", "PUT"],
    allow_headers=["*"],
)

# Include your routers
app.include_router(ping.router)
app.include_router(notes.router, prefix="/notes")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(json.dumps({
        "method": request.method,
        "url": str(request.url),
        "client": request.client.host
    }))
    try:
        response = await call_next(request)
        logger.info(json.dumps({
            "status_code": response.status_code,
            "url": str(request.url)
        }))
        return response
    except Exception as e:
        logger.error(json.dumps({
            "error": str(e),
            "url": str(request.url)
        }))
        raise

