// Function to extract main text
function extractMainText() {
    let mainContent = document.querySelector('main, article, section');

    if (!mainContent) {
        mainContent = document.querySelectorAll('p, h1, h2, h3, h4');
    }

    let textContent = '';
    if (mainContent.length) {
        mainContent.forEach(el => {
            textContent += el.innerText + '\n\n';
        });
    } else {
        textContent = mainContent.innerText;
    }

    return textContent.trim();
}

// Function to highlight words in the text
function highlightWordsInNode(node, synonymsData) {
    if (node.nodeType === Node.TEXT_NODE) {
        const words = node.nodeValue.split(" ");
        const newContent = words.map((word, index) => {
            const synonymData = synonymsData.find(data => {
                if (data !== "NONE") {
                    const [position] = data.split("|");
                    return parseInt(position, 10) === index;
                }
                return false;
            });

            if (synonymData) {
                const [position, com_simp_score, synonymList, syn_comp_scores, rel_scores] = synonymData.split("|");
                const synonyms = synonymList.split(",");
                const synScores = syn_comp_scores.split(",").map(Number);
                const relScores = rel_scores.split(",").map(Number);

                // Check if the original score is lower than all synonym scores
                const originalScore = parseFloat(com_simp_score);
                const isHigher = synScores.every(score => originalScore > score);

                // Replace only if the original score is higher
                if (!isHigher && com_simp_score != 0) {
                    // Find the lowest scored synonym with a relatedness score above the threshold
                    const threshold = 0.5; // relatedness threshold
                    const validSynonyms = synonyms.filter((syn, idx) => relScores[idx] > threshold);
                    
                    if (validSynonyms.length > 0) {
                        // Find the lowest scored synonym based on synScores
                        const lowestScoredSynonymIndex = validSynonyms.map((_, idx) => synScores[synonyms.indexOf(validSynonyms[idx])])
                            .reduce((minIdx, score, idx, arr) => score < arr[minIdx] ? idx : minIdx, 0);
                        
                        return `<span style="background-color: green; color: white;" data-replaced="${word}">${validSynonyms[lowestScoredSynonymIndex]}</span>`;
                    }
                }
            }

            return word; // Return original word if no replacement
        });

        // Replace the text node with new content
        const newHTML = newContent.join(" ");
        const span = document.createElement("span");
        span.innerHTML = newHTML; // Use innerHTML to allow for <span> elements
        node.replaceWith(span); // Replace the original text node with the new span
    } else {
        // Recur for child nodes
        Array.from(node.childNodes).forEach(child => {
            highlightWordsInNode(child, synonymsData);
        });
    }
}

// Create tooltip for hover effect
function createTooltip(replacedWord) {
    const tooltip = document.createElement('div');
    tooltip.innerText = replacedWord;
    tooltip.style.position = 'absolute';
    tooltip.style.backgroundColor = 'red';
    tooltip.style.color = 'white';
    tooltip.style.padding = '5px';
    tooltip.style.borderRadius = '4px';
    tooltip.style.zIndex = '1000';
    tooltip.style.visibility = 'hidden'; // Hidden by default
    document.body.appendChild(tooltip);
    return tooltip;
}

// Add hover effect to the highlighted words
function addHoverEffect() {
    const highlights = document.querySelectorAll('span[style*="background-color: green"]');
    const tooltip = createTooltip('');

    highlights.forEach(span => {
        span.addEventListener('mouseover', (event) => {
            const replacedWord = event.target.getAttribute('data-replaced');
            tooltip.innerText = replacedWord;
            tooltip.style.visibility = 'visible';
            tooltip.style.left = `${event.pageX + 10}px`; // Position tooltip slightly to the right of the cursor
            tooltip.style.top = `${event.pageY + 10}px`;  // Position tooltip slightly below the cursor
        });

        span.addEventListener('mousemove', (event) => {
            tooltip.style.left = `${event.pageX + 10}px`;
            tooltip.style.top = `${event.pageY + 10}px`;
        });

        span.addEventListener('mouseout', () => {
            tooltip.style.visibility = 'hidden'; // Hide the tooltip when not hovering
        });
    });
}

// Listen for messages from popup to trigger text extraction
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "extractText") {
        const extractedText = extractMainText();

        // Send extracted text back to background for backend processing
        chrome.runtime.sendMessage({ text: extractedText });
    }

    if (message.synonyms) {
        const synonymsData = message.synonyms;
        highlightWordsInNode(document.body, synonymsData); // Call function to highlight words
        addHoverEffect(); // Add hover effect to highlighted words
        sendResponse({ status: "Words replaced successfully" });
    }
});
