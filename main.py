from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db, Utilities
from services.service import get_summary, get_all_data, settle_period
from pydantic import BaseModel

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

@app.get('/edit')
async def edit(request: Request, db: Session = Depends(get_db)):
    all_data = get_all_data(db)
    return templates.TemplateResponse(
        'edit.html',
        {'request': request, 'all_data': all_data}
    )

@app.get('/settle')
async def settle(request: Request, year: int, period: str, advance: float, pax: int, db: Session = Depends(get_db)):
    settlement = settle_period(db, year, period, advance, pax)
    return templates.TemplateResponse(
        'settle.html',
        {'request': request, 'settlement': settlement}
    )

class UpdateCellRequest(BaseModel):
    id: int
    field: str
    value: float

@app.post('/update_cell')
async def update_cell(update: UpdateCellRequest, db: Session = Depends(get_db)):
    utility = db.query(Utilities).filter(Utilities.id == update.id).first()
    if not utility:
        raise HTTPException(status_code=404, detail="Record not found")

    # List of allowed fields to prevent arbitrary updates
    allowed_fields = [
        'maintenance_cost',
        'heating_usage',
        'hotwater_usage',
        'coldwater_usage',
        'heating_cost',
        'heating_common_cost',
        'water_heating_cost',
        'water_and_sewage_cost',
        'electricity_usage',
        'electricity_cost',
        'internet_cost'
    ]

    if update.field not in allowed_fields:
        raise HTTPException(status_code=400, detail="Invalid field")

    setattr(utility, update.field, update.value)
    db.commit()

    return {"status": "success", "message": f"Updated {update.field} to {update.value}"}
