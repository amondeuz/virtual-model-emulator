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
    // Install Prisma for LiteLLM database features
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "pip install prisma",
      }
    },
    // Generate Prisma client for LiteLLM
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python -c \"import litellm, os, subprocess; schema=os.path.join(os.path.dirname(litellm.__file__), 'proxy', 'prisma', 'schema.prisma'); subprocess.run(['prisma', 'generate', '--schema=' + schema], check=True)\"",
      }
    },
    // Generate config.yaml with wildcard models for all 9 providers
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "python -c \"import secrets; key='sk-'+secrets.token_hex(16); open('config.yaml','w').write('model_list:\\n  - model_name: \\\"cerebras/*\\\"\\n    litellm_params:\\n      model: \\\"cerebras/*\\\"\\n      api_key: \\\"os.environ/CEREBRAS_API_KEY\\\"\\n  - model_name: \\\"groq/*\\\"\\n    litellm_params:\\n      model: \\\"groq/*\\\"\\n      api_key: \\\"os.environ/GROQ_API_KEY\\\"\\n  - model_name: \\\"bytez/*\\\"\\n    litellm_params:\\n      model: \\\"bytez/*\\\"\\n      api_key: \\\"os.environ/BYTEZ_API_KEY\\\"\\n  - model_name: \\\"deepseek/*\\\"\\n    litellm_params:\\n      model: \\\"deepseek/*\\\"\\n      api_key: \\\"os.environ/DEEPSEEK_API_KEY\\\"\\n  - model_name: \\\"gemini/*\\\"\\n    litellm_params:\\n      model: \\\"gemini/*\\\"\\n      api_key: \\\"os.environ/GEMINI_API_KEY\\\"\\n  - model_name: \\\"huggingface/*\\\"\\n    litellm_params:\\n      model: \\\"huggingface/*\\\"\\n      api_key: \\\"os.environ/HF_TOKEN\\\"\\n  - model_name: \\\"openrouter/*\\\"\\n    litellm_params:\\n      model: \\\"openrouter/*\\\"\\n      api_key: \\\"os.environ/OPENROUTER_API_KEY\\\"\\n  - model_name: \\\"aiml/*\\\"\\n    litellm_params:\\n      model: \\\"aiml/*\\\"\\n      api_key: \\\"os.environ/AIML_API_KEY\\\"\\n  - model_name: \\\"cloudflare/*\\\"\\n    litellm_params:\\n      model: \\\"cloudflare/*\\\"\\n      api_key: \\\"os.environ/CLOUDFLARE_API_KEY\\\"\\n\\ngeneral_settings:\\n  master_key: '+key+'\\n  database_url: \\\"sqlite:///./litellm.db\\\"\\n\\nlitellm_settings:\\n  drop_params: true\\n  check_provider_endpoint: true\\n')\""
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
