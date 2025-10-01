from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import Utilities, get_db

app = FastAPI()

templates = Jinja2Templates(directory='templates')



@app.get('/')
async def root(request: Request, db: Session = Depends(get_db)):
    utilities = (
        db.query(Utilities)
        .order_by(Utilities.month.desc())
        .limit(6)
        .all()
    )
    return templates.TemplateResponse(
        'index.html',
        {'request': request, 'utilities': utilities}
    )