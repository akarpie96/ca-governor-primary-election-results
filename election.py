import time
from datetime import datetime
import pytz

import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


RACE_ID = 83063

SERVICE_ACCOUNT_FILE = "service_account.json"

SHEET_NAME = "Maine Senate Results"
COUNTY_TAB_NAME = "Live Results by County"
SUMMARY_TAB_NAME = "Statewide Summary"

REFRESH_SECONDS = 60


def convert_utc_to_edt(utc_timestamp):
    if not utc_timestamp:
        return "Unknown"

    utc_time = datetime.fromisoformat(
        utc_timestamp.replace("Z", "+00:00")
    )

    eastern = pytz.timezone("America/New_York")
    eastern_time = utc_time.astimezone(eastern)

    return eastern_time.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def fetch_results():
    url = f"https://civicapi.org/api/v2/race/{RACE_ID}"

    resp = requests.get(url)
    resp.raise_for_status()

    return resp.json()


def build_county_df(data):
    rows = []

    last_updated = data.get("last_updated")
    last_updated_edt = convert_utc_to_edt(last_updated)

    region_results = data.get("region_results", {})
    regions = region_results.values() if isinstance(region_results, dict) else region_results

    for region in regions:
        if not isinstance(region, dict):
            continue

        if region.get("type") != "County":
            continue

        for c in region.get("candidates", []):
            rows.append({
                "race_id": RACE_ID,
                "election_name": data.get("election_name"),
                "region_name": region.get("name"),
                "region_type": region.get("type"),
                "candidate_name": c.get("name"),
                "party": c.get("party"),
                "votes": c.get("votes"),
                "percent": c.get("percent"),
                "percent_reporting": region.get("percent_reporting"),
                "last_updated_utc": last_updated,
                "last_updated_edt": last_updated_edt,
            })

    return pd.DataFrame(rows)


def build_summary_df(data):
    rows = []

    last_updated = data.get("last_updated")
    last_updated_edt = convert_utc_to_edt(last_updated)

    for c in data.get("candidates", []):
        rows.append({
            "race_id": RACE_ID,
            "election_name": data.get("election_name"),
            "candidate_name": c.get("name"),
            "party": c.get("party"),
            "votes": c.get("votes"),
            "percent": c.get("percent"),
            "race_percent_reporting": data.get("percent_reporting"),
            "last_updated_utc": last_updated,
            "last_updated_edt": last_updated_edt,
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

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=scopes
    )

    return gspread.authorize(creds)


def get_or_create_worksheet(sheet, tab_name):
    try:
        return sheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        return sheet.add_worksheet(
            title=tab_name,
            rows=5000,
            cols=20
        )


def update_worksheet(worksheet, df):
    worksheet.clear()

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


def update_google_sheet():
    data = fetch_results()

    county_df = build_county_df(data)
    summary_df = build_summary_df(data)

    county_df.to_csv(
        "maine_senate_county_results.csv",
        index=False
    )

    summary_df.to_csv(
        "maine_senate_statewide_summary.csv",
        index=False
    )

    client = get_sheet_client()
    sheet = client.open(SHEET_NAME)

    county_ws = get_or_create_worksheet(
        sheet,
        COUNTY_TAB_NAME
    )

    summary_ws = get_or_create_worksheet(
        sheet,
        SUMMARY_TAB_NAME
    )

    update_worksheet(county_ws, county_df)
    update_worksheet(summary_ws, summary_df)

    print()
    print(f"[{datetime.utcnow().isoformat()}] Updated Google Sheet")
    print(f"County rows: {len(county_df)}")
    print(f"Summary rows: {len(summary_df)}")
    print(f"Race reporting: {data.get('percent_reporting')}%")
    print(f"Last updated UTC: {data.get('last_updated')}")
    print(f"Last updated EDT: {convert_utc_to_edt(data.get('last_updated'))}")


if __name__ == "__main__":
    while True:
        try:
            update_google_sheet()
        except Exception as e:
            print()
            print(f"ERROR: {e}")

        print(f"Sleeping {REFRESH_SECONDS} seconds...")
        print()

        time.sleep(REFRESH_SECONDS)