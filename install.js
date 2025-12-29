module.exports = {
  run: [
    {
      method: "fs.write",
      params: {
        path: "full_install.py",
        text: `# -*- coding: utf-8 -*-
import sys, os, re, subprocess, secrets, pathlib, site, json

def run_command(cmd, desc=""):
    """Helper to run a command and print status."""
    if desc:
        print(f"[INFO] {desc}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARNING] Command may have had issues: {result.stderr[:200]}")
    return result

print('='*60)
print('Virtual Model Emulator - Installation')
print('='*60)

# 1. INSTALL/UPGRADE DEPENDENCIES
print('\\n[1/4] Installing/Upgrading dependencies...')
run_command(f'"{sys.executable}" -m pip install --upgrade pip', "Upgrading pip")
run_command(f'"{sys.executable}" -m pip install --upgrade litellm[proxy]', "Installing litellm[proxy]")
run_command(f'"{sys.executable}" -m pip install --upgrade prisma', "Installing prisma")
print('[OK] Dependencies installed.')

# 2. MODIFY PRISMA SCHEMA FOR SQLITE
print('\\n[2/4] Configuring database for SQLite...')
schema_path = None
for p in sys.path:
    if p and 'site-packages' in p:
        test_path = os.path.join(p, 'litellm_proxy_extras', 'schema.prisma')
        if os.path.exists(test_path):
            schema_path = test_path
            break

if schema_path:
    print(f'Found schema at: {schema_path}')
    try:
        with open(schema_path, 'r') as f:
            content = f.read()
        
        sqlite_config = '''datasource db {
  provider = "sqlite"
  url      = "file:./litellm.db"
}'''
        pattern = r'datasource\\s+db\\s*{[^}]+}'
        new_content = re.sub(pattern, sqlite_config, content, flags=re.DOTALL)
        new_content = new_content.replace('env("DATABASE_URL")', '"file:./litellm.db"')
        
        with open(schema_path, 'w') as f:
            f.write(new_content)
        print('[OK] Schema modified for SQLite.')
        
        # Generate client
        os.chdir(os.path.dirname(schema_path))
        run_command('prisma generate', "Generating Prisma client")
        os.chdir(os.path.dirname(__file__))
        
    except Exception as e:
        print(f'[WARNING] Schema step skipped: {e}')
else:
    print('[WARNING] Could not find schema.prisma in expected location.')

# 3. GENERATE CONFIG.YAML (if missing)
print('\\n[3/4] Checking configuration...')
config_file = 'config.yaml'
if os.path.exists(config_file):
    print('[OK] config.yaml already exists.')
else:
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
    with open(config_file, 'w') as f:
        f.write(config_content)
    print(f'[OK] config.yaml generated.')

# 4. CREATE INSTALLATION MARKER
print('\\n[4/4] Finalizing installation...')
os.makedirs('env', exist_ok=True)
with open('env/.installed', 'w') as f:
    f.write('Installation completed successfully.')
print('[OK] Installation marker created.')

print('\\n' + '='*60)
print('INSTALLATION COMPLETE')
print('='*60)
`
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python full_install.py"
      }
    }
  ]
};
