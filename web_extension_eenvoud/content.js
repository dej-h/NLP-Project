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
                if (synonyms.length > 0 && synonyms[0] !== "NONE") {
                    return `<span style="background-color: green; color: white;">${synonyms[0]}</span>`;
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
        sendResponse({ status: "Words replaced successfully" });
    }
});
