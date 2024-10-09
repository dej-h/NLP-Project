const express = require('express');
const app = express();
const port = 3000;

// Middleware to parse JSON request bodies
app.use(express.json());

// Endpoint to handle POST requests from Chrome extension
app.post('/extract', (req, res) => {
  const { text } = req.body;

  console.log("Received text from Chrome extension:", text);

  // Simulated response with complex words and their synonyms (as described)
  const simulatedResponse = [
    "3|0.8|simple,easy|0.2,0.1|0.4,0.5",     // Replace word at position 3
    "8|0.7|basic,elementary|0.3,0.4|0.2,0.3", // Replace word at position 8
    "NONE" // If no synonyms are found for a certain position
  ];

  // Send the simulated response back to the Chrome extension
  res.json({ replacements: simulatedResponse });
});

// Start the server
app.listen(port, () => {
  console.log(`Backend server running on http://localhost:${port}`);
});