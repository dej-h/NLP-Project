from nltk.corpus import wordnet as wn
import nltk

# Ensure OMW is downloaded
import nltk
nltk.download('omw-1.4')

# Access Dutch WordNet via synsets
dutch_synsets = wn.synsets('geweldig', lang='nld')  # 'hond' is Dutch for 'dog'
print("Dutch synsets for 'vloer':", dutch_synsets)
for synset in dutch_synsets:
    print(f"\nSynonyms in synset '{synset.name()}': {[lemma.name() for lemma in synset.lemmas('nld')]}")
