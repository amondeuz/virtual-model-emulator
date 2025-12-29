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
    // Step 2: Write and run a script to modify the Prisma schema IN-PLACE
    {
      method: "fs.write",
      params: {
        path: "step2_fix_schema.py",
        text: `import sys, os, re, subprocess, site

print("[1/3] Locating the litellm_proxy_extras package...")
package_path = None
# Search sys.path first
for p in sys.path:
    if 'site-packages' in p and os.path.exists(p):
        test_path = os.path.join(p, 'litellm_proxy_extras', 'schema.prisma')
        if os.path.exists(test_path):
            package_path = os.path.dirname(test_path)
            break

# Fallback to site.getsitepackages()
if not package_path:
    for sitedir in site.getsitepackages():
        test_path = os.path.join(sitedir, 'litellm_proxy_extras', 'schema.prisma')
        if os.path.exists(test_path):
            package_path = os.path.dirname(test_path)
            break

if not package_path:
    raise FileNotFoundError("Could not find the litellm_proxy_extras package.")

schema_path = os.path.join(package_path, 'schema.prisma')
print(f"[2/3] Modifying schema at: {schema_path}")

# Read the schema
with open(schema_path, 'r') as f:
    content = f.read()

# Replace PostgreSQL with SQLite
sqlite_config = '''datasource db {
  provider = "sqlite"
  url      = "file:./litellm.db"
}'''
new_content = re.sub(r'datasource\\s+db\\s*{[^}]+}', sqlite_config, content, flags=re.DOTALL)
new_content = new_content.replace('env("DATABASE_URL")', '"file:./litellm.db"')

# Write it back
with open(schema_path, 'w') as f:
    f.write(new_content)

# Generate the Prisma client
os.chdir(package_path)
result = subprocess.run(['prisma', 'generate'], capture_output=True, text=True)
if result.returncode == 0:
    print("[3/3] Success: Prisma client generated from modified schema.")
else:
    print(f"[WARNING] Prisma generation output: {result.stderr[:300]}")
`
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python step2_fix_schema.py"
      }
    },
    // Step 3: Write and run a script to generate config.yaml
    {
      method: "fs.write",
      params: {
        path: "step3_make_config.py",
        text: `import secrets, pathlib, os

print("[INFO] Generating config.yaml...")

# Only generate if it doesn't exist, or you want to force a new key
# To force a new key, remove this check.
if os.path.exists('config.yaml'):
    print("[INFO] config.yaml already exists. Skipping generation.")
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
    pathlib.Path('config.yaml').write_text(config_content)
    print(f"[SUCCESS] config.yaml generated with new master key.")
`
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python step3_make_config.py"
      }
    },
    // Step 4: Create the final installation marker
    {
      method: "fs.write",
      params: {
        path: "env/.installed",
        text: "Installation completed successfully."
      }
    }
  ]
};
