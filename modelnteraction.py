from transformers import AutoTokenizer, AutoModelForMaskedLM, AutoModelForSequenceClassification
import torch

# Load tokenizer and models
tokenizer = AutoTokenizer.from_pretrained("wietsedv/bert-base-dutch-cased")
mask_model = AutoModelForMaskedLM.from_pretrained("wietsedv/bert-base-dutch-cased")

# For sequence similarity scoring
similarity_model = AutoModelForSequenceClassification.from_pretrained("DTAI-KULeuven/robbert-2023-dutch-base")
similarity_tokenizer = AutoTokenizer.from_pretrained("DTAI-KULeuven/robbert-2023-dutch-base")

# Function to generate candidate synonyms
def generate_candidates(sentence, word_to_replace):
    masked_sentence = sentence.replace(word_to_replace, tokenizer.mask_token)
    inputs = tokenizer(masked_sentence, return_tensors="pt")
    
    with torch.no_grad():
        outputs = mask_model(**inputs)
    
    mask_token_index = torch.where(inputs['input_ids'] == tokenizer.mask_token_id)[1]
    mask_token_logits = outputs.logits[0, mask_token_index, :]
    top_tokens = torch.topk(mask_token_logits, 5, dim=1).indices[0].tolist()
    
    candidates = [tokenizer.decode([token]).strip() for token in top_tokens]
    return candidates

# Function to score sentence similarity
def score_similarity(original_sentence, modified_sentence):
    inputs = similarity_tokenizer([original_sentence, modified_sentence], return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = similarity_model(**inputs)
    logits = outputs.logits
    # Assuming binary classification, you might take the probability of the positive class (logits[:, 1])
    similarity_score = torch.softmax(logits, dim=1)[0][1].item()
    return similarity_score

# Main function to suggest replacements
def suggest_replacements(sentence, word_to_replace):
    candidates = generate_candidates(sentence, word_to_replace)
    suggestions = []

    for candidate in candidates:
        modified_sentence = sentence.replace(word_to_replace, candidate)
        similarity_score = score_similarity(sentence, modified_sentence)
        suggestions.append((candidate, similarity_score))
    
    # Sort suggestions by similarity score in descending order
    suggestions = sorted(suggestions, key=lambda x: x[1], reverse=True)
    return suggestions

# Example sentence
sentence = "Het was een mooie dag, en de kinderen speelden vrolijk in het park terwijl de zon scheen."
word_to_replace = "mooie"

# Get replacement suggestions
suggestions = suggest_replacements(sentence, word_to_replace)
print(f"Suggestions for '{word_to_replace}': {suggestions}")

