chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const backendUrl = "http://localhost:3000/extract"; // Backend URL

  // Send the extracted text to the backend
  fetch(backendUrl, {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify({ text: message.text }) // Sending text to backend
  })
  .then(response => response.json())
  .then(data => {
      // Send the received replacements data to content script
      chrome.tabs.sendMessage(sender.tab.id, { synonyms: data.replacements });
  })
  .catch(error => {
      console.error('Error sending data to backend:', error);
  });
});