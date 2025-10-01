import os
import re
import pdfplumber
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def extract_pdf_data(pdf_path):
    # If it's a PDF, proceed with extracting data
    with pdfplumber.open(pdf_path) as pdf:
        extracted_text = ''
        for page in pdf.pages:
            extracted_text += page.extract_text()

    # Extract period from filename (before first dot)
    filename = os.path.basename(pdf_path)
    period = filename.split('.')[0]
    datetime_period = pd.to_datetime(period, format='%Y-%m', errors='coerce')
    # Initialize the dictionary to store the extracted values
    pdf_data_dict = {'Okres': datetime_period}

    # Patterns for matching the relevant expenses
    patterns = {
        'Razem czynsz [zł]': r'Razem naliczenie czynszu nr NC \S+ płatne do dnia \S+ ([\d,]+)',
        'Licznik CO': r'Razem LCO\s+([\d,]+)',
        'Licznik ciepłej wody': r'Razem LCW\s+([\d,]+)',
        'Licznik zimnej wody': r'Razem LZW\s+([\d,]+)',
        'Centralne ogrzewanie wg zużycia [zł]': r'Centralne ogrzewanie wg zużycia \d+,\d+ GJ \d+,\d+ (\d+,\d+)',
        'Koszty stałe i wspólne wytworzenia co i cw [zł]': r'Koszty stałe i wspólne wytworzenia co i cw \d+,\d+ m2 \d+,\d+ (\d+,\d+)',
        'Podgrzanie wody [zł]': r'Podgrzanie wody \d+,\d+ m3 \d+,\d+ (\d+,\d+)',
        'Zimna woda i kanalizacja [zł]': r'Zimna woda i kanalizacja \d+,\d+ m3 \d+,\d+ (\d+,\d+)',
        'Wyrównanie zimna woda [zł]': r'Niedobory / nadwyżki:\s+(-?[\d,]+)',
        'Razem media [zł]': r'Razem rozliczenie zużycia mediów nr RZM \S+ płatne do dnia \S+ ([\d,]+)',
        'RAZEM OPŁATY [zł]': r'RAZEM OPŁATY od: \S+ do: \S+: ([\d ]+\d+,\d+)',
    }

    # Loop through the patterns and apply regex to extract values
    for key, pattern in patterns.items():
        match = re.search(pattern, extracted_text)
        if match:
            clean_value = match.group(1).replace(' ', '').replace(',', '.')
            pdf_data_dict[key] = float(clean_value)  # Storing as a float directly
        else:
            pdf_data_dict[key] = float('nan')  # Use NaN for missing values

    return pdf_data_dict


def check_sums(month_dict):
    if month_dict is not None:
        # Convert dict to DataFrame
        month_df = pd.DataFrame([month_dict])

        if pd.isna(month_df['Razem czynsz [zł]']).any():
            month_df['OK?'] = 'Brak danych dla "Razem czynsz"'
            return month_df

        if pd.isna(month_df['Razem media [zł]']).any():
            month_df['OK?'] = 'Brak danych dla "Razem media"'
            return month_df

        if pd.isna(month_df['RAZEM OPŁATY [zł]']).any():
            month_df['OK?'] = 'Brak danych dla "RAZEM OPŁATY"'
            return month_df

        # Define media columns and sum them
        media_columns = ['Centralne ogrzewanie wg zużycia [zł]',
                         'Koszty stałe i wspólne wytworzenia co i cw [zł]',
                         'Podgrzanie wody [zł]',
                         'Zimna woda i kanalizacja [zł]',
                         'Wyrównanie zimna woda [zł]']

        media_sum = month_df[media_columns].sum(axis=1).item()
        # Add Razem czynsz to media_sum to get total_sum
        total_sum = media_sum + month_df['Razem czynsz [zł]'].item()

        # Check if the calculated sums match the respective fields
        media_difference = abs(media_sum - month_df['Razem media [zł]'].item())
        total_difference = abs(total_sum - month_df['RAZEM OPŁATY [zł]'].item())

        if media_difference < 0.01 and total_difference < 0.01:
            month_df['OK?'] = 'OK'
        else:
            total_difference_value = round(total_sum - month_df['RAZEM OPŁATY [zł]'].item(), 2)
            month_df['OK?'] = f'Różnica {total_difference_value} zł'

        return month_df
    else:
        return None

