module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: "git pull",
        onError: "continue"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python -m pip install --upgrade pip"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python -m pip install --upgrade litellm"
      }
    },
    {
      method: "notify",
      params: {
        title: "Virtual Model Emulator",
        body: "Update complete. Please restart the app."
      }
    }
  ]
};
