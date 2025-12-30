module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "litellm --config config.yaml --port 11434 --host 127.0.0.1",
        on: [{ event: "/Uvicorn running/", done: true }]
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python server.py",
        on: [{ event: "/http:\\/\\/\\S+/", done: true }]
      }
    },
    {
      method: "local.set",
      params: {
        url: "http://localhost:8765/config.html"
      }
    }
  ]
}
