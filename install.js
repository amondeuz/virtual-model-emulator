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
          `python -c "
import secrets
key = 'sk-' + secrets.token_hex(16)
config = '''model_list:
  - model_name: openai-wildcard
    litellm_params:
      model: openai/*
      api_key: os.environ/OPENAI_API_KEY
  - model_name: anthropic-wildcard
    litellm_params:
      model: anthropic/*
      api_key: os.environ/ANTHROPIC_API_KEY
  - model_name: groq-wildcard
    litellm_params:
      model: groq/*
      api_key: os.environ/GROQ_API_KEY
  - model_name: mistral-wildcard
    litellm_params:
      model: mistral/*
      api_key: os.environ/MISTRAL_API_KEY
  - model_name: gemini-wildcard
    litellm_params:
      model: gemini/*
      api_key: os.environ/GEMINI_API_KEY
  - model_name: cohere-wildcard
    litellm_params:
      model: cohere/*
      api_key: os.environ/COHERE_API_KEY
  - model_name: together-wildcard
    litellm_params:
      model: together_ai/*
      api_key: os.environ/TOGETHER_API_KEY
  - model_name: openrouter-wildcard
    litellm_params:
      model: openrouter/*
      api_key: os.environ/OPENROUTER_API_KEY
  - model_name: deepseek-wildcard
    litellm_params:
      model: deepseek/*
      api_key: os.environ/DEEPSEEK_API_KEY
  - model_name: cerebras-wildcard
    litellm_params:
      model: cerebras/*
      api_key: os.environ/CEREBRAS_API_KEY

general_settings:
  master_key: ''' + key + '''

litellm_settings:
  drop_params: true
  check_provider_endpoint: true
'''
open('config.yaml', 'w').write(config)
"`
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
