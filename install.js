module.exports = {
  "run": [
    {
      "method": "log",
      "params": {
        "raw": "Installing Python dependencies..."
      }
    },
    {
      "method": "shell.run",
      "params": {
        "message": "pip install -r requirements.txt",
        "venv": "env", // Key: Tells Pinokio to run this INSIDE the virtual env
        "path": "."
      }
    },
    {
      "method": "log",
      "params": {
        "raw": "Installation complete!"
      }
    }
  ]
}