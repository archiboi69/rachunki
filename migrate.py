import pandas as pd
from db import Utilities, init_db, Session
from datetime import date

df = pd.read_csv('instance/rachunki_focha.csv')

init_db()

mapping = {
    'Okres': 'month',
    'Razem czynsz [zł]': 'maintenance_cost',
    'Licznik CO': 'heating_usage',
    'Licznik ciepłej wody': 'hotwater_usage',
    'Licznik zimnej wody': 'coldwater_usage',
    'Centralne ogrzewanie wg zużycia [zł]': 'heating_cost',
    'Koszty stałe i wspólne wytworzenia co i cw [zł]': 'heating_common_cost',
    'Podgrzanie wody [zł]': 'water_heating_cost',
    'Zimna woda i kanalizacja [zł]': 'water_and_sewage_cost',
    'Wyrównanie zimna woda [zł]': 'water_and_sewage_level',
    'Zużycie prądu': 'electricity_usage',
    'Koszt prądu': 'electricity_cost',
    'OK?': 'ok',
}

df = df.rename(columns=mapping)
df['month'] = pd.to_datetime(df['month'], errors='coerce').dt.to_period('M').dt.start_time.dt.date

for index, row in df.iterrows():
    if row['ok'] and row['ok'] != 'OK':
        differnce = row['ok'].split(" ")[1]
        updated_cost = row['water_and_sewage_cost'] + float(differnce)
        df.at[index, 'water_and_sewage_cost'] = updated_cost

df['water_and_sewage_cost'] = (df['water_and_sewage_cost'] + df['water_and_sewage_level']).round(2)

threshold = date(2025, 6, 1)
df['internet_cost'] = df['month'].apply(lambda d: 65 if d >= threshold else 60)

records = df.to_dict(orient='records')

with Session() as session:
    for record in reversed(records):
        month = record['month']
        utility = session.query(Utilities).filter_by(month=month).one_or_none()

        if not utility:
            utility = Utilities(month=month)
            session.add(utility)

        utility.heating_usage = record['heating_usage']
        utility.hotwater_usage = record['hotwater_usage']
        utility.coldwater_usage = record['coldwater_usage']
        utility.heating_cost = record['heating_cost']
        utility.heating_common_cost = record['heating_common_cost']
        utility.water_heating_cost = record['water_heating_cost']
        utility.water_and_sewage_cost = record['water_and_sewage_cost']
        utility.maintenance_cost = record['maintenance_cost']
        utility.internet_cost = record['internet_cost']
        utility.electricity_usage = record['electricity_usage']
        utility.electricity_cost = record['electricity_cost']

    session.commit()
    session.close()