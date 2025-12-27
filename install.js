module.exports = {
  run: [
    // Install Python dependencies
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "pip install -r requirements.txt"
        ],
      }
    },
    // Create marker file to indicate successful installation
    {
      method: "fs.writeFile",
      params: {
        path: "env/.installed",
        content: "Installation completed successfully"
      }
    }
  ]
}