def extract_electricity_data(pdf_path):
    # Extract period from filename (YYYY-MM-MM format)
    filename = os.path.basename(pdf_path)
    match = re.search(r'prad-(\d{4}-\d{2}-\d{2})', filename)
    if not match:
        print(f"Invalid electricity bill filename format: {filename}")
        return None

    period = match.group(1)
    year, month1, month2 = period.split('-')

    with pdfplumber.open(pdf_path) as pdf:
        text = ''
        for page in pdf.pages:
            text += page.extract_text()

    # Extract total usage and cost (modify these patterns based on your PDF structure)
    usage_match = re.search(r'Zużycie energii elektrycznej:\s*([\d,]+)', text)
    cost_match = re.search(r'wartość usługi\s*([\d,]+)', text)

    if not usage_match or not cost_match:
        print(f"Could not extract usage or cost from {filename}")
        return None

    total_usage = float(usage_match.group(1).replace(',', '.'))
    total_cost = float(cost_match.group(1).replace(',', '.'))

    # Split usage and cost equally between two months
    monthly_usage = total_usage / 2
    monthly_cost = total_cost / 2

    # Create two monthly records
    records = []
    for month in [month1, month2]:
        record = {
            'Okres': f"{year}-{month}",
            'Zużycie prądu': monthly_usage,
            'Koszt prądu': monthly_cost
        }
        records.append(record)

    return records

def split_electricity_bill(bill_data):
    """Split a bi-monthly electricity bill into two monthly entries."""
    # If bill_data is already a list of monthly records, return it as is
    if isinstance(bill_data, list) and len(bill_data) == 2:
        return bill_data

    # If it's a single dictionary, split it
    if isinstance(bill_data, dict):
        month1 = datetime.strptime(bill_data['Okres'], '%Y-%m-%d')
        month2 = month1 + timedelta(days=32)
        month2 = month2.replace(day=1)

        split_data = []
        for month in [month1, month2]:
            monthly_data = bill_data.copy()
            monthly_data['Okres'] = month.strftime('%Y-%m-%d')
            monthly_data['Zużycie prądu'] = bill_data['Zużycie prądu'] / 2
            monthly_data['Koszt prądu'] = bill_data['Koszt prądu'] / 2
            split_data.append(monthly_data)

        return split_data

    # If it's neither a list nor a dictionary, return None or raise an error
    print(f"Unexpected data format for electricity bill: {type(bill_data)}")
    return None

def update_csv(csv_file, new_data):
    if os.path.exists(csv_file):
        existing_data = pd.read_csv(csv_file)
        existing_data['Okres'] = pd.to_datetime(existing_data['Okres'])
    else:
        existing_data = pd.DataFrame()

    new_df = pd.DataFrame(new_data)
    new_df['Okres'] = pd.to_datetime(new_df['Okres'])

    # Merge new data with existing data, keeping existing data where there's an overlap
    merged_data = pd.concat([existing_data, new_df]).drop_duplicates(subset=['Okres'], keep='first')

    # Sort the DataFrame by 'Okres' in descending order
    merged_data = merged_data.sort_values('Okres', ascending=False)

    # Convert 'Okres' back to string format for saving
    merged_data['Okres'] = merged_data['Okres'].dt.strftime('%Y-%m-%d')

    # Save the updated DataFrame
    merged_data.to_csv(csv_file, index=False)

def process_bills(directory, csv_file):
    all_data = []
    
    for filename in os.listdir(directory):
        if filename.endswith('.pdf'):
            filepath = os.path.join(directory, filename)
            
            if filename.startswith('prad'):
                bill_data = extract_electricity_data(filepath)
                if bill_data:
                    all_data.extend(bill_data)
            else:
                bill_data = extract_pdf_data(filepath)
                checked_data = check_sums(bill_data)
                if checked_data is not None:
                    all_data.append(checked_data.to_dict('records')[0])
    
    update_csv(csv_file, all_data)

# Main execution
csv_file = 'rachunki_focha.csv'
bills_directory = '/Users/michaldeja/Documents/automat_rachunkowy/data'
process_bills(bills_directory, csv_file)