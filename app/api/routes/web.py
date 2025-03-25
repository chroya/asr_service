from fastapi import APIRouter, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

@router.get("", response_class=HTMLResponse)
async def web_index(request: Request):
    """
    Web界面首页
    """
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/transcribe", response_class=HTMLResponse)
async def web_transcribe(request: Request):
    """
    转写页面
    """
    return templates.TemplateResponse("transcribe.html", {"request": request})

@router.get("/tasks", response_class=HTMLResponse)
async def web_tasks(request: Request):
    """
    任务列表页面
    """
    return templates.TemplateResponse("tasks.html", {"request": request})

@router.get("/task/{task_id}", response_class=HTMLResponse)
async def web_task_detail(request: Request, task_id: str):
    """
    任务详情页面
    """
    return templates.TemplateResponse("task_detail.html", {"request": request, "task_id": task_id}) 