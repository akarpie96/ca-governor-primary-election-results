import gspread
from google.oauth2.service_account import Credentials

SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_NAME = "Maine Senate Results"
TAB_NAME = "Live Results by County"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=scopes
)

client = gspread.authorize(creds)

sheet = client.open(SHEET_NAME)

try:
    worksheet = sheet.worksheet(TAB_NAME)
except gspread.exceptions.WorksheetNotFound:
    worksheet = sheet.add_worksheet(title=TAB_NAME, rows=1000, cols=20)

worksheet.update(
    values=[["Connected!"]],
    range_name="A1"
)

print("Success! Google Sheet updated.")