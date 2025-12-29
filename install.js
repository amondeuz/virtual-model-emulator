module.exports = {
  run: [
    // Step 1: Install and upgrade core dependencies
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "python -m pip install --upgrade pip",
          "pip install --upgrade litellm[proxy]",
          "pip install --upgrade prisma"
        ]
      }
    },
    // Step 2: Modify Prisma schema for SQLite and generate client
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: `python -c "
import subprocess, sys, os, re
site_packages = next(p for p in sys.path if 'site-packages' in p)
src_schema = os.path.join(site_packages, 'litellm_proxy_extras', 'schema.prisma')
print(f'[INFO] Copying schema from: {src_schema}')
with open(src_schema, 'r') as f:
    content = f.read()
sqlite_datasource = '''datasource db {
  provider = \"sqlite\"
  url      = \"file:./litellm.db\"
}'''
content = re.sub(r'datasource\\\\s+db\\\\s*\\\\{[^}]+\\\\}', sqlite_datasource, content, flags=re.DOTALL)
with open('schema.prisma', 'w') as f:
    f.write(content)
print('[INFO] Generated SQLite-compatible schema.prisma')
subprocess.run(['prisma', 'generate', '--schema=schema.prisma'], check=True)
print('[SUCCESS] Prisma client generated.')
"`
      }
    },
    // NEW Step 3A: Write a simple Python script to generate config.yaml
    {
      method: "fs.write",
      params: {
        path: "generate_config.py",
        text: `import secrets, pathlib

# Generate a secure master key for LiteLLM
master_key = 'sk-' + secrets.token_hex(16)

config_content = f'''model_list:
  - model_name: "cerebras/*"
    litellm_params:
      model: "cerebras/*"
      api_key: "os.environ/CEREBRAS_API_KEY"
  - model_name: "groq/*"
    litellm_params:
      model: "groq/*"
      api_key: "os.environ/GROQ_API_KEY"
  - model_name: "bytez/*"
    litellm_params:
      model: "bytez/*"
      api_key: "os.environ/BYTEZ_API_KEY"
  - model_name: "deepseek/*"
    litellm_params:
      model: "deepseek/*"
      api_key: "os.environ/DEEPSEEK_API_KEY"
  - model_name: "gemini/*"
    litellm_params:
      model: "gemini/*"
      api_key: "os.environ/GEMINI_API_KEY"
  - model_name: "huggingface/*"
    litellm_params:
      model: "huggingface/*"
      api_key: "os.environ/HF_TOKEN"
  - model_name: "openrouter/*"
    litellm_params:
      model: "openrouter/*"
      api_key: "os.environ/OPENROUTER_API_KEY"
  - model_name: "aiml/*"
    litellm_params:
      model: "aiml/*"
      api_key: "os.environ/AIML_API_KEY"
  - model_name: "cloudflare/*"
    litellm_params:
      model: "cloudflare/*"
      api_key: "os.environ/CLOUDFLARE_API_KEY"

general_settings:
  master_key: {master_key}
  database_url: "sqlite:///./litellm.db"

litellm_settings:
  drop_params: true
  check_provider_endpoint: true
'''

pathlib.Path('config.yaml').write_text(config_content)
print('[SUCCESS] config.yaml generated.')`
      }
    },
    // NEW Step 3B: Run the Python script we just created
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python generate_config.py"
      }
    },
    // Step 5: Create installation marker
    {
      method: "fs.write",
      params: {
        path: "env/.installed",
        text: ""
      }
    }
  ]
};
