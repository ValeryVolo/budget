from datetime import date, datetime
import pandas as pd
import requests
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('budget_sync.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 1. Configuration
EXPENSES_URL = "https://api.sheety.co/6b500d383340c356b1a7995e68cc95e4/budget/regularExpenses"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSe-EEdHd0JEmtdcH0hdeM-dvx0DAZwUgHTZvsST8DqjHg1BRw/formResponse"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = ""
DATE_ENTRY_ID = "entry.858835467"  # The ID for your Date field

# MAPPING (Form ID : CSV Column Name)
# Make sure these match your CSV headers exactly!
FIELD_MAP = {
    "entry.1184823503": "item",
    "entry.2098795030": "amount",
    "entry.1548477373": "category"
}

def get_data_from_sheety():
    """Fetch data from Sheety API and save to CSV"""
    global CSV_FILE
    logger.info("=" * 60)
    logger.info("Starting Sheety API fetch...")
    logger.info(f"Target URL: {EXPENSES_URL}")
    
    try:
        response = requests.get(url=EXPENSES_URL, timeout=10)
        logger.info(f"Sheety API Response Status: {response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Raw API response keys: {list(data.keys())}")
        
        # Get the first (and usually only) key from the response
        sheet_data = next(iter(data.values()))
        logger.info(f"Retrieved {len(sheet_data)} rows from Sheety")
        
        if len(sheet_data) == 0:
            logger.warning("No data returned from Sheety API - empty sheet")
            return False
        
        # Log sample data
        logger.info(f"Sample first row: {sheet_data[0]}")
        logger.info(f"Columns in data: {list(sheet_data[0].keys())}")
        
        df_sheety = pd.DataFrame(sheet_data)
        CSV_FILE = os.path.join(BASE_DIR, f'RegularExpenses{date.today()}.csv')
        df_sheety.to_csv(CSV_FILE, index=False)
        
        logger.info(f"CSV file created: {CSV_FILE}")
        logger.info(f"CSV shape: {df_sheety.shape[0]} rows x {df_sheety.shape[1]} columns")
        logger.info("✓ Sheety API fetch successful")
        return True
        
    except requests.exceptions.Timeout:
        logger.error("Timeout: Sheety API request took too long (>10 seconds)")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection Error: Unable to reach Sheety API - {e}")
        return False
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error: Sheety API returned status {response.status_code}")
        logger.error(f"Response body: {response.text}")
        return False
    except ValueError as e:
        logger.error(f"JSON Decode Error: Invalid JSON response from Sheety - {e}")
        return False
    except KeyError as e:
        logger.error(f"Key Error: Could not find expected data structure in response - {e}")
        logger.error(f"Response keys: {list(data.keys())}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in get_data_from_sheety: {type(e).__name__} - {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def process_and_send():
    """Read CSV and send each row to Google Form"""
    logger.info("=" * 60)
    logger.info("Starting form submission process...")
    
    # Validate CSV file exists
    if not CSV_FILE:
        logger.error("CSV_FILE is empty - get_data_from_sheety() likely failed")
        return False
    
    if not os.path.exists(CSV_FILE):
        logger.error(f"CSV file not found: {CSV_FILE}")
        return False
    
    file_size = os.path.getsize(CSV_FILE)
    logger.info(f"CSV file size: {file_size} bytes")
    
    if file_size == 0:
        logger.error("CSV file is empty - no data to process")
        return False
    
    # Read CSV with encoding fallback
    try:
        try:
            df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
        except UnicodeDecodeError:
            logger.warning("UTF-8 decoding failed, trying windows-1251")
            df = pd.read_csv(CSV_FILE, encoding='windows-1251')
    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    # Validate CSV has required columns
    missing_columns = []
    for csv_column in FIELD_MAP.values():
        if csv_column not in df.columns:
            missing_columns.append(csv_column)
    
    if missing_columns:
        logger.error(f"CSV missing required columns: {missing_columns}")
        logger.error(f"Available columns: {list(df.columns)}")
        return False
    
    logger.info(f"CSV loaded successfully: {len(df)} rows")
    logger.info(f"Columns found: {list(df.columns)}")
    logger.info(f"Sample first row: {df.iloc[0].to_dict()}")
    
    time_now = datetime.now()
    successful_submissions = 0
    failed_submissions = 0
    
    # Submit each row
    for index, row in df.iterrows():
        logger.info(f"Processing row {index + 1}/{len(df)}")
        
        # Build the payload dynamically
        payload = {}
        
        try:
            for entry_id, csv_column in FIELD_MAP.items():
                # Match the Form ID to the data in that CSV column
                payload[entry_id] = str(row[csv_column])
            
            # Add the current date (per your requirement)
            payload[DATE_ENTRY_ID] = time_now.strftime('%Y-%m-%d')
            
            logger.debug(f"  Payload: {payload}")
            
            # Send the data
            response = requests.post(FORM_URL, data=payload, timeout=10)
            
            logger.info(f"  Response status: {response.status_code}")
            logger.debug(f"  Response headers: {dict(response.headers)}")
            
            # Google Forms always returns 200, but we can check response size
            if len(response.text) > 50:  # Successful form typically has larger response
                logger.info(f"  ✓ Row {index + 1}: Successfully submitted {row[FIELD_MAP['entry.1184823503']]}")
                successful_submissions += 1
            else:
                logger.warning(f"  ⚠ Row {index + 1}: Submission may have failed (small response)")
                logger.warning(f"  Response*
