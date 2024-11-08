import sqlite3
import re
import spacy
from transformers import AutoTokenizer, AutoModelForMaskedLM, AutoModelForSequenceClassification
import torch
import time
from sentence_transformers import SentenceTransformer, util
start_time = time.time()
# Load multilingual SimCSE model
simcse_model = SentenceTransformer("paraphrase-xlm-r-multilingual-v1")
# Load SpaCy Dutch language model for lemmatization
nlp = spacy.load("nl_core_news_lg")
stopwords = nlp.Defaults.stop_words  # Set of Dutch stopwords from SpaCy
# Load tokenizer and models
tokenizer = AutoTokenizer.from_pretrained("wietsedv/bert-base-dutch-cased")
mask_model = AutoModelForMaskedLM.from_pretrained("wietsedv/bert-base-dutch-cased")
similarity_model = AutoModelForSequenceClassification.from_pretrained("DTAI-KULeuven/robbert-2023-dutch-base")
similarity_tokenizer = AutoTokenizer.from_pretrained("DTAI-KULeuven/robbert-2023-dutch-base")

# Database connection functions
def open_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    return conn, cursor

def close_database(conn):
    conn.close()

def fetch_words(cursor):
    cursor.execute('SELECT word FROM words')
    return cursor.fetchall()

def fetch_synonyms(cursor, word):
    cursor.execute('SELECT synonym FROM synonyms WHERE word = ?', (word,))
    return cursor.fetchall()

def fetch_word_simplicity_score(cursor, word):
    cursor.execute("SELECT simplicity_score FROM words WHERE word = ?", (word,))
    result = cursor.fetchone()
    return result[0] if result else None

# Extract word scores and synonyms from database using lemmatized text
def extract_word_scores_and_synonyms(text, cursor,initial_word_count = 0, debug=False):
    # Lemmatize the text for database lookup
    lemmatized_text = " ".join([token.lemma_ for token in nlp(text)])
    words = re.findall(r'\w+', lemmatized_text.lower())
    word_positions = {index: word for index, word in enumerate(words)}

    result = []
    db_words = {word[0] for word in fetch_words(cursor)}  # Convert list of tuples to set of words for fast lookup

    for position, word in word_positions.items():
        position += initial_word_count
        # Fetch simplicity score for filtering
        simplicity_score = fetch_word_simplicity_score(cursor, word)
        
        # Continue only if word is in the database and simplicity score is <= 10000
        if word in db_words and simplicity_score is not None and simplicity_score <= 10000:
            cursor.execute("SELECT simplicity_score FROM words WHERE word = ?", (word,))
            complex_simplicity_score = cursor.fetchone()[0]
            synonyms = fetch_synonyms(cursor, word)

            if synonyms:
                for synonym_tuple in synonyms:
                    synonym = synonym_tuple[0]
                    synonym_simplicity_score = fetch_word_simplicity_score(cursor, synonym)

                    # Filter out synonyms with simplicity score > 10000
                    if synonym_simplicity_score is not None and synonym_simplicity_score <= 10000:
                        cursor.execute("SELECT relatedness_score FROM synonyms WHERE word = ? AND synonym = ?", (word, synonym))
                        relatedness_score = cursor.fetchone()[0]
                        
                        if debug:
                            result.append(f"{word}|{position}|{complex_simplicity_score}|{synonym}|{synonym_simplicity_score}|{relatedness_score}")
                        else:
                            result.append(f"{position}|{complex_simplicity_score}|{synonym}|{synonym_simplicity_score}|{relatedness_score}")
            else:
                if debug:
                    result.append(f"{word}|{position}|{complex_simplicity_score}|NONE|NONE|NONE")
                else:
                    result.append(f"{position}|{complex_simplicity_score}|NONE|NONE|NONE")
        else:
            if debug:
                print(f"Word '{word}' not found in the database or has simplicity score > 10000, skipping...")
            continue
    return ";".join(result), len(words)

