"""
Denna fil hämtar info för tvserier, den använder IDn för tv-serier som samlats in av fetch_ids.

details_progress.txt (skapas om den inte existerar) för att hålla koll på vilka IDn som redan har inhämtats.
"""

import csv
import json
import logging
from typing import Any

# Hanterar kontakt med API
from api_client import error_handling, rate_limit

logger = logging.getLogger(__name__)

base_url = "https://api.themoviedb.org/3/tv/"


def append_json_line(data: dict[str, Any], filename: str) -> None:
    with open(filename, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

"""
def save_completed_ids(completed_ids: set[int], filename: str = "______") -> None:
    with open(filename, "w") as f:
        f.write("\n".join(str(i) for i in completed_ids))


def load_completed_ids(filename: str = "______") -> set[int]:
    if os.path.exists(filename):
        with open(filename) as f:
            return {int(line) for line in f if line.strip()}
    return set()
"""

def load_show_ids(filename: str = "data/raw/show_ids.csv") -> list[int]:
    ids = []
    with open(filename, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.append(int(row["id"]))
    return ids


def extract_season_data(details_json: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": details_json["id"],
        "popularity": details_json["popularity"],
        "name": details_json["name"],
        "episode_run_time": details_json["episode_run_time"],
        "number_of_episodes": details_json["number_of_episodes"],
        "number_of_seasons": details_json["number_of_seasons"],
        "seasons": [
            {
                "season_number": s["season_number"],
                "air_date": s["air_date"],
                "episode_count": s["episode_count"]
            }
            for s in details_json.get("seasons", [])
        ],
        "networks": [
                    {
                        "network": n["name"]
                    }
                    for n in details_json.get("networks", [])
                ],
        "genres": [
                            {
                                "genre": g["name"]
                            }
                            for g in details_json.get("genres", [])
                        ]
    }


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
            season_data = extract_season_data(response.json())
            append_json_line(season_data, filename="data/raw/show_details.jsonl")

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