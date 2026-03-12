from datetime import date, datetime
import pandas as pd
import requests
import os


# SHEETY_ENDPOINT_REGULAR_EXPENSES = "https://api.sheety.co/6b500d383340c356b1a7995e68cc95e4/budget/regularExpenses"
# SHEETY_ENDPOINT_EXPENSES = "https://api.sheety.co/6b500d383340c356b1a7995e68cc95e4/budget/expenses"

# 1. Configuration
EXPENSES_URL = "https://api.sheety.co/6b500d383340c356b1a7995e68cc95e4/budget/regularExpenses"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSe-EEdHd0JEmtdcH0hdeM-dvx0DAZwUgHTZvsST8DqjHg1BRw/formResponse"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = ""
DATE_ENTRY_ID = "entry.858835467"  # The ID for your Date field

# responseSheety = requests.get(url=SHEETY_ENDPOINT_REGULAR_EXPENSES)
# responseSheety.raise_for_status()
# data = responseSheety.json()
# print(data)


# MAPPING (Form ID : CSV Column Name)
# Make sure these match your CSV headers exactly!
FIELD_MAP = {
    "entry.1184823503": "item",
    "entry.2098795030": "amount",
    "entry.1548477373": "category"
}

#Getting data via Sheety request from Regular Expenses Sheet
# 2. Make a GET request to the Sheety API
def get_data_from_sheety():
    global CSV_FILE
    global BASE_DIR
    try:
        response = requests.get(url=EXPENSES_URL)
        response.raise_for_status()
        data = response.json()
        sheet_data = next(iter(data.values()))
        df_sheety = pd.DataFrame(sheet_data)
        CSV_FILE = os.path.join(BASE_DIR, f'RegularExpenses{date.today()}.csv')
        df_sheety.to_csv(CSV_FILE, index=False)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Sheety API: {e}")
    except KeyError:
        print("Error: Could not find the expected data structure in the Sheety response. Check your sheet name.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def process_and_send():
    time_now = datetime.now()
    # Read the CSV
    try:
        df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
    except UnicodeDecodeError:
        df = pd.read_csv(CSV_FILE, encoding='windows-1251')

    for index, row in df.iterrows():
        # Build the payload dynamically
        payload = {}

        for entry_id, csv_column in FIELD_MAP.items():
            # Match the Form ID to the data in that CSV column
            payload[entry_id] = row[csv_column]
            # print(row['Item'])

        # Add the current date (per your requirement)
        payload[DATE_ENTRY_ID] = time_now.strftime('%Y-%m-%d')

        # Send the data
        try:
            response = requests.post(FORM_URL,
                                     data=payload)

            if response.status_code == 200:
                print(f"Row {index + 1}: Successfully sent {row[FIELD_MAP['entry.1184823503']]}")
                with open("log.txt",
                          "a",
                          encoding='utf-8') as file:
                    file.write(f"{time_now}: Row {index + 1}: Successfully sent {row[FIELD_MAP['entry.1184823503']]}\n")
            else:
                print(f"{time_now}: Row {index + 1}: Failed with status {response.status_code}")
                with open("log.txt",
                          "a",
                          encoding='utf-8') as file:
                    file.write(f"Row {index + 1}: Failed with status {response.status_code}\n")
        except Exception as e:
            print(f"Row {index + 1}: Connection Error: {e}")


if __name__ == "__main__":
    get_data_from_sheety()
    process_and_send()


####ALTERNATIVE TO FILL THE SHEET DIRECTLY (NOT Vfillin form)
# for value in data["regularExpenses"]:
#     body = {
#         "expense": {
#             "purchaseDate": ,
#             "item": value["item"],
#             "amount": value["amount"],
#             "category": value["category"]
#         }
#     }
#     response = requests.post(url=SHEETY_ENDPOINT_EXPENSES,
#                              JSON=body)
#     with open("log.txt", "a", encoding='utf-8') as file:
#
#         if response.status_code == 200:
#             file.write(f"{time_now}: Success! The request was successful. Adding {body["expense"]["item"]} with a value of: {body["expense"]["amount"]}\n")
#         else:
#             file.write(f"Request failed with status code: {response.status_code} Failed when tried to add {body["expense"]["item"]} with a value of: {body["expense"]["amount"]}\n")


