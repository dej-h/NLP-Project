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

  const pythonProcess = spawn('python', ['getSynonymsDB.py']);

  // Write the text to the Python process via stdin
  pythonProcess.stdin.write(text);
  pythonProcess.stdin.end();

  let dataToSend = '';

  pythonProcess.stdout.on('data', (data) => {
    dataToSend += data.toString();
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Error: ${data}`);
  });

  pythonProcess.on('close', (code) => {
    if (code === 0) {
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
