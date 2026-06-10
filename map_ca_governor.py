import requests
import pandas as pd
import plotly.express as px


RACE_ID = 79777
OUTPUT_FILE = "ca_governor_county_map.html"

CA_COUNTY_FIPS = {
    "Alameda": "06001", "Alpine": "06003", "Amador": "06005", "Butte": "06007",
    "Calaveras": "06009", "Colusa": "06011", "Contra Costa": "06013",
    "Del Norte": "06015", "El Dorado": "06017", "Fresno": "06019",
    "Glenn": "06021", "Humboldt": "06023", "Imperial": "06025", "Inyo": "06027",
    "Kern": "06029", "Kings": "06031", "Lake": "06033", "Lassen": "06035",
    "Los Angeles": "06037", "Madera": "06039", "Marin": "06041",
    "Mariposa": "06043", "Mendocino": "06045", "Merced": "06047",
    "Modoc": "06049", "Mono": "06051", "Monterey": "06053", "Napa": "06055",
    "Nevada": "06057", "Orange": "06059", "Placer": "06061", "Plumas": "06063",
    "Riverside": "06065", "Sacramento": "06067", "San Benito": "06069",
    "San Bernardino": "06071", "San Diego": "06073", "San Francisco": "06075",
    "San Joaquin": "06077", "San Luis Obispo": "06079", "San Mateo": "06081",
    "Santa Barbara": "06083", "Santa Clara": "06085", "Santa Cruz": "06087",
    "Shasta": "06089", "Sierra": "06091", "Siskiyou": "06093", "Solano": "06095",
    "Sonoma": "06097", "Stanislaus": "06099", "Sutter": "06101", "Tehama": "06103",
    "Trinity": "06105", "Tulare": "06107", "Tuolumne": "06109", "Ventura": "06111",
    "Yolo": "06113", "Yuba": "06115",
}


def fetch_results():
    url = f"https://civicapi.org/api/v2/race/{RACE_ID}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def get_regions(data):
    region_results = data.get("region_results", {})

    if isinstance(region_results, dict):
        return [r for r in region_results.values() if isinstance(r, dict)]

    if isinstance(region_results, list):
        return [r for r in region_results if isinstance(r, dict)]

    return []


def build_county_winner_df(data):
    rows = []

    for region in get_regions(data):
        if region.get("type") != "County":
            continue

        county_name = region.get("name")

        candidates = region.get("candidates", [])
        if not candidates:
            continue

        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.get("votes") or 0,
            reverse=True
        )

        winner = sorted_candidates[0]
        runner_up = sorted_candidates[1] if len(sorted_candidates) > 1 else None

        winner_votes = winner.get("votes") or 0
        runner_up_votes = runner_up.get("votes") or 0 if runner_up else 0

        rows.append({
            "county_name": county_name,
            "fips": CA_COUNTY_FIPS.get(county_name),
            "winner": winner.get("name"),
            "winner_party": winner.get("party"),
            "winner_votes": winner_votes,
            "winner_percent": winner.get("percent"),
            "runner_up": runner_up.get("name") if runner_up else None,
            "runner_up_votes": runner_up_votes,
            "margin_votes": winner_votes - runner_up_votes,
            "percent_reporting": region.get("percent_reporting"),
        })

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["fips"])

    return df


def make_map(df):
    geojson_url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    counties_geojson = requests.get(geojson_url).json()

    fig = px.choropleth(
        df,
        geojson=counties_geojson,
        locations="fips",
        color="winner",
        scope="usa",
        hover_name="county_name",
        hover_data={
            "fips": False,
            "winner": True,
            "winner_party": True,
            "winner_votes": ":,",
            "winner_percent": True,
            "runner_up": True,
            "runner_up_votes": ":,",
            "margin_votes": ":,",
            "percent_reporting": True,
        },
        title="California Governor Primary — County Winners",
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False
    )

    fig.write_html(OUTPUT_FILE)

    print(f"Map written to: {OUTPUT_FILE}")


def main():
    data = fetch_results()
    df = build_county_winner_df(data)

    print("County rows:", len(df))
    print(df[["county_name", "winner", "winner_votes", "winner_percent"]].head())

    make_map(df)


if __name__ == "__main__":
    main()