chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    const backendUrl = "http://localhost:3000/extract"; // Your backend URL

    // Ensure the message contains the 'text'
    if (message.text) {
        console.log("Sending text to backend:", message.text);

        // Send the extracted text to the backend
        fetch(backendUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: message.text }) // Send text to backend
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Send the received replacements data to content script
            chrome.tabs.sendMessage(sender.tab.id, { synonyms: data.replacements }, () => {
                if (chrome.runtime.lastError) {
                    console.error('Error sending message to content script:', chrome.runtime.lastError);
                } else {
                    console.log('Synonyms sent to content script:', data.replacements);
                }
            });
        })
        .catch(error => {
            console.error('Error sending data to backend', error);
            sendResponse({ status: "error", message: error.message });
        });

        // Return true to indicate asynchronous response
        return true;
    }
});
