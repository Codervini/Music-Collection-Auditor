from uuid_extensions import uuid7, uuid7str
import requests
from mca.core.logger import set_logger
from datetime import date
import time
from requests_cache import CachedSession

logger = set_logger(__name__)


def generate_uuidv7():
    return uuid7()

def api_request_handler(api, session:CachedSession, header=None, retries=5):
    for attempt in range(1, retries + 1):
        try:
            match header:
                case None:
                    response = session.get(api)
                case _:
                    response = session.get(api, headers=header)

            logger.info(f"API response: {response} | status={response.status_code} | cached={response.from_cache}")

            if response.status_code == 404:
                logger.warning(f"Resource not found | status={response.status_code} | url={api}")
                response.raise_for_status()

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Response data: {data}")
                if session.service == "musicbrainz" and not response.from_cache:
                    time.sleep(1)
                return data
            
            logger.warning(f"API request failed | attempt={attempt}/{retries} | status={response.status_code} | url={api}")

            if response.status_code == 503:
                time.sleep(5)
                continue
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error | attempt={attempt}/{retries} | url={api} | error={e}",exc_info=True)
            if attempt < retries:
                time.sleep(5)
                continue
            raise
    raise RuntimeError(f"API request failed after {retries} attempts: {api}")
    
def coerce_to_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    try:
        if len(value) == 10:  # full date "2019-06-15"
            return date.fromisoformat(value)
        else:  # anything else — year only, year-month, whatever
            return date(int(value[:4]), 1, 1)
    except (ValueError, TypeError):
        return None