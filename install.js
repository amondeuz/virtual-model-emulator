module.exports = {
  run: [
    // Step 1: Install and upgrade all dependencies
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
    // Step 2: CRITICAL - Modify Prisma schema IN-PLACE and generate client
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: `python -c "
import sys, os, re, subprocess, pathlib, json

# Find the actual installed litellm_proxy_extras package
package_path = None
for p in sys.path:
    if 'site-packages' in p and os.path.exists(p):
        test_dir = os.path.join(p, 'litellm_proxy_extras')
        if os.path.exists(test_dir):
            package_path = test_dir
            break

if not package_path:
    import site
    for sitedir in site.getsitepackages():
        test_dir = os.path.join(sitedir, 'litellm_proxy_extras')
        if os.path.exists(test_dir):
            package_path = test_dir
            break

if not package_path:
    raise FileNotFoundError('Could not find litellm_proxy_extras package.')

schema_file = os.path.join(package_path, 'schema.prisma')
print(f'[INFO] Modifying schema at: {schema_file}')

# Read, modify, and write back to package location
with open(schema_file, 'r') as f:
    content = f.read()

# Replace PostgreSQL with SQLite configuration
sqlite_config = '''datasource db {
  provider = \"sqlite\"
  url      = \"file:./litellm.db\"
}'''

# Replace the datasource block
new_content = re.sub(r'datasource\\s+db\\s*{[^}]+}', sqlite_config, content, flags=re.DOTALL)

# Also replace any env(\"DATABASE_URL\") references
new_content = new_content.replace('env(\"DATABASE_URL\")', '\"file:./litellm.db\"')

# Write back to the original package file
with open(schema_file, 'w') as f:
    f.write(new_content)
print('[SUCCESS] Package schema updated for SQLite.')

# Generate Prisma client from the modified schema
print('[INFO] Generating Prisma client...')
os.chdir(package_path)
result = subprocess.run(['prisma', 'generate'], capture_output=True, text=True)
if result.returncode == 0:
    print('[SUCCESS] Prisma client generated.')
else:
    print(f'[WARNING] Prisma generation had issues: {result.stderr[:200]}')
"`
      }
    },
    // Step 3: Generate config.yaml
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: `python -c "
import secrets, pathlib
master_key = 'sk-' + secrets.token_hex(16)
config = f'''model_list:
  - model_name: \"cerebras/*\"
    litellm_params:
      model: \"cerebras/*\"
      api_key: \"os.environ/CEREBRAS_API_KEY\"
  - model_name: \"groq/*\"
    litellm_params:
      model: \"groq/*\"
      api_key: \"os.environ/GROQ_API_KEY\"
  - model_name: \"bytez/*\"
    litellm_params:
      model: \"bytez/*\"
      api_key: \"os.environ/BYTEZ_API_KEY\"
  - model_name: \"deepseek/*\"
    litellm_params:
      model: \"deepseek/*\"
      api_key: \"os.environ/DEEPSEEK_API_KEY\"
  - model_name: \"gemini/*\"
    litellm_params:
      model: \"gemini/*\"
      api_key: \"os.environ/GEMINI_API_KEY\"
  - model_name: \"huggingface/*\"
    litellm_params:
      model: \"huggingface/*\"
      api_key: \"os.environ/HF_TOKEN\"
  - model_name: \"openrouter/*\"
    litellm_params:
      model: \"openrouter/*\"
      api_key: \"os.environ/OPENROUTER_API_KEY\"
  - model_name: \"aiml/*\"
    litellm_params:
      model: \"aiml/*\"
      api_key: \"os.environ/AIML_API_KEY\"
  - model_name: \"cloudflare/*\"
    litellm_params:
      model: \"cloudflare/*\"
      api_key: \"os.environ/CLOUDFLARE_API_KEY\"
general_settings:
  master_key: {master_key}
  database_url: \"sqlite:///./litellm.db\"
litellm_settings:
  drop_params: true
  check_provider_endpoint: true
'''
pathlib.Path('config.yaml').write_text(config)
print('[SUCCESS] config.yaml generated.')
"`
      }
    },
    // Step 4: Create installation marker
    {
      method: "fs.write",
      params: {
        path: "env/.installed",
        text: "Installation completed"
      }
    }
  ]
};
