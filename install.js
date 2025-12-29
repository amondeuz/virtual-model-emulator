module.exports = {
  run: [
    // Step 1: Install/upgrade all Python dependencies
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
    // Step 2A: Write the script to modify the Prisma schema IN-PLACE
    {
      method: "fs.write",
      params: {
        path: "fix_prisma_schema.py",
        text: `import sys, os, re, subprocess, pathlib

print("[INFO] Starting Prisma schema modification...")

# 1. Find the 'litellm_proxy_extras' package to get the ORIGINAL schema.prisma
package_path = None
for p in sys.path:
    if 'site-packages' in p:
        test_path = os.path.join(p, 'litellm_proxy_extras')
        if os.path.exists(test_path):
            package_path = test_path
            break

if not package_path:
    raise FileNotFoundError("Could not find 'litellm_proxy_extras' package.")

schema_path = os.path.join(package_path, 'schema.prisma')
print(f"[INFO] Modifying package schema at: {schema_path}")

# 2. Read the original schema
with open(schema_path, 'r') as f:
    content = f.read()

# 3. CRITICAL: Change from PostgreSQL to SQLite IN THE ORIGINAL FILE
sqlite_config = '''datasource db {
  provider = "sqlite"
  url      = "file:./litellm.db"
}'''

# Use regex to find and replace the entire datasource block
pattern = r'datasource\\s+db\\s*{[^}]+}'
new_content = re.sub(pattern, sqlite_config, content, flags=re.DOTALL)

# Also ensure any env("DATABASE_URL") is replaced
new_content = new_content.replace('env("DATABASE_URL")', '"file:./litellm.db"')

# 4. Write the changes back to the ORIGINAL package file
with open(schema_path, 'w') as f:
    f.write(new_content)
print("[SUCCESS] Package schema.prisma updated for SQLite.")

# 5. Generate the Prisma client FROM THE MODIFIED PACKAGE SCHEMA
print("[INFO] Generating Prisma client...")
result = subprocess.run(
    ['prisma', 'generate', '--schema', schema_path],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"[ERROR] Prisma generation failed. Output:\\n{result.stderr}")
    raise RuntimeError("Prisma client generation failed.")
else:
    print("[SUCCESS] Prisma client generated from modified schema.")
    print(f"[DEBUG] Stdout: {result.stdout}")
`
      }
    },
    // Step 2B: Run the schema fix script
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python fix_prisma_schema.py"
      }
    },
    // Step 3A: Write the config.yaml generator
    {
      method: "fs.write",
      params: {
        path: "make_config.py",
        text: `import secrets, pathlib

print("[INFO] Generating LiteLLM config.yaml...")
master_key = 'sk-' + secrets.token_hex(16)

config = f'''model_list:
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

pathlib.Path('config.yaml').write_text(config)
print(f"[SUCCESS] config.yaml generated with master key.")
`
      }
    },
    // Step 3B: Run the config generator
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python make_config.py"
      }
    },
    // Step 4: Create the installation marker
    {
      method: "fs.write",
      params: {
        path: "env/.installed",
        text: ""
      }
    }
  ]
};
