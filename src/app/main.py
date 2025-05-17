from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram
from contextlib import asynccontextmanager
import logging
import sys
import json
import datetime
import os
import time

from app.api import ping, notes
from app.db import engine, metadata, database

# Настройка логирования
class JsonFormatter(logging.Formatter):
    def format(self, record):
        if isinstance(record.msg, dict):
            log_record = record.msg
        else:
            log_record = {"message": str(record.msg)}
        log_record["level"] = record.levelname
        log_record["timestamp"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        log_record["name"] = record.name
        log_record["container"] = os.getenv("SERVICE_NAME", "web")
        log_record["service_name"] = os.getenv("SERVICE_NAME", "web")
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

logger = logging.getLogger("app")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Метрики Prometheus
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total count of HTTP requests",
    ["method", "endpoint", "status_code", "service"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint", "service"],
    buckets=[0.1, 0.5, 1, 2, 5]
)

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
    service_name = os.getenv("SERVICE_NAME", "web")
    start_time = time.time()
    
    base_log = {
        "container": service_name,
        "service_name": service_name,
        "name": "app",
    }
    
    request_log = {
        **base_log,
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3],
        "level": "INFO",
        "method": request.method,
        "url": str(request.url.path),
        "client": request.client.host if request.client else "unknown"
    }
    logger.info(request_log)
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Обновляем метрики Prometheus
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            service=service_name
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
            service=service_name
        ).observe(duration)
        
        response_log = {
            **base_log,
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3],
            "level": "INFO",
            "status_code": response.status_code,
            "url": str(request.url.path),
            "method": request.method,
            "client": request.client.host if request.client else "unknown",
            "duration": round(duration, 3)
        }
        logger.info(response_log)
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        error_log = {
            **base_log,
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3],
            "level": "ERROR",
            "error": str(e),
            "url": str(request.url.path),
            "method": request.method,
            "client": request.client.host if request.client else "unknown",
            "duration": round(duration, 3)
        }
        logger.error(error_log)
        raise

