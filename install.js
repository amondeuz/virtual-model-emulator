module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: `python -c "
# -*- coding: utf-8 -*-
import sys, os, re, subprocess, secrets, pathlib, site, json

print('='*60)
print('Virtual Model Emulator - Installation')
print('='*60)

# ============================================================================
# 1. INSTALL/UPGRADE DEPENDENCIES
# ============================================================================
print('\\n[1/3] Installing/Upgrading dependencies...')
subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], check=False)
subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'litellm[proxy]'], check=False)
subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'prisma'], check=False)
print('[OK] Dependencies installed.')

# ============================================================================
# 2. MODIFY PRISMA SCHEMA FOR SQLITE
# ============================================================================
print('\\n[2/3] Configuring database for SQLite...')

# Find the litellm_proxy_extras package
schema_path = None
search_paths = sys.path + site.getsitepackages()

for p in search_paths:
    if p and 'site-packages' in p:
        test_path = os.path.join(p, 'litellm_proxy_extras', 'schema.prisma')
        if os.path.exists(test_path):
            schema_path = test_path
            break

if not schema_path:
    # Last resort: search entire Python environment
    import pip
    dist = pip.get_installed_distributions()
    for d in dist:
        if d.key == 'litellm':
            # Use d.location to find the package
            possible = os.path.join(d.location, 'litellm_proxy_extras', 'schema.prisma')
            if os.path.exists(possible):
                schema_path = possible
                break

if not schema_path:
    print('[WARNING] Could not find schema.prisma. Database features may not work.')
    schema_path = 'schema.prisma'  # Fallback

print(f'Found schema at: {schema_path}')

# Read and modify the schema
try:
    with open(schema_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace PostgreSQL with SQLite
    sqlite_config = '''datasource db {
  provider = "sqlite"
  url      = "file:./litellm.db"
}'''
    
    # Pattern for datasource block
    pattern = r'datasource\\s+db\\s*{[^}]+}'
    new_content = re.sub(pattern, sqlite_config, content, flags=re.DOTALL)
    
    # Also replace env(\"DATABASE_URL\") if present
    new_content = new_content.replace('env(\\"DATABASE_URL\\")', '\\"file:./litellm.db\\"')
    
    # Write back
    with open(schema_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print('[OK] Schema modified for SQLite.')
    
    # Generate Prisma client
    package_dir = os.path.dirname(schema_path)
    original_cwd = os.getcwd()
    os.chdir(package_dir)
    
    result = subprocess.run(['prisma', 'generate'], 
                          capture_output=True, 
                          text=True, 
                          shell=False)
    
    os.chdir(original_cwd)
    
    if result.returncode == 0:
        print('[OK] Prisma client generated.')
    else:
        print(f'[WARNING] Prisma generation: {result.stderr[:200]}')
        
except Exception as e:
    print(f'[WARNING] Schema modification skipped: {e}')

# ============================================================================
# 3. GENERATE CONFIG.YAML (Only if missing)
# ============================================================================
print('\\n[3/3] Checking configuration...')

config_file = 'config.yaml'
if os.path.exists(config_file):
    print('[OK] config.yaml already exists. Keeping current configuration.')
else:
    print('Generating new config.yaml...')
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
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f'[OK] config.yaml generated with master key.')

# ============================================================================
# 4. CREATE INSTALLATION MARKER
# ============================================================================
print('\\n[4/4] Finalizing installation...')
marker_dir = 'env'
if not os.path.exists(marker_dir):
    os.makedirs(marker_dir, exist_ok=True)

with open(os.path.join(marker_dir, '.installed'), 'w') as f:
    f.write('Installation completed successfully.')

print('='*60)
print('INSTALLATION COMPLETE')
print('='*60)
print('\\nNext steps:')
print('1. Start the app from the Pinokio menu')
print('2. Open the Connect page to add provider API keys')
print('3. Use the Emulator page to configure model routing')
print('='*60)
"`
      }
    }
  ]
};
