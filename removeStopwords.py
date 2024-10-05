import nltk
from nltk.corpus import stopwords

# Download Dutch stopwords if not already present
nltk.download('stopwords')

# Get Dutch stopwords
stop_words = set(stopwords.words('dutch'))

# Example list of words (that could be from frequency list)
words = ['dag', 'de', 'huis', 'man', 'mooi', 'en', 'tijd']

# Filter out stopwords
filtered_words = [word for word in words if word not in stop_words]
print(filtered_words)
