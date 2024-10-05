import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import asyncio
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch_synonyms(session, word):
    """Asynchronous function to fetch synonyms from synoniemen.net."""
    url = f"https://synoniemen.net/index.php?zoekterm={word}"
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                synonym_table = soup.find('dl', class_='alstrefwoordtabel')
                
                synonyms = []
                if synonym_table:
                    for synonym in synonym_table.find_all('a'):
                        synonyms.append(synonym.text)
                return synonyms
            elif response.status == 429:
                # Too many requests; return a signal to retry with backoff
                logging.warning(f"Too many requests for word '{word}' - HTTP 429. Retrying later.")
                return "rate_limit"
            else:
                logging.warning(f"Failed to fetch synonyms for '{word}'. HTTP Status: {response.status}")
                return []
    except Exception as e:
        logging.error(f"Error occurred while fetching '{word}': {e}")
        return []
    
def get_synonyms(word):
    """Scrapes synonyms for a single word from synoniemen.net."""
    # Construct the URL with the search term
    url = f"https://synoniemen.net/index.php?zoekterm={word}"
    
    try:
        # Send an HTTP request to get the webpage content
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Check if the request was successful

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the relevant synonym table
        synonym_table = soup.find('dl', class_='alstrefwoordtabel')
        
        # Extract all <a> tags within <dd> elements in the synonym table
        synonyms = []
        if synonym_table:
            for synonym in synonym_table.find_all('a'):
                synonyms.append(synonym.text)
            return synonyms  # Return the found synonyms
        else:
            logging.warning(f"No synonym table found for word: {word}")
            return []  # Return an empty list if no synonyms are found

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred for word '{word}': {http_err}")
        raise http_err  # Raise the exception so the calling function can handle it
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"Connection error occurred for word '{word}': {conn_err}")
        raise conn_err  # Raise the exception so the calling function can handle it
    except requests.exceptions.Timeout as timeout_err:
        logging.error(f"Timeout error for word '{word}': {timeout_err}")
        raise timeout_err  # Raise the exception so the calling function can handle it
    except Exception as err:
        logging.error(f"An error occurred for word '{word}': {err}")
        raise err  # Raise any other errors for higher-level handling


def get_synonyms_for_words(words, min_delay=0.5, max_delay=1.5):
    """
    Scrapes synonyms for a list of words from synoniemen.net and includes a delay between requests.
    
    :param words: List of words to scrape synonyms for
    :param min_delay: Minimum delay between requests in seconds (default: 0.5 second)
    :param max_delay: Maximum delay between requests in seconds (default: 1.5 seconds)
    :return: Dictionary with words as keys and lists of synonyms as values
    """
    all_synonyms = {}

    for word in words:
        logging.info(f"Fetching synonyms for '{word}'")
        synonyms = get_synonyms(word)
        all_synonyms[word] = synonyms
        #print(f"Synonyms for '{word}': {synonyms}")
        
        # Introduce a random delay between min_delay and max_delay seconds
        delay = random.uniform(min_delay, max_delay)
        logging.info(f"Sleeping for {delay:.2f} seconds before the next request")
        time.sleep(delay)

    return all_synonyms


# Example usage
test_words = [
    "groot",        # big
    "snel",         # fast
    "mooi",         # beautiful
    "krachtig",     # powerful
    "vriendelijk",  # friendly
    "intelligent",  # intelligent
    "blij",         # happy
    "slecht",       # bad
    "simpel",       # simple
    "sterk"         # strong
]

# only run if main
if __name__ == "__main__":
    # Define delay settings
    min_delay = 0.5  # Minimum 1 second delay
    max_delay = 1.5  # Maximum 3 seconds delay

    start_time = time.time()

    # Get synonyms for the list of test words
    synonyms_dict = get_synonyms_for_words(test_words, min_delay=min_delay, max_delay=max_delay)

    print(f"Time taken: {time.time() - start_time:.2f} seconds")


