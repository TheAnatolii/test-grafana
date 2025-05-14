from fastapi import APIRouter
import logging

router = APIRouter()
logger = logging.getLogger("app")


@router.get("/ping")
async def pong():
    logger.info("Ping endpoint called")
    return {"ping": "pong!"}