import os
import json
from datetime import datetime

import pytz
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


RACE_ID = 83063

SHEET_NAME = "Maine Senate Results"
SUMMARY_TAB_NAME = "Statewide Summary"


def convert_utc_to_edt(utc_timestamp):
    if not utc_timestamp:
        return "Unknown"

    utc_time = datetime.fromisoformat(
        utc_timestamp.replace("Z", "+00:00")
    )

    eastern = pytz.timezone("America/New_York")
    eastern_time = utc_time.astimezone(eastern)

    return eastern_time.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def current_sheet_update_times():
    utc_now = datetime.utcnow().isoformat() + "Z"

    eastern = pytz.timezone("America/New_York")
    edt_now = datetime.now(eastern).strftime("%Y-%m-%d %I:%M:%S %p %Z")

    return utc_now, edt_now


def fetch_results():
    url = f"https://civicapi.org/api/v2/race/{RACE_ID}"

    resp = requests.get(url)
    resp.raise_for_status()

    return resp.json()


def build_summary_df(data):
    rows = []

    api_last_updated_utc = data.get("last_updated")
    api_last_updated_edt = convert_utc_to_edt(api_last_updated_utc)

    sheet_updated_utc, sheet_updated_edt = current_sheet_update_times()

    for c in data.get("candidates", []):
        rows.append({
            "race_id": RACE_ID,
            "election_name": data.get("election_name"),
            "candidate_name": c.get("name"),
            "party": c.get("party"),
            "votes": c.get("votes"),
            "percent": c.get("percent"),
            "race_percent_reporting": data.get("percent_reporting"),
            "api_last_updated_utc": api_last_updated_utc,
            "api_last_updated_edt": api_last_updated_edt,
            "sheet_updated_utc": sheet_updated_utc,
            "sheet_updated_edt": sheet_updated_edt,
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(
            by="votes",
            ascending=False
        )

    return df


def get_sheet_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    if service_account_json:
        service_account_info = json.loads(service_account_json)

        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )
    else:
        creds = Credentials.from_service_account_file(
            "service_account.json",
            scopes=scopes
        )

    return gspread.authorize(creds)


def get_or_create_worksheet(sheet, tab_name):
    try:
        return sheet.worksheet(tab_name)

    except gspread.exceptions.WorksheetNotFound:
        return sheet.add_worksheet(
            title=tab_name,
            rows=1000,
            cols=20
        )


def clean_dataframe_for_sheets(df):
    if df.empty:
        return df

    df = df.copy()
    df = df.replace([float("inf"), float("-inf")], "")
    df = df.fillna("")

    return df


def update_worksheet(worksheet, df):
    worksheet.clear()

    df = clean_dataframe_for_sheets(df)

    if df.empty:
        worksheet.update(
            values=[["No data returned"]],
            range_name="A1"
        )
        return

    worksheet.update(
        values=[df.columns.tolist()] + df.values.tolist(),
        range_name="A1"
    )

    worksheet.freeze(rows=1)
    worksheet.set_basic_filter()

    worksheet.format("1:1", {
        "textFormat": {"bold": True},
        "backgroundColor": {
            "red": 0.9,
            "green": 0.9,
            "blue": 0.9
        }
    })


def update_google_sheet():
    data = fetch_results()

    summary_df = build_summary_df(data)

    client = get_sheet_client()
    sheet = client.open(SHEET_NAME)

    summary_ws = get_or_create_worksheet(
        sheet,
        SUMMARY_TAB_NAME
    )

    update_worksheet(summary_ws, summary_df)

    print(f"[{datetime.utcnow().isoformat()}Z] Updated Google Sheet")
    print(f"Summary rows: {len(summary_df)}")
    print(f"Race reporting: {data.get('percent_reporting')}%")
    print(f"API last updated UTC: {data.get('last_updated')}")
    print(f"API last updated EDT: {convert_utc_to_edt(data.get('last_updated'))}")


if __name__ == "__main__":
    update_google_sheet()