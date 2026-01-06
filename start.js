module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python app_launcher.py",
        on: [{ event: "/All services started and verified/", done: true }]
      }
    },
    {
      method: "local.set",
      params: {
        url: "http://localhost:8775/config.html"
      }
    }
  ]
}
