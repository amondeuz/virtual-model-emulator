module.exports = {
  daemon: true,
  run: [
    {
      method: "log",
      params: {
        raw: "Starting Virtual Model Emulator..."
      }
    },
    {
      method: "shell.run",
      params: {
        // Change this line to use the venv's Python directly
        message: ".\\env\\Scripts\\python -m server.main",
        // Remove the "venv": "env" line entirely
        on: [
          {
            "event": "/PINOKIO_STARTUP: (http:\\/\\/localhost:[0-9]+\\/config\\.html)/",
            "done": true
          }
        ]
      }
    },
    {
      method: "local.set",
      params: {
        url: "{{input.event[1]}}"
      }
    },
    {
      method: "log",
      params: {
        raw: "UI ready at {{input.event[1]}}"
      }
    }
  ]
}
