#!/usr/bin/env python3
"""Generate config.yaml with wildcard models for all providers."""
import secrets

key = 'sk-' + secrets.token_hex(16)

config = f'''model_list:
  - model_name: aiml-wildcard
    litellm_params:
      model: aiml_api/*
      api_key: os.environ/AIML_API_KEY
  - model_name: bytez-wildcard
    litellm_params:
      model: bytez/*
      api_key: os.environ/BYTEZ_API_KEY
  - model_name: cerebras-wildcard
    litellm_params:
      model: cerebras/*
      api_key: os.environ/CEREBRAS_API_KEY
  - model_name: cloudflare-wildcard
    litellm_params:
      model: cloudflare/*
      api_key: os.environ/CLOUDFLARE_API_KEY
  - model_name: deepseek-wildcard
    litellm_params:
      model: deepseek/*
      api_key: os.environ/DEEPSEEK_API_KEY
  - model_name: gemini-wildcard
    litellm_params:
      model: gemini/*
      api_key: os.environ/GEMINI_API_KEY
  - model_name: groq-wildcard
    litellm_params:
      model: groq/*
      api_key: os.environ/GROQ_API_KEY
  - model_name: huggingface-wildcard
    litellm_params:
      model: huggingface/*
      api_key: os.environ/HUGGINGFACE_API_KEY
  - model_name: openrouter-wildcard
    litellm_params:
      model: openrouter/*
      api_key: os.environ/OPENROUTER_API_KEY

general_settings:
  master_key: {key}

litellm_settings:
  drop_params: true
  check_provider_endpoint: true
'''

with open('config.yaml', 'w') as f:
    f.write(config)

print(f"Generated config.yaml with master_key: {key[:10]}...")
