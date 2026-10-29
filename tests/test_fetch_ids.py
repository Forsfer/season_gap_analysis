"""
AI-användande: Denna filen är skriven med AI.
-----------------------------------------------------------
Tester för fetch_ids.

Del 1: enhetstester av funktionerna som inte rör API:et.
Del 2: tester av main, där error_handling byts ut mot en låtsasversion
       så att TMDB aldrig anropas.
"""
import logging

import pytest

import fetch_ids
from fetch_ids import append_show_ids_csv, extract_show_ids, extract_total_pages


# ---------------------------------------------------------------------------
# Del 1: enhetstester
# ---------------------------------------------------------------------------
def test_extract_show_ids_returnerar_id_och_namn():
    response_json = {
        "results": [
            {"id": 1399, "name": "Game of Thrones", "popularity": 99.0},
            {"id": 1396, "name": "Breaking Bad", "popularity": 80.5},
        ]
    }

    result = extract_show_ids(response_json)

    assert result == [(1399, "Game of Thrones"), (1396, "Breaking Bad")]


def test_extract_show_ids_tom_sida_ger_tom_lista():
    assert extract_show_ids({"results": []}) == []


def test_extract_total_pages():
    assert extract_total_pages({"total_pages": 87, "results": []}) == 87


def test_append_show_ids_csv_skriver_header_en_gang(tmp_path):
    filename = tmp_path / "raw" / "show_ids.csv"

    append_show_ids_csv([(1, "Serie A")], filename=str(filename))
    append_show_ids_csv([(2, "Serie B")], filename=str(filename))

    lines = filename.read_text(encoding="utf-8").splitlines()
    assert lines == ["id,name", "1,Serie A", "2,Serie B"]


# ---------------------------------------------------------------------------
# Del 2: tester av main
# ---------------------------------------------------------------------------
class FakeResponse:
    """Låtsas vara ett requests.Response. Har bara det main använder: .json()"""

    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


def page_response(page, total_pages, shows):
    return FakeResponse({
        "page": page,
        "total_pages": total_pages,
        "results": [{"id": show_id, "name": name} for show_id, name in shows],
    })


def fake_api(monkeypatch, responses):
    """
    Byter ut error_handling och rate_limit i fetch_ids.
    responses är en dict: sidnummer -> svar (eller None för ett misslyckat anrop).
    Returnerar en lista med de sidor som anropades.
    """
    called_pages = []

    def fake_error_handling(endpoint, params=None):
        page = params["page"]
        called_pages.append(page)
        if len(called_pages) > 20:  # skydd mot oändlig loop, så att testet inte hänger sig
            raise RuntimeError("Fler än 20 anrop, troligen en oändlig loop")
        return responses.get(page)

    monkeypatch.setattr(fetch_ids, "error_handling", fake_error_handling)
    monkeypatch.setattr(fetch_ids, "rate_limit", lambda seconds=0: None)
    return called_pages


@pytest.fixture(autouse=True)
def kor_i_tom_mapp(tmp_path, monkeypatch):
    """main skriver till data/raw/ och app.log, så varje test körs i en egen tom mapp."""
    monkeypatch.chdir(tmp_path)


def read_csv_lines():
    with open("data/raw/show_ids.csv", encoding="utf-8") as f:
        return f.read().splitlines()


def test_alla_sidor_lyckas(monkeypatch):
    called_pages = fake_api(monkeypatch, {
        1: page_response(1, 2, [(1, "Serie A"), (2, "Serie B")]),
        2: page_response(2, 2, [(3, "Serie C")]),
    })

    fetch_ids.main()

    assert called_pages == [1, 2]
    assert read_csv_lines() == ["id,name", "1,Serie A", "2,Serie B", "3,Serie C"]


def test_en_sida_i_mitten_misslyckas_fortsatter_och_loggar(monkeypatch, caplog):
    called_pages = fake_api(monkeypatch, {
        1: page_response(1, 3, [(1, "Serie A")]),
        2: None,
        3: page_response(3, 3, [(3, "Serie C")]),
    })

    with caplog.at_level(logging.INFO):
        fetch_ids.main()

    assert called_pages == [1, 2, 3]
    assert read_csv_lines() == ["id,name", "1,Serie A", "3,Serie C"]
    assert "1 sidor misslyckades: [2]" in caplog.text


def test_forsta_sidan_misslyckas_avbryter(monkeypatch, caplog):
    called_pages = fake_api(monkeypatch, {1: None})

    with caplog.at_level(logging.INFO):
        fetch_ids.main()

    assert called_pages == [1]  # avbryter direkt, ingen oändlig loop
    assert "Första sidan misslyckades" in caplog.text
    assert "Alla sidor hämtades" not in caplog.text