from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import json
import subprocess
import os
import traceback

app = Flask(__name__)

# Function to apply red color to rows where 'Sprawdzenie' is not OK (green tick)
def highlight_errors(row):
    return ['background-color: #ffcccc' if row['OK?'] != '✅' else '' for _ in row]

# Function to check sums and update 'Sprawdzenie' column
def check_sums(df):
    media_columns = ['Centralne ogrzewanie wg zużycia [zł]',
                     'Koszty stałe i wspólne wytworzenia co i cw [zł]',
                     'Podgrzanie wody [zł]',
                     'Zimna woda i kanalizacja [zł]',
                     'Wyrównanie zimna woda [zł]']

    media_sum = df[media_columns].sum(axis=1)
    total_sum = media_sum + df['Razem czynsz [zł]']

    media_difference = abs(media_sum - df['Razem media [zł]'])
    total_difference = abs(total_sum - df['RAZEM OPŁATY [zł]'])

    df['OK?'] = 'OK'
    mask = (media_difference >= 0.01) | (total_difference >= 0.01)
    df.loc[mask, 'OK?'] = 'Różnica ' + (total_sum - df['RAZEM OPŁATY [zł]']).round(2).astype(str) + ' zł'

    return df

# Route to summary
@app.route('/')
def summary():
    csv_file = 'rachunki_focha.csv'
    
    if not os.path.exists(csv_file) or os.path.getsize(csv_file) == 0:
        return render_template('table.html', tables="<p>Brak danych</p>", page="summary", chart_data=json.dumps({}))

    # Read the CSV file into a DataFrame
    df = pd.read_csv(csv_file)

    if df.empty:
        return render_template('table.html', tables="<p>Brak danych</p>", page="summary", chart_data=json.dumps({}))

    # Convert 'Okres' column to datetime
    df['Okres'] = pd.to_datetime(df['Okres'], errors='coerce')
    
    # Create display version of 'Okres' in YYYY-MM format
    df['Okres_display'] = df['Okres'].dt.strftime('%Y-%m')

    # Print column names for debugging
    print("Columns in DataFrame:", df.columns.tolist())

    # Calculate the sum of water-related expenses and create a new column 'Woda'
    water_columns = ['Podgrzanie wody [zł]', 'Zimna woda i kanalizacja [zł]', 'Wyrównanie zimna woda [zł]']
    df['Woda'] = df[water_columns].sum(axis=1)

    # Calculate water usage
    usage_columns = ['Licznik ciepłej wody', 'Licznik zimnej wody']
    df['Zużycie wody'] = df[usage_columns].sum(axis=1)

    # Calculate the sum of heating-related expenses and create a new column 'CO'
    heating_columns = ['Centralne ogrzewanie wg zużycia [zł]', 'Koszty stałe i wspólne wytworzenia co i cw [zł]']
    df['CO'] = df[heating_columns].sum(axis=1)

    # Process electricity data
    df['Zużycie prądu'] = df['Zużycie prądu'].fillna(0).astype(float)
    df['Koszt prądu'] = df['Koszt prądu'].fillna(0).astype(float)

    # Add internet bill (constant 60 zł)
    df['🌐 Internet'] = '65.00 zł'

    # Create display columns
    df['🏠 Czynsz'] = df['Razem czynsz [zł]'].round(2).astype(str) + ' zł'
    df['Zużycie wody'] = df['Zużycie wody'].round(2).astype(str) + ' m3'
    df['💧 Woda'] = df['Woda'].round(2).astype(str) + ' zł'
    df['Zużycie CO'] = df['Licznik CO'].round(2).astype(str) + ' GJ'
    df['🌡️ CO'] = df['CO'].round(2).astype(str) + ' zł'
    df['Zużycie prąd'] = df['Zużycie prądu'].round(2).astype(str) + ' kWh'
    df['⚡ Prąd'] = df['Koszt prądu'].round(2).astype(str) + ' zł'
    df['Opłaty ASM'] = df['RAZEM OPŁATY [zł]'].round(2).astype(str) + ' zł'

    # Select columns for table display
    display_columns = ['Okres', '🏠 Czynsz', 'Zużycie wody', '💧 Woda', 'Zużycie CO', '🌡️ CO', 'Opłaty ASM', '⚡ Prąd', '🌐 Internet', 'OK?']
    table_df = df[display_columns]

    # Prepare data for the chart
    chart_columns = ['Okres', '🏠 Czynsz', '💧 Woda', '🌡️ CO', '⚡ Prąd', 'Opłaty ASM']
    chart_data = df[chart_columns].copy()
    
    # Convert timestamps to strings for JSON serialization
    chart_data['Okres'] = chart_data['Okres'].dt.strftime('%m-%Y')
    
    for col in chart_columns[1:]:  # Skip 'Okres'
        chart_data[col] = chart_data[col].str.replace(' zł', '').astype(float)
    
    chart_json = json.dumps({
        'labels': chart_data['Okres'].tolist(),
        'czynsz': chart_data['🏠 Czynsz'].tolist(),
        'woda': chart_data['💧 Woda'].tolist(),
        'co': chart_data['🌡️ CO'].tolist(),
        'prad': chart_data['⚡ Prąd'].tolist(),
        'oplaty_asm': chart_data['Opłaty ASM'].tolist()
    })

    # Prepare the table data (last 6 rows)
    table_df = table_df.head(6)

    # Replace 'OK' with green tick and 'Różnica' with red X
    table_df['OK?'] = table_df['OK?'].apply(lambda x: '✅' if x == 'OK' else '❌')

    # Reset the index to ensure it's removed
    table_df = table_df.reset_index(drop=True)

    # Apply the styling
    styled_df = table_df.style.apply(highlight_errors, axis=1)
    styled_df = styled_df.set_table_styles([
        {'selector': 'th', 'props': [('background-color', '#f8f9fa'), ('color', '#333'), ('font-weight', 'bold')]},
        {'selector': 'td', 'props': [('border', '1px solid #dee2e6')]},
        {'selector': 'tr:nth-of-type(even)', 'props': [('background-color', '#f8f9fa')]},
    ])
    styled_df = styled_df.set_properties(**{'text-align': 'center'})

    # Convert DataFrame to HTML, explicitly hiding the index
    html_table = styled_df.hide(axis="index").to_html(classes='table table-hover summary-table', escape=False)

    # Calculate quarterly totals
    def get_season_and_year(date):
        month = date.month
        year = date.year
        
        # Create a sortable quarter key (YYYY.Q format)
        if 9 <= month <= 11:  # Sep-Nov
            return f"{year}-jesień", f"{year}.3"
        elif month == 12:  # December
            return f"{year}-zima", f"{year}.4"
        elif 1 <= month <= 2:  # Jan-Feb
            return f"{year-1}-zima", f"{year-1}.4"
        elif 3 <= month <= 5:  # Mar-May
            return f"{year}-wiosna", f"{year}.1"
        else:  # Jun-Aug
            return f"{year}-lato", f"{year}.2"

    # Create both display and sort keys
    quarter_info = df['Okres'].apply(get_season_and_year)
    df['Quarter'] = quarter_info.apply(lambda x: x[0])
    df['Quarter_sort'] = quarter_info.apply(lambda x: x[1])

    # Convert cost columns to numeric values
    df['Total_ASM'] = df['RAZEM OPŁATY [zł]']
    df['Total_Prad'] = df['Koszt prądu'].fillna(0)
    df['Total_Internet'] = 65  # constant internet cost

    quarterly_totals = df.groupby('Quarter').agg({
        'Total_ASM': 'sum',
        'Total_Prad': 'sum',
        'Total_Internet': 'sum',
        'Quarter_sort': 'first'  # Keep the sort key
    }).round(2)
    
    quarterly_totals['Total'] = quarterly_totals[['Total_ASM', 'Total_Prad', 'Total_Internet']].sum(axis=1)
    
    # Sort by the numeric sort key and drop it from display
    quarterly_totals = quarterly_totals.sort_values('Quarter_sort', ascending=False)
    quarterly_totals = quarterly_totals.drop('Quarter_sort', axis=1)
    
    # Convert quarterly totals to HTML
    quarterly_html = quarterly_totals.to_html(
        classes='table table-hover quarterly-table',
        float_format=lambda x: f'{x:.2f} zł'
    )

    # Use Okres_display for the main table
    df['Okres'] = df['Okres_display']

    return render_template(
        'table.html', 
        tables=html_table, 
        quarterly_tables=quarterly_html,
        page="summary", 
        chart_data=chart_json
    )


