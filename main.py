from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from services.summary import get_summary, get_all_data

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')



@app.get('/')
async def root(request: Request, db: Session = Depends(get_db)):
    summary_data = get_summary(db, limit=12)
    return templates.TemplateResponse(
        'index.html',
        {'request': request, 'summary_data': summary_data}
    )

@app.get('/all')
async def all(request: Request, db: Session = Depends(get_db)):
    all_data = get_all_data(db)
    return templates.TemplateResponse(
        'all.html',
        {'request': request, 'all_data': all_data}
    )