"""
Denna filen används för att kontakta api
"""
import logging
import os  # För att kunna accessa filsystemet
import time

import requests
from dotenv import load_dotenv  # retrieve the value of an environment variable.
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

load_dotenv()

api_key = os.getenv(key="api_key")
if not api_key:
    raise RuntimeError("api_key saknas, kontrollera .env")

logger = logging.getLogger(__name__)


## ----------- Retries med urllib3/requests och session
## https://requests.readthedocs.io/en/latest/user/advanced/#example-automatic-retries
retries = Retry(
    total=3,
    backoff_factor=2.5,
    status_forcelist=[429, 500, 502, 503, 504],
)

session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=retries))
session.headers.update({
    "accept": "application/json",
    "Authorization": f"Bearer {api_key}",
})
## ---------------------------

# Anropar API. Anrop avbryts om 10 sekunder passerar.
def make_call(endpoint: str, params: dict | None = None) -> requests.Response: # None är standardvärde, params behöver inte skickas med
    return session.get(url=endpoint, params=params, timeout=10)


def error_handling(endpoint: str, params: dict | None = None) -> requests.Response | None:
    try:
        response = make_call(endpoint, params)
        response.raise_for_status()
        return response # Om anropet lyckades

    except requests.exceptions.HTTPError as http_err:
        logger.warning("HTTP Error: %s", http_err)
        
    except requests.exceptions.ConnectionError as e:
        logger.warning("Connection Error: %s", e)
        
    except requests.exceptions.Timeout:
        logger.warning("Timeout Error: The request timed out")
       
    except requests.exceptions.RequestException as e:
        logger.warning("Request Exception: %s", e)

    return None


# För att undvika att skicka massvis med förfrågningar till APIet på en gång, vilket kan läsas som spamm, så har vi 25ms paus mellan varje anrop.
def rate_limit(seconds: float = 0.25):
    time.sleep(seconds)