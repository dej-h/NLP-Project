document.getElementById("extract").addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      // Send a message to the content script to extract the text
      chrome.tabs.sendMessage(tabs[0].id, { action: "extractText" });
  });
});
