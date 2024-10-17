from transformers import pipeline

# Load a simpler model for testing (GPT-2 Small Dutch)
generator = pipeline("text-generation", model="GroNLP/gpt2-small-dutch")

# Provide a simple prompt
response = generator("Geef me enkele suggesties voor een film.", max_new_tokens=50)
print(response[0]["generated_text"])
