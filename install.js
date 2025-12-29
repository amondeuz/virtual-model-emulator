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
    // NEW DEBUG STEP: Check if LiteLLM extras are installed
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python -c \"import pkgutil; print('LiteLLM extras found:', pkgutil.find_loader('litellm_proxy_extras') is not None)\"",
        onError: "continue" // Don't stop if this fails
      }
    },
    // Step 2A: Write the Prisma modification script
    {
      method: "fs.write",
      params: {
        path: "modify_prisma_schema.py",
        text: `import subprocess, sys, os, re

# Find the site-packages directory
site_packages = next(p for p in sys.path if 'site-packages' in p)
print(f'[DEBUG] Site-packages path: {site_packages}')
src_schema = os.path.join(site_packages, 'litellm_proxy_extras', 'schema.prisma')
print(f'[INFO] Copying schema from: {src_schema}')

# Check if source file exists
if not os.path.exists(src_schema):
    print(f'[ERROR] Schema file not found at: {src_schema}')
    print('[INFO] Checking common locations...')
    # Try a common alternative path pattern
    import site
    for sitedir in site.getsitepackages():
        check_path = os.path.join(sitedir, 'litellm_proxy_extras', 'schema.prisma')
        print(f'  Checking: {check_path}')
        if os.path.exists(check_path):
            src_schema = check_path
            print(f'[INFO] Found schema at: {src_schema}')
            break
    else:
        raise FileNotFoundError(f'Could not find schema.prisma in any known location')

# Read and modify the schema
with open(src_schema, 'r') as f:
    content = f.read()

# Replace PostgreSQL datasource with SQLite
sqlite_datasource = '''datasource db {
  provider = "sqlite"
  url      = "file:./litellm.db"
}'''
content = re.sub(r'datasource\\s+db\\s*\\{[^}]+\\}', sqlite_datasource, content, flags=re.DOTALL)

# Write the modified schema locally
with open('schema.prisma', 'w') as f:
    f.write(content)
print('[INFO] Generated SQLite-compatible schema.prisma')

# Generate the Prisma client
print('[INFO] Generating Prisma client...')
result = subprocess.run(['prisma', 'generate', '--schema=schema.prisma'], capture_output=True, text=True)
if result.returncode != 0:
    print(f'[ERROR] Prisma generation failed: {result.stderr}')
    raise RuntimeError('Prisma client generation failed')
print('[SUCCESS] Prisma client generated.')`
      }
    },
    // Step 2B: Run the Prisma modification script
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python modify_prisma_schema.py"
      }
    },
    // Step 3A: Write the config generation script
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
    // Step 3B: Run the config generation script
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python generate_config.py"
      }
    },
    // Step 4: Create installation marker
    {
      method: "fs.write",
      params: {
        path: "env/.installed",
        text: "Installation completed successfully"
      }
    },
    // NEW FINAL STEP: Verify installation
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python -c \"import os; print(f'Installation marker exists: {os.path.exists(\\\"env/.installed\\\")}')\""
      }
    }
  ]
};
