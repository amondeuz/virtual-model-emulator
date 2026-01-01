module.exports = {
  run: [{
    method: "shell.run",
    params: {
      venv: "env",
      message: "python stop_postgres.py"
    }
  }]
};
