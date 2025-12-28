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
    // Generate config.yaml with master key
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "python -c \"import secrets; key='sk-'+secrets.token_hex(16); open('config.yaml','w').write('model_list: []\\n\\ngeneral_settings:\\n  master_key: '+key+'\\n\\nlitellm_settings:\\n  drop_params: true\\n')\""
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
