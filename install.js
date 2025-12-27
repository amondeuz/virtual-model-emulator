module.exports = {
  run: [
    {
      method: "log",
      params: {
        raw: "Installing Python dependencies..."
      }
    },
    {
      method: "shell.run",
      params: {
        // Change this line to use the venv's pip directly
        message: ".\\env\\Scripts\\pip install -r requirements.txt",
        path: "."
        // Remove the "venv": "env" line entirely
      }
    },
    {
      method: "log",
      params: {
        raw: "Installation complete!"
      }
    }
  ]
}
