from sqlalchemy.orm import Session
from db import Utilities
from decimal import Decimal
from datetime import date

def _as_money(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal(0)

def _calculate_monthly_costs(row):

    maintenance = _as_money(row.maintenance_cost)
    heating = _as_money(row.heating_cost) + _as_money(row.heating_common_cost)
    water = _as_money(row.water_and_sewage_cost) + _as_money(row.water_heating_cost)
    electricity = _as_money(row.electricity_cost)
    internet = _as_money(row.internet_cost)
    asm = maintenance + heating + water
    total = asm + electricity + internet

    return {
        'maintenance': maintenance,
        'heating': heating,
        'water': water,
        'electricity': electricity,
        'internet': internet,
        'asm': asm,
        'total': total,
        }

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
        item = _calculate_monthly_costs(row)
        item['month'] = row.month
        summary.append(item)

    return summary

def settle_period(db: Session, year, period, advance, pax):

    period_map = {
        "spring": (3, 4, 5),
        "summer": (6, 7, 8),
        "fall": (9, 10, 11),
        "all": range(1,12)
    }

    if period != "winter":
        period_months = [date(year, m, 1) for m in period_map[period]]
    else:
        period_months = [
            date((year - 1), 12, 1),
            date(year, 1, 1),
            date(year, 2, 1)
            ]

    rows = db.query(Utilities).where(Utilities.month.in_(period_months)).all()

    total_cost = sum(_calculate_monthly_costs(row)['total'] for row in rows)
    total_advance = Decimal(advance) * pax * len(rows)
    outstanding = total_cost - total_advance

    return {
        "period" : f"{period} {str(year)}",
        "cost" : total_cost,
        "advance" : total_advance,
        "outstanding" : outstanding,
        "cost_per_person": (total_cost / pax).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP"),
        "advance_per_person": (total_advance / pax).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP"),
        "outstanding_per_person": (outstanding / pax).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
    }