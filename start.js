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
        message: ".\\env\\Scripts\\python -m server.main",
        // KEY CHANGE: This new, standard regex catches any standard HTTP URL
        on: [{
          "event": "/http:\\/\\/[^\\s]+/", // This matches "http://" followed by any non-space chars
          "done": true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        // KEY CHANGE: Use event[0] which is the *entire matched string*
        url: "{{input.event[0]}}"
      }
    },
    {
      method: "log",
      params: {
        raw: "UI ready at {{input.event[0]}}"
      }
    }
  ]
}
