"""
Denna fil hämtar info för tvserier, den använder IDn för tv-serier som samlats in av fetch_ids.

"""

import csv
import json
import logging
from datetime import datetime, timezone
from typing import Any

# Hanterar kontakt med API
from api_client import error_handling, rate_limit

logger = logging.getLogger(__name__)

base_url = "https://api.themoviedb.org/3/tv"


def append_json_line(data: dict[str, Any], filename: str) -> None:
    with open(filename, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

def load_show_ids(filename: str = "data/raw/show_ids.csv") -> list[int]:
    ids = []
    with open(filename, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.append(int(row["id"]))
    return ids

def main():
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler("app.log", mode="a", encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
        handlers=[console_handler, file_handler]
    )
    
    open("data/raw/show_details.jsonl", "w").close()  # tömmer filen så att varje körning börjar om från noll

    show_ids = load_show_ids()
    failed_ids = []

    logger.info("Hämtning startas")

    for series_id in show_ids:
        response = error_handling(f"{base_url}/{series_id}")

        if response is not None:
            details = response.json()
            details["fetched_at"] = datetime.now(timezone.utc).isoformat()  # när datan hämtades
            append_json_line(details, filename="data/raw/show_details.jsonl")

            logger.info("Detaljer för %s sparade", series_id)
        else:
            failed_ids.append(series_id)

        rate_limit()

    if failed_ids:
        logger.warning("Klart. %s serier misslyckades: %s", len(failed_ids), failed_ids)
    else:
        logger.info("Klart. Alla serier hämtades")



if __name__ == "__main__":
    main()