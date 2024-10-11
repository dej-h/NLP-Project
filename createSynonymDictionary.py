import sqlite3
import time
import math
import logging
import re
# Load the functions from the previous code:

def load_idx_file(idx_file):
    """
    Load the index (.idx) file that maps words to their positions in the .dat file.
    
    :param idx_file: Path to the .idx file.
    :return: Dictionary with words as keys and their starting positions in the .dat file as values.
    """
    idx_data = {}
    with open(idx_file, 'r', encoding='ISO8859-1') as file:
        for line in file:
            if '|' in line:
                word, pos = line.strip().split('|')
                idx_data[word] = int(pos)
    return idx_data


def get_all_synonyms(dat_file, word, idx_data):
    """
    Retrieve all synonyms for a given word from the .dat file using the index.
    
    :param dat_file: Path to the .dat file.
    :param word: The word to retrieve synonyms for.
    :param idx_data: Dictionary of word positions loaded from the .idx file.
    :return: List of synonyms for the word, or None if no synonyms are found.
    """
    if word not in idx_data:
        return None

    synonyms = []
    start_pos = idx_data[word]
    
    # Open the .dat file in read mode
    with open(dat_file, 'r', encoding='ISO8859-1') as file:
        # Use start_pos to seek directly to the word's location
        file.seek(start_pos)
        
        # Start reading from this position
        for line in file:
            line = line.strip()
            if line.startswith(f"{word}|"):
                # Found the word entry, now gather synonyms
                for next_line in file:
                    next_line = next_line.strip()
                    if next_line.startswith('-|'):
                        synonym = next_line.split('|')[1]
                        synonyms.append(synonym)
                    else:
                        # Stop when the next entry (non-synonym) starts
                        break
                break
    
    return synonyms if synonyms else None



# Load SpaCy's Dutch language model for word categorization
import spacy
nlp = spacy.load("nl_core_news_lg") # , disable=["ner", "parser"] # Disable unnecessary pipeline components

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def categorize_words_in_batch(words):
    """
    Categorize a batch of words using SpaCy's efficient pipeline.
    
    :param words: List of words to categorize.
    :return: List of tuples (word, part of speech).
    """
    categorized_words = []
    for doc in nlp.pipe(words, batch_size=1000):
        for token in doc:
            categorized_words.append((token.text, token.pos_))  # Append word and its part of speech
    return categorized_words


