from sqlalchemy import Date, Numeric, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from datetime import date
from decimal import Decimal

DATABASE_URL = 'sqlite:///instance/utilities.db'

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

class Base(DeclarativeBase):
    pass

class Utilities(Base):
    __tablename__ = 'utilities'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[date] = mapped_column(Date, unique=True, index=True)

    heating_usage: Mapped[float | None]
    hotwater_usage: Mapped[float | None]
    coldwater_usage: Mapped[float | None]

    heating_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    heating_common_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    water_heating_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    water_and_sewage_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    maintenance_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    internet_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    
    electricity_usage: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    electricity_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    def __repr__(self):
        return f"Utilities(id={self.id}, month={self.month}"

    