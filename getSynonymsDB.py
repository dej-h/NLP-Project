import sqlite3
import re
import spacy
def open_database(db_path):
    """
    Open a connection to the SQLite database.
    :param db_path: Path to the SQLite database file.
    :return: SQLite connection and cursor.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    return conn, cursor

def fetch_words(cursor):
    """
    Fetch all words from the 'words' table in the database.
    :param cursor: SQLite cursor.
    :return: List of words from the database.
    """
    cursor.execute('SELECT word FROM words')
    return cursor.fetchall()

def fetch_synonyms(cursor, word):
    """
    Fetch all synonyms for a given word from the 'synonyms' table in the database.
    :param cursor: SQLite cursor.
    :param word: Word for which to fetch synonyms.
    :return: List of synonyms for the given word.
    """
    cursor.execute('SELECT synonym FROM synonyms WHERE word = ?', (word,))
    return cursor.fetchall()

def close_database(conn):
    """
    Close the SQLite database connection.
    :param conn: SQLite connection to close.
    """
    conn.close()
    
def extract_word_scores_and_synonyms(text, debug=False):
    # Open database connection
    db_path = 'dutch_synonyms_NN.db'
    conn, cursor = open_database(db_path)

    # Tokenize the text into words, preserving word positions
    words = re.findall(r'\w+', text)
    # simplify the words to lowercase
    words = [word.lower() for word in words]
    word_positions = {index: word for index, word in enumerate(words)}

    result = []

    # Fetch all words from the database for lookup
    db_words = {word[0] for word in fetch_words(cursor)}  # Convert list of tuples to set of words for fast lookup

    # Iterate through each word in the text
    for position, word in word_positions.items():
        if word in db_words:  # If the word exists in the database
            # Fetch simplicity score for the word
            cursor.execute("SELECT simplicity_score FROM words WHERE word = ?", (word,))
            complex_simplicity_score = cursor.fetchone()[0]

            # Fetch synonyms and relatedness scores
            synonyms = fetch_synonyms(cursor, word)

            if synonyms:  # If synonyms are found
                for synonym_tuple in synonyms:
                    synonym = synonym_tuple[0]
                    # Fetch simplicity score and relatedness score for each synonym
                    cursor.execute("SELECT simplicity_score FROM words WHERE word = ?", (synonym,))
                    synonym_simplicity_score = cursor.fetchone()[0]

                    cursor.execute("SELECT relatedness_score FROM synonyms WHERE word = ? AND synonym = ?", (word, synonym))
                    relatedness_score = cursor.fetchone()[0]

                    # Format with | separators; put original word first if debug=True
                    if debug:
                        result.append(f"{word}|{position}|{complex_simplicity_score}|{synonym}|{synonym_simplicity_score}|{relatedness_score}")
                    else:
                        result.append(f"{position}|{complex_simplicity_score}|{synonym}|{synonym_simplicity_score}|{relatedness_score}")
            else:  # No synonyms found
                if debug:
                    result.append(f"{word}|{position}|{complex_simplicity_score}|NONE|NONE|NONE")
                else:
                    result.append(f"{position}|{complex_simplicity_score}|NONE|NONE|NONE")
        else:
            # Word is not in the database, consider it as non-complex and skip
            if debug:
                print(f"Word '{word}' not found in the database, skipping...")
            continue
            

    # Close the database connection
    close_database(conn)

    # Return the result in the required format, separated by semicolons
    return ";".join(result)

# Load the large Dutch language model
nlp = spacy.load("nl_core_news_lg")

# Example input text
text = "De gecompliceerde infrastructuur van de metropool vereist een systematische analyse door deskundigen."

# Unlemmatized version
print("Unlemmatized input:")
response_unlemmatized = extract_word_scores_and_synonyms(text, debug=True)
for i in response_unlemmatized.split(";"):
    print(i)

# Lemmatized version
print("\nLemmatized input:")
lemmatized_words = [token.lemma_ for token in nlp(text)]
lemmatized_text = " ".join(lemmatized_words)
response_lemmatized = extract_word_scores_and_synonyms(lemmatized_text, debug=True)
for i in response_lemmatized.split(";"):
    print(i)