"""
Denna fil hämtar IDn för tvserier, som sedan används av fetch_details för att hämta info om varje serie med hjälp av id.
"""

import csv
import logging
import os  # För att kunna accessa filsystemet
from typing import Any

# Hanterar kontakt med API
from api_client import error_handling, rate_limit

logger = logging.getLogger(__name__)

# Parametrar
total_pages = None # Endpointen returnerar sidor, så vi använder värdet från parametern total pages i första sidan för att veta antalet sidor som ska bearbetas.

base_url = "https://api.themoviedb.org/3/discover/tv"
params = {
    'air_date.gte': '1998-01-01', # Vi vill ha alla säsonger under 2000-talet, och om säsong 2 kom i januari 2000 så behöver vi säsong 1 som kom innan 2000-talet för att räkna ut antal dagar väntetid
    'include_adult': 'false',
    'include_null_first_air_dates': 'false',
    'language': 'en-US',
    'sort_by': 'first_air_date.asc',
    'vote_count.gte': 200, # 200 röster är en bra tröskel för att filtrera bort för små serier
    'with_original_language': 'en',
    'without_genres': '10767,10764,16,10762,10763,99', # Måste vara utan mellanrum annars blir det '+' med: "10767%2C+2010764"
        # 10767 = Talk, 10764 = Reality, 16 = Animation, 10762 = Kids, 10763 = News, 99 = Documentary.
    'with_type': '4|2' # 4 = Scripted, 2 = Miniseries.
}
      

# Hämtar antalet sidor som API-svaret anger
def extract_total_pages(response_json: dict[str, Any]) -> int:
    return response_json["total_pages"]

# Hämtar id och name från api-svar
def extract_show_ids(response_json: dict[str, Any]) -> list[tuple[int, str]]: 
    results = response_json["results"]
    return [(show["id"], show["name"]) for show in results]

# Skriver data från api-svar till fil.
def append_show_ids_csv(shows: list[tuple[int, str]], filename: str = "data/raw/show_ids.csv") -> None:
    os.makedirs(os.path.dirname(filename), exist_ok=True) # Skapar data/raw/ om mappen saknas
    file_exists = os.path.exists(filename) # Kollar om filen existerar
    with open(filename, "a", newline="", encoding="utf-8") as f: # öppnar filen eller skapar den om den saknas
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["id", "name"])   # header bara första gången filen skapas
        for show_id, name in shows:
            writer.writerow([show_id, name])


def main():
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler("app.log", mode="a", encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
        handlers=[console_handler, file_handler]
    )

    if os.path.exists("data/raw/show_ids.csv"):
        os.remove("data/raw/show_ids.csv")  # börja om från noll, headern skrivs igen

    page = 1
    total_pages = None
    failed_pages = []

    logger.info("Hämtning startas")

    while total_pages is None or page <= total_pages:
        response = error_handling(base_url, {**params, "page": page})

        if response is not None:
            response_json = response.json()

            if total_pages is None:
                total_pages = extract_total_pages(response_json)

            shows = extract_show_ids(response_json)
            append_show_ids_csv(shows)

            logger.info("IDn från sida %s av %s sparade", page, total_pages)
        else:
            failed_pages.append(page)
            
            # För att undvika evig loop utifall APIet inte returnerar några sidor.
            if total_pages is None:
                logger.error("Första sidan misslyckades, avbryter")
                break
            

        rate_limit()
        page += 1

    if failed_pages:
        logger.warning("Klart. %s sidor misslyckades: %s", len(failed_pages), failed_pages)
    else:
        logger.info("Klart. Alla sidor hämtades")


if __name__ == "__main__":
    main()