def initialize_database(db_path, dictionary_file, no_uppercase=False, no_special_characters=False, allowed_special_chars="'-"):
    """
    Initialize the database with words and their respective parts of speech.
    
    :param db_path: Path to the SQLite database.
    :param dictionary_file: Path to the dictionary file containing the list of words.
    :param no_uppercase: Flag to exclude words with uppercase letters.
    :param no_special_characters: Flag to exclude words with special characters.
    :param allowed_special_chars: Special characters that are allowed in words.
    """
    
    # print if you are sure you want to redo the database
    print("Are you sure you want to initialize the database? This will clear all existing data.")
    response = input("Enter 'yes' to confirm: ")
    if response.lower() != 'yes':
        print("Initialization aborted.")
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            word TEXT PRIMARY KEY,
            word_type TEXT,
            simplicity_score REAL DEFAULT 0.0,
            processed BOOLEAN DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT,
            synonym TEXT,
            relatedness_score REAL DEFAULT 0.0,
            FOREIGN KEY (word) REFERENCES words (word)
        )
    ''')
    
    # Read words from the dictionary file
    with open(dictionary_file, 'r', encoding='utf-8') as file:
        words = file.read().splitlines()
    
    print("First 10 words:", words[:10])
    print("Last 10 words:", words[-10:])
    
    regex_pattern = f"^[a-zA-Z{re.escape(allowed_special_chars)}]+$"
    filtered_words = []
    
    print(f"Amount of words before filtering: {len(words)}")
    
    for word in words:
        if no_uppercase and not word.islower():
            continue
        if not re.match(regex_pattern, word):
            continue
        filtered_words.append(word)
    
    print(f"Amount of words after filtering: {len(filtered_words)}")
    
    # Categorize words in batches
    words_with_types = []
    batch_size = 10000
    total_words = len(filtered_words)
    start_time = time.time()

    for i in range(0, total_words, batch_size):
        batch = filtered_words[i:i+batch_size]
        categorized_batch = categorize_words_in_batch(batch)
        words_with_types.extend(categorized_batch)
        
        elapsed_time = time.time() - start_time
        progress = ((i + len(batch)) / total_words) * 100
        print(f"Processed {i + len(batch)}/{total_words} words ({progress:.2f}%) - Elapsed time: {elapsed_time:.2f}s")

    # Insert words and their parts of speech into the database
    cursor.executemany('INSERT OR IGNORE INTO words (word, word_type) VALUES (?, ?)', words_with_types)
    conn.commit()
    conn.close()


def process_word(word, idx_data, dat_file, cursor, conn):
    """
    Process a single word by fetching its synonyms and inserting them into the database.
    
    :param word: The word to process.
    :param idx_data: Dictionary of word positions loaded from the .idx file.
    :param dat_file: Path to the .dat file.
    :param cursor: SQLite cursor to interact with the database.
    :param conn: SQLite connection to commit the changes.
    """
    logging.info(f"Processing word: {word}")
    synonyms = get_all_synonyms(dat_file, word, idx_data)
    
    # Normalize the original word (lowercase, strip)
    normalized_word = word.lower().strip()
    
    # Remove synonyms that are the same as the word (regardless of case or leading/trailing spaces)
    if synonyms:
        synonyms = [synonym for synonym in synonyms if synonym.lower().strip() != normalized_word]
    
    # Remove any duplicate entries
    if synonyms:
        synonyms = list(set(synonyms))
    
    # Insert synonyms into the database
    if synonyms:
        synonyms_with_scores = [(word, synonym, calculate_relatedness_score(position))
                                for position, synonym in enumerate(synonyms)]
        
        cursor.executemany('''
            INSERT INTO synonyms (word, synonym, relatedness_score)
            VALUES (?, ?, ?)
        ''', synonyms_with_scores)
        logging.info(f"Synonyms for '{word}' inserted.")
    
    # Mark the word as processed
    cursor.execute('UPDATE words SET processed = 1 WHERE word = ?', (word,))
    logging.info(f"Word '{word}' marked as processed.")
    
    # Commit the changes to the database
    conn.commit()




def process_synonyms(db_path, idx_file, dat_file):
    """
    Process all words that haven't been processed by fetching their synonyms and inserting them into the database.
    
    :param db_path: Path to the SQLite database.
    :param idx_file: Path to the .idx file.
    :param dat_file: Path to the .dat file.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Fetch words that haven't been processed yet
    cursor.execute('SELECT word FROM words WHERE processed = 0')
    words = cursor.fetchall()
    
    if not words:
        logging.info("All words have been processed.")
        conn.close()
        return
    
    # Load the index file
    idx_data = load_idx_file(idx_file)
    
    total_words = len(words)
    total_processed = 0
    start_time = time.time()

    for word in words:
        process_word(word[0], idx_data, dat_file, cursor,conn)
        total_processed += 1
        display_progress_bar(total_processed, total_words, start_time)

    conn.commit()
    conn.close()
    logging.info("Synonym processing completed.")


def calculate_relatedness_score(position, method="exp", decay_rate=0.1):
    """
    Calculate a relatedness score based on the position of the synonym.
    
    :param position: Position of the synonym in the list (0-indexed).
    :param method: Scoring method, either "log" for logarithmic decay or "exp" for exponential decay.
    :param decay_rate: Used for exponential decay to control the steepness of the decline.
    :return: Relatedness score as a float value.
    """
    if method == "log":
        return 1 / (math.log(position + 2))  # Logarithmic decay
    elif method == "exp":
        return math.exp(-decay_rate * position)  # Exponential decay
    else:
        raise ValueError("Invalid method. Choose 'log' or 'exp'.")


def display_progress_bar(total_processed, total_words, start_time):
    """
    Display a progress bar to track the processing progress.
    
    :param total_processed: Number of words processed so far.
    :param total_words: Total number of words to process.
    :param start_time: The time when processing started, used to estimate remaining time.
    """
    progress = (total_processed / total_words) * 100
    elapsed_time = time.time() - start_time
    avg_time_per_word = elapsed_time / total_processed if total_processed > 0 else 0
    remaining_words = total_words - total_processed
    est_time_remaining = remaining_words * avg_time_per_word
    
    bar_length = 40
    block = int(bar_length * (total_processed / total_words))
    bar = "#" * block + "-" * (bar_length - block)
    
    print(f"\r[{bar}] {progress:.2f}% completed - Estimated time remaining: {est_time_remaining / 60:.2f} minutes", end="")

def assign_simplicity_scores(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT word FROM words')
    words = cursor.fetchall()
    
    for (word,) in words:
        simplicity_score = 1.0 / (1 + len(word))  # Simple heuristic
        cursor.execute('UPDATE words SET simplicity_score = ? WHERE word = ?', (simplicity_score, word))
    
    conn.commit()
    conn.close()
    print("Simplicity scores assigned.")

def reset_processed_and_synonyms(db_path):
    """
    Resets the 'processed' column in the 'words' table and clears the 'synonyms' table.
    
    :param db_path: Path to the SQLite database
    """
    # ask user if sure
    print("Are you sure you want to reset the database? This will clear all synonyms and reset the 'processed' flags.")
    response = input("Enter 'yes' to confirm: ")
    if response.lower() != 'yes':
        print("Reset operation aborted.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Reset all 'processed' flags in the 'words' table
        cursor.execute('UPDATE words SET processed = 0')
        print("All 'processed' flags in the 'words' table have been reset.")
        
        # Clear all data from the 'synonyms' table
        cursor.execute('DELETE FROM synonyms')
        print("All data in the 'synonyms' table has been cleared.")
        
        # Commit changes
        conn.commit()
    
    except Exception as e:
        print(f"Error resetting the database: {e}")
    
    finally:
        conn.close()

def sync_words_and_synonyms(db_path):
    """
    Synchronize the synonym and word database by adding all synonyms that are not present in the 'words' table.
    Categorize the new words using SpaCy.
    
    :param db_path: Path to the SQLite database.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Fetch all synonyms
    cursor.execute('SELECT DISTINCT synonym FROM synonyms')
    synonyms = [row[0] for row in cursor.fetchall()]
    
    # Fetch all words
    cursor.execute('SELECT word FROM words')
    words = {row[0] for row in cursor.fetchall()}  # Set for faster lookup
    
    # Find synonyms not in words
    new_synonyms = [synonym for synonym in synonyms if synonym not in words]
    
    if new_synonyms:
        print("Found:", len(new_synonyms), "new synonyms.")
        
        # Categorize the new words
        categorized_words = categorize_words_in_batch(new_synonyms)
        
        # Insert new words into the 'words' table, skipping duplicates
        for word, word_type in categorized_words:
            try:
                cursor.execute('''
                    INSERT INTO words (word, word_type, simplicity_score, processed)
                    VALUES (?, ?, 0.0, 1)
                ''', (word, word_type))
            except sqlite3.IntegrityError:
                # If word already exists, just skip it
                print(f"Skipping duplicate word: {word}")
                
    else:
        print("No new synonyms found.")
    
    # Commit changes and close the connection
    conn.commit()
    conn.close()
    
    
def recategorize_words(db_path):
    """
    Recategorize all words in the 'words' table using SpaCy and update their word_type in the database.
    Display a progress bar to show processing progress.
    
    :param db_path: Path to the SQLite database.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Fetch all words from the 'words' table
    cursor.execute('SELECT word FROM words')
    words = [row[0] for row in cursor.fetchall()]
    total_words = len(words)
    
    if total_words > 0:
        print(f"Found {total_words} words to recategorize.")
        
        # Start time for progress estimation
        start_time = time.time()
        total_processed = 0
        
        # Categorize words in batch
        categorized_words = categorize_words_in_batch(words)
        
        # Update word_type for each word in the database and display progress
        for word, word_type in categorized_words:
            cursor.execute('''
                UPDATE words
                SET word_type = ?
                WHERE word = ?
            ''', (word_type, word))
            
            # Update progress bar
            total_processed += 1
            display_progress_bar(total_processed, total_words, start_time)
        
        print("\nRecategorization complete.")
    else:
        print("No words found for recategorization.")
    
    # Commit changes and close the connection
    conn.commit()
    conn.close()
    
    
      
def main():
    """
    Main function to initialize the database and process the words to extract and store their synonyms.
    """
    db_path = 'dutch_synonyms.db'
    dictionary_file = 'OpenTaal-210G-woordenlijsten/OpenTaal-210G-basis-gekeurd.txt'
    idx_file = 'sym_database/th_nl_v2.idx'
    dat_file = 'sym_database/th_nl_v2.dat'
    #initialize_database(db_path, dictionary_file, no_uppercase=True, no_special_characters=True)
    #process_synonyms(db_path, idx_file, dat_file)
    #recategorize_words(db_path)


if __name__ == "__main__":
    main()
