module.exports = {
  "daemon": true,
  "run": [
    {
      "method": "log",
      "params": {
        "raw": "Starting Virtual Model Emulator..."
      }
    },
    {
      "method": "shell.run",
      "params": {
        // This line must be changed. Use the venv parameter correctly.
        "message": "python -m server.main",
        "venv": "env", // Pinokio will now use the venv's Python
        "on": [
          {
            // Keep your PINOKIO_STARTUP regex.
            "event": "/PINOKIO_STARTUP: (http:\\/\\/localhost:[0-9]+\\/config\\.html)/",
            "done": true
          }
        ]
      }
    },
    {
      "method": "local.set",
      "params": {
        "url": "{{input.event[1]}}"
      }
    },
    {
      "method": "log",
      "params": {
        "raw": "UI ready at {{input.event[1]}}"
      }
    }
  ]
}