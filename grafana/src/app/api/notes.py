from app.api import crud
from app.api.models import NoteDB, NoteSchema
from fastapi import APIRouter, HTTPException, Path
from typing import List 
from datetime import datetime as dt
import logging

router = APIRouter()
logger = logging.getLogger("app")


@router.post("/", response_model=NoteDB, status_code=201)
async def create_note(payload: NoteSchema):
    logger.info(f"Создание заметки: {payload.title}")
    note_id = await crud.post(payload)
    created_date = dt.now().strftime("%Y-%m-%d %H:%M")

    response_object = {
        "id": note_id,
        "title": payload.title,
        "description": payload.description,
        "completed": payload.completed,
        "created_date": created_date,
    }
    return response_object

@router.get("/{id}/", response_model=NoteDB)
async def read_note(id: int = Path(..., gt=0),):
    logger.info(f"Чтение заметки id={id}")
    note = await crud.get(id)
    if not note:
        logger.warning(f"Заметка id={id} не найдена")
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@router.get("/", response_model=List[NoteDB])
async def read_all_notes():
    logger.info("Чтение всех заметок")
    return await crud.get_all()

@router.put("/{id}/", response_model=NoteDB)
async def update_note(payload:NoteSchema,id:int=Path(...,gt=0)): #Ensures the input is greater than 0
    logger.info(f"Обновление заметки id={id}")
    note = await crud.get(id)
    if not note:
        logger.warning(f"Заметка id={id} не найдена для обновления")
        raise HTTPException(status_code=404, detail="Note not found")
    note_id = await crud.put(id, payload)
    response_object = {
        "id": note_id,
        "title": payload.title,
        "description": payload.description,
        "completed": payload.completed,
    }
    return response_object

#DELETE route
@router.delete("/{id}/", response_model=NoteDB)
async def delete_note(id:int = Path(...,gt=0)):
    logger.info(f"Удаление заметки id={id}")
    note = await crud.get(id)
    if not note:
        logger.warning(f"Заметка id={id} не найдена для удаления")
        raise HTTPException(status_code=404, detail="Note not found")
    await crud.delete(id)

    return note
