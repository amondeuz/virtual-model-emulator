module.exports = {
  run: [
    // Install Python dependencies and create marker file in a single shell step
    // This ensures the marker file is created even if step transitions fail
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "python -m pip install --upgrade pip",
          "pip install -r requirements.txt",
          "python -c \"import pathlib; pathlib.Path('env/.installed').write_text('Installation completed successfully')\""
        ],
      }
    }
  ]
}
