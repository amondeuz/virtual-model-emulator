module.exports = {
  run: [
    {
      method: "process.kill",
      params: {
        pid: "start.js"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python stop_postgres.py",
        onError: "continue"
      }
    },
    {
      method: "notify",
      params: {
        title: "Virtual Model Emulator",
        body: "All services stopped"
      }
    }
  ]
};
