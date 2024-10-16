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

// Function to replace words with synonyms
function replaceWordsWithSynonyms(text, synonymsData) {
    const words = text.split(" ");
    
    synonymsData.forEach(data => {
        if (data !== "NONE") {
            const [position, , synonymList] = data.split("|");
            const positionIndex = parseInt(position, 10);
            const synonyms = synonymList.split(",");

            if (positionIndex < words.length && synonyms.length > 0) {
                words[positionIndex] = synonyms[0];
            }
        }
    });

    return words.join(" ");
}

// Listen for messages from popup to trigger text extraction
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "extractText") {
        const extractedText = extractMainText();

        // Send extracted text back to background for backend processing
        chrome.runtime.sendMessage({ text: extractedText });
    }
    
    if (message.synonyms) {
        const extractedText = document.body.innerText;
        const newText = replaceWordsWithSynonyms(extractedText, message.synonyms);

        document.body.innerText = newText;
        sendResponse({ status: "Words replaced successfully" });
    }
});