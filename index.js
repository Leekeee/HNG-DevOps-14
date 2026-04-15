const express = require('express');
const app = express();
const PORT = 3000; // internal port — Nginx will proxy to this

app.get('/', (req, res) => {
  res.status(200).json({ message: "API is running" });
});

app.get('/health', (req, res) => {
  res.status(200).json({ message: "healthy" });
});

app.get('/me', (req, res) => {
  res.status(200).json({
    name: "OLANREWAJU Oluwagbemileke",
    email: "lekenoch18@gmail.com",
    github: "https://github.com/Leekeee"
  });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});