# Route to display the full data with "Sprawdzenie"
@app.route('/edit')
def edit_data():
    df = pd.read_csv('rachunki_focha.csv')
    df['Okres'] = pd.to_datetime(df['Okres'], errors='coerce').dt.strftime('%Y-%m')
    
    def create_editable_table(df):
        table_html = '<table class="table table-hover edit-table">'
        # Add header
        table_html += '<thead><tr>'
        for col in df.columns:
            table_html += f'<th>{col}</th>'
        table_html += '</tr></thead>'
        
        # Add body
        table_html += '<tbody>'
        for idx, row in df.iterrows():
            table_html += '<tr>'
            for col in df.columns:
                cell_value = row[col]
                if pd.isna(cell_value):
                    cell_value = ''
                elif isinstance(cell_value, (int, float, np.integer, np.floating)):
                    cell_value = f'{cell_value:.2f}'
                table_html += f'<td class="editable" data-row="{idx}" data-column="{col}">{cell_value}</td>'
            table_html += '</tr>'
        table_html += '</tbody></table>'
        return table_html

    html_table = create_editable_table(df)
    
    return render_template('table.html', tables=html_table, page="edit")


@app.route('/update_cell', methods=['POST'])
def update_cell():
    row = int(request.form['row'])
    column = request.form['column']
    value = request.form['value']
    
    df = pd.read_csv('rachunki_focha.csv')
    
    # Convert value to the appropriate type
    original_type = df[column].dtype
    if pd.api.types.is_numeric_dtype(original_type):
        try:
            value = float(value)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid numeric value'})
    
    df.at[row, column] = value
    
    # Recalculate 'Sprawdzenie'
    df = check_sums(df)
    
    # Save updated DataFrame
    df.to_csv('rachunki_focha.csv', index=False)
    
    # Return updated 'OK?' value for the row
    return jsonify({
        'status': 'success',
        'sprawdzenie': df.at[row, 'OK?']
    })


@app.route('/update_bills', methods=['POST'])
def update_bills():
    try:
        print("Attempting to run get_bills_data.py...")
        result = subprocess.run(['python', 'get_bills_data.py'], capture_output=True, text=True, check=True)
        print("get_bills_data.py output:", result.stdout)
        return jsonify({'status': 'success', 'message': 'Bills added successfully', 'output': result.stdout})
    except subprocess.CalledProcessError as e:
        print("Error running get_bills_data.py:", e)
        print("Error output:", e.stderr)
        return jsonify({'status': 'error', 'message': 'Error adding bills', 'output': e.stderr})
    except Exception as e:
        print("Unexpected error:", str(e))
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': 'Unexpected error occurred', 'output': str(e)})

if __name__ == '__main__':
    app.run(debug=True)