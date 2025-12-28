module.exports = {
  run: [
    // Install Python dependencies
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "python -m pip install --upgrade pip",
          "pip install -r requirements.txt"
        ],
      }
    },
    // Generate config.yaml with wildcard models for all providers
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "python scripts/generate_config.py"
        ],
      }
    },
    // Create marker file
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "python -c \"import pathlib; pathlib.Path('env/.installed').write_text('Installation completed successfully')\""
        ],
      }
    }
  ]
}