# Helper function for context-based lemmatization
def lemmatize_in_context(sentence, target_word):
    """
    Finds the lemma of target_word within the context of sentence using SpaCy.
    :param sentence: The full sentence in which target_word appears.
    :param target_word: The word to be lemmatized.
    :return: Lemma of the target word if found, otherwise None.
    """
    doc = nlp(sentence)
    for token in doc:
        if token.text == target_word:
            return token.lemma_
    return None

def check_simcse_similarity(original_sentence, modified_sentence):
    embeddings = simcse_model.encode([original_sentence, modified_sentence])
    similarity_score = util.cos_sim(embeddings[0], embeddings[1]).item()
    return similarity_score

# Score sentence similarity
def score_similarity(original_sentence, modified_sentence):
    inputs = similarity_tokenizer([original_sentence, modified_sentence], return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = similarity_model(**inputs)
    logits = outputs.logits
    similarity_score = torch.softmax(logits, dim=1)[0][1].item()
    return similarity_score

# Generate model-based synonym candidates in the same format as database suggestions
def generate_candidates(sentence, word_to_replace, cursor, position, debug=False):
    if debug:
        print(f"\nGenerating candidates for '{word_to_replace}' at position {position}")
    
    # Skip stopwords
    if word_to_replace in stopwords:
        if debug:
            print(f"Skipping '{word_to_replace}' as it is a stopword.")
        return []

    # Lemmatize the word for database lookup using context-based lemmatization
    lemmatized_word = lemmatize_in_context(sentence, word_to_replace)
    if lemmatized_word is None:
        if debug:
            print(f"Could not find lemma for '{word_to_replace}' in the sentence.")
        return []

    # Check if the lemmatized word exists in the database with simplicity score <= 10000
    complex_simplicity_score = fetch_word_simplicity_score(cursor, lemmatized_word)
    if complex_simplicity_score is None:
        if debug:
            print(f"Skipping '{word_to_replace}' (lemmatized as '{lemmatized_word}') for model suggestions (not in database).")
        return []
    elif complex_simplicity_score > 10000:
        if debug:
            print(f"Skipping '{word_to_replace}' (lemmatized as '{lemmatized_word}') for model suggestions (simplicity score > 10000).")
        return []

    # Use SpaCy to get the POS of the original word
    doc = nlp(sentence)
    original_word_type = None
    for token in doc:
        if token.text == word_to_replace:
            original_word_type = token.pos_
            break

    if original_word_type is None:
        if debug:
            print(f"Could not determine word type for '{word_to_replace}' in the sentence.")
        return []

    # Masking the sentence for candidate generation
    masked_sentence = sentence.replace(word_to_replace, tokenizer.mask_token)
    inputs = tokenizer(masked_sentence, return_tensors="pt")
    
    with torch.no_grad():
        outputs = mask_model(**inputs)
    
    mask_token_index = torch.where(inputs['input_ids'] == tokenizer.mask_token_id)[1]
    mask_token_logits = outputs.logits[0, mask_token_index, :]
    top_tokens = torch.topk(mask_token_logits, 5, dim=1).indices[0].tolist()
    
    # Filter candidates to match the original word type and format output
    formatted_candidates = []
    if debug:
        print("Top candidates:")
    for token_id in top_tokens:
        candidate = tokenizer.decode([token_id]).strip()
        if candidate == word_to_replace:
            if debug:
                print(f"Filtering out '{candidate}': same as original word.")
            continue
        # check if the candidate is a contains the original word ( prevent a compound word to be replaced by one of its components)
        if word_to_replace in candidate:
            if debug:
                print(f"Filtering out '{candidate}': contains original word.")
            continue
        candidate_sentence = sentence.replace(word_to_replace, candidate)
        lemmatized_candidate = lemmatize_in_context(candidate_sentence, candidate)

        # Fetch POS for candidate and check match with original
        candidate_doc = nlp(candidate_sentence)
        candidate_word_type = None
        for token in candidate_doc:
            if token.text == candidate:
                candidate_word_type = token.pos_
                break
        if candidate_word_type != original_word_type:
            if debug:
                print(f"Filtering out '{candidate}' due to word type mismatch (expected '{original_word_type}', got '{candidate_word_type}').")
            continue
        
        candidate_simplicity_score = fetch_word_simplicity_score(cursor, lemmatized_candidate)
        if candidate_simplicity_score is None:
            if debug:
                print(f"Filtering out '{candidate}' (lemmatized as '{lemmatized_candidate}'): not in database.")
            continue
        elif candidate_simplicity_score > 10000:
            if debug:
                print(f"Filtering out '{candidate}' (lemmatized as '{lemmatized_candidate}'): simplicity score {candidate_simplicity_score} > 10000.")
            continue

        similarity_score = check_simcse_similarity(sentence, candidate_sentence)
        if debug:
            formatted_candidate = f"{word_to_replace}|{position}|{complex_simplicity_score}|{candidate}|{candidate_simplicity_score}|{similarity_score}"
        else:
            formatted_candidate = f"{position}|{complex_simplicity_score}|{candidate}|{candidate_simplicity_score}|{similarity_score}"
        formatted_candidates.append(formatted_candidate)
        
        if debug:
            print(f"Accepted candidate '{candidate}': {formatted_candidate}")
    
    return formatted_candidates


# Main function to suggest replacements from both sources
def suggest_replacements(text, db_path='dutch_synonyms_NN.db', debug=False, max_tokens=512):
    conn, cursor = open_database(db_path)
    
    segments = []
    current_segment = []
    current_length = 0

    words = re.findall(r'\w+', text.lower())
    for word in words:
        token_length = len(tokenizer(word)['input_ids'])
        if current_length + token_length > max_tokens:
            segments.append(" ".join(current_segment))
            current_segment = []
            current_length = 0
        current_segment.append(word)
        current_length += token_length

    if current_segment:
        segments.append(" ".join(current_segment))
    db_suggestions = []
    model_suggestions = []
    current_word_count = 0
    
    for segment in segments:
        db_suggestion, temp_word_count = extract_word_scores_and_synonyms(segment, cursor, current_word_count, debug=debug)
        db_suggestions.append(db_suggestion)
        
        lemmatized_segment = " ".join([token.lemma_ for token in nlp(segment)])
        word_positions = {index + current_word_count: word for index, word in enumerate(re.findall(r'\w+', lemmatized_segment.lower()))}
        model_string = ""
        for position, word in word_positions.items():
            candidates = generate_candidates(segment, word, cursor, position, debug=debug)
            if candidates:
                for candidate in candidates:
                    model_suggestions.append(candidate)
                    model_string += candidate + ";"
        model_suggestions.append(model_string)
        current_word_count += temp_word_count
            
    # Combine all db_suggestions and model_suggestions into single strings
    combined_db_suggestions = ";".join(db_suggestions)
    combined_model_suggestions = ";".join(model_suggestions)

    if debug:
        print("\nCombined Database Suggestions:")
        for suggestion in combined_db_suggestions.split(";"):
            print(suggestion)
        
        print("\nCombined Model Suggestions:")
        for suggestion in combined_model_suggestions.split(";"):
            print(suggestion)
    
    close_database(conn)
    
    # normalize both databases into a single long string
    
    return combined_db_suggestions, combined_model_suggestions

def fill_in_replacements(model_suggestions, db_suggestions, text, debug=False):
    simplicity_weight = 0.5
    relatedness_weight = 0.5
    
    # Input data format (no debug): position|simplicity_score|synonym|synonym_simplicity_score|relatedness_score
    # Input data format (debug): word|position|simplicity_score|synonym|synonym_simplicity_score|relatedness_score

    # Parse the suggestions into lists of tuples, keeping all entries
    db_entries = []
    for suggestion in db_suggestions.split(";"):
        if suggestion:
            parts = suggestion.split("|")
            position = int(parts[1]) if debug else int(parts[0])
            entry = parts[2:] if debug else parts[1:]
            db_entries.append((position, entry))
    
    model_entries = []
    for suggestion in model_suggestions.split(";"):
        if suggestion:
            parts = suggestion.split("|")
            position = int(parts[1]) if debug else int(parts[0])
            entry = parts[2:] if debug else parts[1:]
            model_entries.append((position, entry))

    lines = text.splitlines()
    result_lines = []

    word_counter = 0  # A counter to keep track of word positions across lines

    for line in lines:
        result_tokens = re.findall(r'\w+|[^\w\s]', line)  # Tokenize line with punctuation preservation
        line_word_counter = 0  # A counter for words within this line

        for i, token in enumerate(result_tokens):
            if not re.match(r'\w+', token):  # Check if token is not a word (punctuation or whitespace)
                continue

            # Collect all DB and model replacements for the current word position
            db_replacements = [entry for pos, entry in db_entries if pos == word_counter]
            model_replacements = [entry for pos, entry in model_entries if pos == word_counter]
            
            # Find the best DB replacement based on simplicity score
            best_db_replacement = None
            best_db_simplicity_score = float('inf')
            
            for replacement in db_replacements:
                if replacement[2] != "NONE" and float(replacement[0]) < float(replacement[2]):
                    synonym_simplicity_score = float(replacement[2])
                    if synonym_simplicity_score < best_db_simplicity_score:
                        best_db_simplicity_score = synonym_simplicity_score
                        best_db_replacement = replacement[1]  # synonym

            # If a DB replacement is found, apply it and skip to the next word
            if best_db_replacement:
                print(f"Putting the word: {best_db_replacement} in place of {token} at position {word_counter} (DB)")
                result_tokens[i] = (
                    best_db_replacement.capitalize() if token[0].isupper() else best_db_replacement
                )
                word_counter += 1  # Increase word count since we handled a word
                line_word_counter += 1
                continue

            # If no DB replacement is used, find the best model replacement
            best_model_replacement = None
            best_model_score = float('-inf')
            
            for replacement in model_replacements:
                if replacement[2] != "NONE" and float(replacement[0]) < float(replacement[2]):
                    simplicity_score = float(replacement[0])
                    relatedness_score = float(replacement[2])
                    score = simplicity_score * relatedness_score  # Combined score for model suggestions
                    if score > best_model_score:
                        best_model_score = score
                        best_model_replacement = replacement[1]  # synonym

            # Apply the best model replacement if it exists
            if best_model_replacement:
                print(f"Putting the word: {best_model_replacement} in place of {token} at position {word_counter} (Model)")
                result_tokens[i] = (
                    best_model_replacement.capitalize() if token[0].isupper() else best_model_replacement
                )

            # Increase word count only after processing a word token
            word_counter += 1
            line_word_counter += 1

        # Reconstruct line and add it to result lines
        result_line = ' '.join(result_tokens).replace(' .', '.').replace(' ,', ',')
        result_lines.append(result_line)

    # Join the result lines back into a single text, preserving line breaks
    return '\n'.join(result_lines)



        
    
    
    
 
# Example usage
text = "In Nederland is het niet verboden om een product onder de inkoopprijs te verkopen. Vooral supermarkten verkopen soms hun producten onder de inkoopprijs. Zo hebben zij een voordeel op hun concurrenten. Dat is gunstig voor de consument. De overheid wil verkoop beneden de inkoopprijs niet verbieden. De verwachting is namelijk dat een dergelijk verbod geen effect heeft op de positie van kleinere kruideniers of van leveranciers (boeren en tuinders).\n\nHet energielabel geeft aan hoe goed een woning is geïsoleerd (zogenoemde isolatieniveau). En hoe dak, vloeren en ramen van een woning optimaal geïsoleerd kunnen worden (zogenoemde streefwaarden). Bij een oude woning liggen de streefwaarden lager dan bij een nieuwe woning. Als een dak, vloer of raam optimaal is geïsoleerd, vermeldt het energielabel dat het voldoet aan de standaard voor woningisolatie.\n\nIs het tarief van de kinderopvang hoger dan de maximale vergoeding? Dan betalen de ouders het bedrag boven de maximale uurprijs zelf. Is het tarief van de kinderopvang lager dan de maximumprijs per uur? Dan krijgen ouders over dat goedkopere uurtarief kinderopvangtoeslag.\n\nHeeft u van de politie een bekeuring ontvangen voor het niet voldoen aan de identificatieplicht? Dan kunt u hiertegen geen bezwaar maken. Van het Centraal Justitieel Incassobureau (CJIB) ontvangt u een acceptgiro om de boete te betalen. Betaalt u de boete niet, dan beslist de officier van Justitie of u strafrechtelijk wordt vervolgd. Dit kan nog tot 2 jaar na de datum van de overtreding.\n\nBij een ramp kunnen mensen en bedrijven materiële schade lijden. Het kabinet kan gedupeerden dan helpen met de Wet tegemoetkoming schade bij rampen (Wts). Dankzij de Wts kunnen gedupeerden onder voorwaarden, een financiële tegemoetkoming krijgen voor de geleden schade en kosten. Het gaat daarbij alleen om schade die niet verhaalbaar, niet vermijdbaar en niet redelijkerwijs verzekerbaar is.\n\nVogelgriep verspreidt zich in Nederland door bijvoorbeeld trekvogels. Dit heeft grote gevolgen voor de natuur en pluimveebedrijven. De Rijksoverheid neemt bij verdenking van vogelgriep maatregelen om verspreiding tegen te gaan. Ook is er een plan om besmetting met het virus zo veel mogelijk te voorkomen.\n\nDe mensen in het gaswinningsgebied willen dat de overheid voorrang geeft aan het verbeteren van de schadeafhandeling. En de versterking van onveilige huizen zo snel mogelijk afrondt. 29 van de 50 maatregelen die de overheid neemt, zijn bedoeld om dit voor elkaar te krijgen.\n\nGemeenten hebben per 1 februari 2024 met de Wet gemeentelijke taak mogelijk maken asielopvangvoorzieningen (Spreidingswet) een wettelijke taak in de opvang van asielzoekers. Het doel van de wet is te komen tot voldoende opvangplekken en een evenwichtiger verdeling van asielzoekers over provincies en gemeenten.\n\nOm terug te keren naar het land van herkomst heeft de vreemdeling een geldig reisdocument nodig, zoals een paspoort. Het komt voor dat vreemdelingen geen geldig reisdocument hebben. Het land van herkomst moet de vreemdeling dan identificeren. Daarnaast regelt het land van herkomst van de vreemdeling een (vervangend) reisdocument, zoals een noodreisdocument (een laissez-passer).\n\nDe basisschool bewaart verschillende gegevens over uw kind in een leerlingdossier, zoals de leerresultaten. U en de school mogen deze gegevens inzien. In speciale gevallen mogen anderen dat ook, zoals in een noodsituatie of bij een vermoeden van kindermishandeling."
debug = True
db_suggestions, model_suggestions = suggest_replacements(text, debug=debug)
reformed_text = fill_in_replacements(model_suggestions, db_suggestions, text, debug=debug)

print("Original text:")
print(text)
print("\nReformed text:")
print(reformed_text)

print(f"Execution time: {time.time() - start_time:.2f} seconds")
## print all the stopwords
#print(stopwords)


# print the words types of the whole sentence
# doc = nlp(text)
# for token in doc:
#     print(token.text, token.pos_)
    

