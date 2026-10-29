"""
AI-användande: Denna filen är skriven med AI.
----------------------------------------------------
Tester för fetch_details.

Del 1: enhetstester av funktionerna som inte rör API:et.
Del 2: tester av main, där error_handling byts ut mot en låtsasversion
       så att TMDB aldrig anropas.
"""
import json
import logging

import pytest

import fetch_details
from fetch_details import append_json_line, extract_season_data, load_show_ids


# ---------------------------------------------------------------------------
# Del 1: enhetstester
# ---------------------------------------------------------------------------
def make_details_json():
    """Ett förenklat svar från /tv/{id}, med bara de fält koden använder plus ett extra."""
    return {
        "id": 1399,
        "name": "Game of Thrones",
        "popularity": 99.5,
        "episode_run_time": [60],
        "number_of_episodes": 73,
        "number_of_seasons": 8,
        "overview": "Fält som inte ska följa med",
        "seasons": [
            {"season_number": 0, "air_date": None, "episode_count": 14, "name": "Specials"},
            {"season_number": 1, "air_date": "2011-04-17", "episode_count": 10, "name": "Season 1"},
        ],
        "networks": [{"id": 49, "name": "HBO"}],
        "genres": [{"id": 18, "name": "Drama"}, {"id": 10765, "name": "Sci-Fi & Fantasy"}],
    }


# --- load_show_ids ---

def test_load_show_ids_laser_id_som_heltal(tmp_path):
    filename = tmp_path / "show_ids.csv"
    filename.write_text("id,name\n1399,Game of Thrones\n1396,Breaking Bad\n", encoding="utf-8")

    result = load_show_ids(str(filename))

    assert result == [1399, 1396]


def test_load_show_ids_saknad_fil_kraschar(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_show_ids(str(tmp_path / "finns_inte.csv"))


# --- extract_season_data ---

def test_extract_season_data_plockar_ut_ratt_falt():
    result = extract_season_data(make_details_json())

    assert result["id"] == 1399
    assert result["name"] == "Game of Thrones"
    assert result["number_of_seasons"] == 8
    assert "overview" not in result


def test_extract_season_data_forenklar_listorna():
    result = extract_season_data(make_details_json())

    assert result["seasons"] == [
        {"season_number": 0, "air_date": None, "episode_count": 14},
        {"season_number": 1, "air_date": "2011-04-17", "episode_count": 10},
    ]
    assert result["networks"] == [{"network": "HBO"}]
    assert result["genres"] == [{"genre": "Drama"}, {"genre": "Sci-Fi & Fantasy"}]


def test_extract_season_data_saknade_listor_ger_tomma_listor():
    details = make_details_json()
    del details["seasons"]
    del details["networks"]
    del details["genres"]

    result = extract_season_data(details)

    assert result["seasons"] == []
    assert result["networks"] == []
    assert result["genres"] == []


def test_extract_season_data_saknat_obligatoriskt_falt_kraschar():
    details = make_details_json()
    del details["popularity"]

    with pytest.raises(KeyError):
        extract_season_data(details)


# --- append_json_line ---

def test_append_json_line_en_rad_per_anrop(tmp_path):
    filename = tmp_path / "show_details.jsonl"

    append_json_line({"id": 1, "name": "Serie A"}, str(filename))
    append_json_line({"id": 2, "name": "Café Ü"}, str(filename))

    lines = filename.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [
        {"id": 1, "name": "Serie A"},
        {"id": 2, "name": "Café Ü"},
    ]


# ---------------------------------------------------------------------------
# Del 2: tester av main
# ---------------------------------------------------------------------------

class FakeResponse:
    """Låtsas vara ett requests.Response. Har bara det main använder: .json()"""

    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


def details_response(series_id, name):
    data = make_details_json()
    data["id"] = series_id
    data["name"] = name
    return FakeResponse(data)


def fake_api(monkeypatch, responses):
    """
    Byter ut error_handling och rate_limit i fetch_details.
    responses är en dict: serie-id -> svar (eller None för ett misslyckat anrop).
    Returnerar en lista med de URL:er som anropades.
    """
    called_urls = []

    def fake_error_handling(endpoint, params=None):
        called_urls.append(endpoint)
        series_id = int(endpoint.rstrip("/").split("/")[-1])
        return responses.get(series_id)

    monkeypatch.setattr(fetch_details, "error_handling", fake_error_handling)
    monkeypatch.setattr(fetch_details, "rate_limit", lambda seconds=0: None)
    return called_urls


def write_show_ids(*shows):
    """Skapar data/raw/show_ids.csv, som fetch_ids annars hade skapat."""
    rows = ["id,name"] + [f"{show_id},{name}" for show_id, name in shows]
    with open("data/raw/show_ids.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")


def read_details():
    with open("data/raw/show_details.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


@pytest.fixture
def projektmapp(tmp_path, monkeypatch):
    """main använder relativa sökvägar, så varje test körs i en egen tom mapp med data/raw/."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "raw").mkdir(parents=True)
    return tmp_path


def test_main_alla_serier_lyckas(projektmapp, monkeypatch):
    write_show_ids((1399, "Game of Thrones"), (1396, "Breaking Bad"))
    fake_api(monkeypatch, {
        1399: details_response(1399, "Game of Thrones"),
        1396: details_response(1396, "Breaking Bad"),
    })

    fetch_details.main()

    details = read_details()
    assert [d["id"] for d in details] == [1399, 1396]
    assert details[1]["name"] == "Breaking Bad"


def test_main_anropar_ratt_url(projektmapp, monkeypatch):
    write_show_ids((1399, "Game of Thrones"))
    called_urls = fake_api(monkeypatch, {1399: details_response(1399, "Game of Thrones")})

    fetch_details.main()

    assert called_urls == ["https://api.themoviedb.org/3/tv/1399"]


def test_main_en_serie_misslyckas_fortsatter_och_loggar(projektmapp, monkeypatch, caplog):
    write_show_ids((1, "Serie A"), (2, "Serie B"), (3, "Serie C"))
    fake_api(monkeypatch, {
        1: details_response(1, "Serie A"),
        2: None,
        3: details_response(3, "Serie C"),
    })

    with caplog.at_level(logging.INFO):
        fetch_details.main()

    assert [d["id"] for d in read_details()] == [1, 3]
    assert "1 serier misslyckades: [2]" in caplog.text


def test_main_tva_korningar_ger_inga_dubbletter(projektmapp, monkeypatch):
    write_show_ids((1399, "Game of Thrones"))
    fake_api(monkeypatch, {1399: details_response(1399, "Game of Thrones")})

    fetch_details.main()
    fetch_details.main()

    assert [d["id"] for d in read_details()] == [1399]