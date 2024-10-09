
function extractMainText() {
  
  // Try selecting common main content tags
  let mainContent = document.querySelector('main, article, section');
  
  if (!mainContent) {
      // Fallback to paragraphs if no specific main content element is found
      mainContent = document.querySelectorAll('p, h1, h2, h3, h4');
  }

  // Collect innerText from the elements (and concatenate multiple elements if necessary)
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

// Send the extracted text to the background script
chrome.runtime.sendMessage({ text: extractMainText() });

// Function to replace words based on positions and synonyms
function replaceWordsWithSynonyms(text, synonymsData) {
  const words = text.split(" ");
  
  synonymsData.forEach(data => {
      if (data !== "NONE") {
          const [position, , synonymList] = data.split("|");
          const positionIndex = parseInt(position, 10);
          const synonyms = synonymList.split(",");

          // Replace the word at the specified position with the first synonym
          if (positionIndex < words.length && synonyms.length > 0) {
              words[positionIndex] = synonyms[0];
          }
      }
  });

  return words.join(" ");
}

// Listen for the message from the background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.synonyms) {
      const extractedText = document.body.innerText;
      const newText = replaceWordsWithSynonyms(extractedText, message.synonyms);

      // Replace the entire document body text with the updated version
      document.body.innerText = newText;

      // Send a response to the background script
      sendResponse({ status: "Words replaced successfully" });
  }
});
