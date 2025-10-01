from sqlalchemy.orm import Session
from db import Utilities
from decimal import Decimal

def _as_money(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal(0)

def get_all_data(db: Session):
    rows = db.query(Utilities).order_by(Utilities.month.desc()).all()
    return rows

def get_summary(db: Session, limit: int = None):
    rows = (
        db.query(Utilities)
        .order_by(Utilities.month.desc())
        .limit(limit)
        .all()
    )
    
    summary = []

    for row in rows:
        month = row.month
        maintenance = _as_money(row.maintenance_cost)
        heating = _as_money(row.heating_cost) + _as_money(row.heating_common_cost)
        water = _as_money(row.water_and_sewage_cost) + _as_money(row.water_heating_cost)
        electrcity = _as_money(row.electricity_cost)
        internet = _as_money(row.internet_cost)
        asm = maintenance + heating + water
        total = asm + electrcity + internet

        summary.append({
            'month': month,
            'maintenance': maintenance,
            'heating': heating,
            'water': water,
            'electrcity': electrcity,
            'internet': internet,
            'asm': asm,
            'total': total,
        })

    return summary