module.exports = {
  daemon: true,
  run: [
    // Step 1: Validate configuration
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python validate_config.py",
        on: [{ event: "/Environment validated/", done: true }]
      }
    },
    // Step 2: Start PostgreSQL
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python start_postgres.py",
        on: [{ event: "/PostgreSQL ready/", done: true }]
      }
    },
    // Step 3: Start LiteLLM with DATABASE_URL loaded
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python start_litellm.py",
        on: [{ event: "/Application startup complete|Uvicorn running/", done: true }]
      }
    },
    // Step 4: Start API server
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
        url: "http://localhost:8775/config.html"
      }
    }
  ]
}
