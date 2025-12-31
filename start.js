module.exports = {
  daemon: true,
  run: [
    // Step 1: Start PostgreSQL
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python start_postgres.py",
        on: [{ event: "/PostgreSQL ready/", done: true }]
      }
    },
    // Step 2: Start LiteLLM with DATABASE_URL loaded
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python start_litellm.py",
        on: [{ event: "/Uvicorn running/", done: true }]
      }
    },
    // Step 3: Start Flask server
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
