from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sqlite3
import os
# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("user-data-dir=C:/Users/Dejan/AppData/Local/Google/Chrome/User Data")
chrome_options.add_argument("profile-directory=Default")

# Specify the path to ChromeDriver
chrome_driver_path = 'C:/Webdrivers/Chromedriver/chromedriver.exe'

# Create a Service object with the path to the driver
service = Service(executable_path=chrome_driver_path)

# Initialize WebDriver with the Service object and Chrome options
driver = webdriver.Chrome(service=service, options=chrome_options)

# # Open the page
# driver.get('https://portal.clarin.ivdnt.org/corpus-frontend-chn/chn-extern/search/hits?filter=languageVariant%3A%28"NN"%29&first=0&group=hit%3Aword%3Ai&number=20&patt=%5B%5D&interface=%7B"form"%3A"explore"%2C"exploreMode"%3A"frequency"%7D')

# # Wait until the table with the words and frequencies loads
# wait = WebDriverWait(driver, 10)
# table_body = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.group-table tbody')))

# Function to scrape words and their frequencies
def scrape_words_and_frequencies(table_body):
    words_data = []
    rows = table_body.find_elements(By.CSS_SELECTOR, 'tr.grouprow')
    
    for row in rows:
        word = row.find_element(By.TAG_NAME, 'td').text
        # Get the frequency and convert it to a number
        frequency = row.find_element(By.CSS_SELECTOR, 'div.progress-bar').text.strip().replace(',', '')
        frequency = int(frequency)  # Convert frequency to an integer
        
        # Break the loop if the frequency is below the threshold (25 in this case)
        if frequency < 100:
            break
        #print("Appending word: ", word, " ||| frequency: ", frequency)
        words_data.append((word, frequency))
    
    return words_data

# Function to save the last scraped word count to a file
def save_word_count(word_count):
    with open("last_word_count.txt", "w") as f:
        f.write(str(word_count))

# Function to load the last scraped word count from the file
def load_word_count():
    if os.path.exists("last_word_count.txt"):
        with open("last_word_count.txt", "r") as f:
            return int(f.read())
    return 0  # Start from 0 words if no record exists

# Function to generate the URL for a specific starting word index (based on the word count)
def generate_url(start_word_index, entries_per_page=100):
    url = f'https://portal.clarin.ivdnt.org/corpus-frontend-chn/chn-extern/search/hits?filter=languageVariant%3A%28"NN"%29&first={start_word_index}&group=hit%3Aword%3Ai&number={entries_per_page}&patt=%5B%5D&interface=%7B"form"%3A"explore"%2C"exploreMode"%3A"frequency"%7D'
    return url

# Function to move between pages and continue from the last word using the URL and the "Next" button
def navigate_pages(entries_per_page=200, max_retries=5):
    scraper_data = []
    wait = WebDriverWait(driver, 30)  # WebDriverWait with 10 seconds max wait time

    # Load the last saved word count
    total_word_count = load_word_count()
    total_time = 0  # To store the cumulative time for all pages

    # Calculate the initial page to load based on the word count
    start_word_index = total_word_count

    try:
        # Initial load using the URL to resume from the last saved word count
        start_time = time.time()
        url = generate_url(start_word_index, entries_per_page)
        driver.get(url)  # Directly go to the page using the URL

        # Wait until the table body loads for the current page
        table_body = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.group-table tbody')))

        # Calculate the latest load time for the initial page
        load_time = time.time() - start_time
        total_time += load_time
        print(f"Page loaded from word index {start_word_index}. Load time: {load_time:.2f} seconds")

        # Scrape the data from the current page
        page_data = scrape_words_and_frequencies(table_body)
        if not page_data:
            # If the current page returns no valid data, stop scraping
            return scraper_data

        # Append the scraped data to the main list
        scraper_data.extend(page_data)

        # Update the total word count based on the number of words scraped in this page
        words_scraped = len(page_data)
        total_word_count += words_scraped

        # Save the updated word count in case of a crash
        save_word_count(total_word_count)

    except Exception as e:
        print(f"Error loading initial page from word index {start_word_index}: {e}")
        return scraper_data  # Return what we scraped so far

    # After the initial page load, use the "Next" button for subsequent pages
    retries = 0  # Counter to track retries
    while True:
        try:
            # Record the start time for the next page load
            start_time = time.time()

            # Refetch the "Next" button each time to avoid stale element reference
            next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'li.next')))
            next_button.click()

            # Wait until the table body loads for the next page
            table_body = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.group-table tbody')))

            # Calculate the latest load time for the next page
            load_time = time.time() - start_time
            total_time += load_time
            print(f"Next page loaded. Load time: {load_time:.2f} seconds")

            # Scrape the data from the current page
            page_data = scrape_words_and_frequencies(table_body)
            if not page_data:
                # If the current page returns no valid data, stop scraping
                break

            # Append the scraped data to the main list
            scraper_data.extend(page_data)

            # Update the total word count based on the number of words scraped in this page
            words_scraped = len(page_data)
            total_word_count += words_scraped

            # Save the updated word count in case of a crash
            save_word_count(total_word_count)
            # reset retries if successful
            retries = 0

        except Exception as e:
            # Handle stale element reference error with retries
            print(f"Error after navigating to the next page: {e}")
            retries += 1
            if retries < max_retries:
                print(f"Retrying... attempt {retries}")
                time.sleep(1)  # Optional small delay before retrying
                continue  # Retry the loop
            else:
                print(f"Exceeded maximum retries ({max_retries})")
                break

    return scraper_data


# SQLite function to assign simplicity scores
def assign_simplicity_scores(db_path, scraper_data):
    """
    Assigns simplicity scores to words based on their frequency from the scraper.
    Simplicity scores are between 0 and 1, with higher frequencies resulting in higher scores.
    
    :param db_path: Path to the SQLite database.
    :param scraper_data: List of tuples with words and their frequencies from the scraper. 
                         Example: [('word1', 500), ('word2', 1000), ...]
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Calculate total frequency from the scraper to normalize scores
    total_frequency = sum(frequency for word, frequency in scraper_data)

    # Assign simplicity scores based on frequency
    for word, frequency in scraper_data:
        # Check if the word exists in the database
        cursor.execute('SELECT word FROM words WHERE word = ?', (word,))
        result = cursor.fetchone()
        
        if result:
            # Simplicity score based on frequency, normalized between 0 and 1
            simplicity_score = frequency # / total_frequency  # Normalization
            cursor.execute('UPDATE words SET simplicity_score = ? WHERE word = ?', (simplicity_score, word))
    
    conn.commit()
    conn.close()
    print("Simplicity scores assigned based on frequency.")

# Scrape and assign simplicity scores
def main():
    db_path = 'dutch_Synonyms_NN.db'  # Update with your actual database path
    scraper_data = navigate_pages()  # Scrape all the pages and gather the words and frequencies
    assign_simplicity_scores(db_path, scraper_data)  # Assign simplicity scores based on the scraped data

    # Close the browser when done
    driver.quit()

# Run the main function to execute the scraper and assign scores
main()
