def load_idx_file(idx_file):
    idx_data = {}
    with open(idx_file, 'r', encoding='ISO8859-1') as file:
        for line in file:
            if '|' in line:
                word, pos = line.strip().split('|')
                idx_data[word] = int(pos)
    return idx_data

def get_all_synonyms(dat_file, word, idx_data):
    if word not in idx_data:
        return None

    synonyms = []
    start_pos = idx_data[word]
    with open(dat_file, 'r', encoding='ISO8859-1') as file:
        # Jump to the start position from the .idx file
        file.seek(start_pos)
        
        for line in file:
            if line.startswith(word + '|'):
                # Start reading synonyms after finding the word
                for next_line in file:
                    next_line = next_line.strip()
                    if next_line.startswith('-|'):
                        synonym = next_line.split('|')[1]
                        synonyms.append(synonym)
                    else:
                        # Break if we hit a new word entry
                        break
                break
    return synonyms

# Load the index file
idx_data = load_idx_file('sym_database/th_nl_v2.idx')

# Retrieve all synonyms
word = "a"
synonyms = get_all_synonyms('sym_database/th_nl_v2.dat', word, idx_data)
print(f"Synonyms for {word}: {synonyms}")
