const express = require('express');
const { spawn } = require('child_process'); // To execute Python script
const app = express();
const port = 3000;

// Middleware to parse JSON request bodies
app.use(express.json());

// Endpoint to handle POST requests from Chrome extension
app.post('/extract', (req, res) => {
  const { text } = req.body;

  console.log("Received text from Chrome extension:", text);

  // Call Python script
  const pythonProcess = spawn('python', ['./NLP-project/Test_backend/getSynonymsDB.py', text]);

  let dataToSend = '';

  // Collect data from Python script
  pythonProcess.stdout.on('data', (data) => {
    dataToSend += data.toString();
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Error: ${data}`);
  });

  // When the Python process finishes, send the result back
  pythonProcess.on('close', (code) => {
    if (code === 0) {
      // Send the response back to the Chrome extension
      res.json({ replacements: dataToSend.split(';') });
    } else {
      res.status(500).send('Error executing Python script');
    }
  });
});

// Start the server
app.listen(port, () => {
  console.log(`Backend server running on http://localhost:${port}`);
});
