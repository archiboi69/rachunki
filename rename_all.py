import os
import re

folder = '/Users/michaldeja/Documents/automat_rachunkowy/data'

for filename in os.listdir(folder):

    old_path = os.path.join(folder, filename)

    if os.path.isfile(old_path):
        match = re.search(r'(\d{4})\.(\d{2}) Oplaty\.pdf', filename)

        if match:
            year = match.group(1)
            month = match.group(2)

            new_filename = f'{year}-{month}.pdf'

            new_path = os.path.join(folder, new_filename)
            os.rename(old_path, new_path)
            print('Renamed file', old_path,'to', new_path)
