module.exports = {
  run: [
    // Step 1: Install Python and Prisma dependencies
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "python -m pip install --upgrade pip",
          "pip install 'litellm[proxy]' prisma"
        ]
      }
    },
    // Step 2: CRITICAL - Modify Prisma schema for SQLite and generate client
    // This step converts the datasource from PostgreSQL to SQLite.
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: `python -c "
import subprocess, sys, os, shutil, re
# Find the site-packages directory
site_packages = next(p for p in sys.path if 'site-packages' in p)
src_schema = os.path.join(site_packages, 'litellm_proxy_extras', 'schema.prisma')
print(f'[INFO] Copying schema from: {src_schema}')
# Read and modify the schema
with open(src_schema, 'r') as f:
    content = f.read()
# Replace PostgreSQL datasource with SQLite
sqlite_datasource = '''datasource db {
  provider = \"sqlite\"
  url      = \"file:./litellm.db\"
}'''
content = re.sub(r'datasource\\s+db\\s*\\{[^}]+\\}', sqlite_datasource, content, flags=re.DOTALL)
# Write the modified schema locally
with open('schema.prisma', 'w') as f:
    f.write(content)
print('[INFO] Generated SQLite-compatible schema.prisma')
# Generate the Prisma client
subprocess.run(['prisma', 'generate', '--schema=schema.prisma'], check=True)
print('[SUCCESS] Prisma client generated.')
"`
      }
    },
    // Step 3: Generate the main LiteLLM config.yaml
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: `python -c "
import secrets, pathlib
# Generate a secure master key for LiteLLM
master_key = 'sk-' + secrets.token_hex(16)
config_content = '''model_list:
  - model_name: \"cerebras/*\"
    litellm_params:
      model: \"cerebras/*\"
      api_key: \"os.environ/CEREBRAS_API_KEY\"
  # ... [Include all other provider blocks from your working file here]
general_settings:
  master_key: {master_key}
  database_url: \"sqlite:///./litellm.db\"
litellm_settings:
  drop_params: true
  check_provider_endpoint: true
'''
pathlib.Path('config.yaml').write_text(config_content)
print(f'[SUCCESS] config.yaml generated with master key.')
"`
      }
    },
    // Step 4: Create installation marker
    {
      method: "fs.write",
      params: {
        path: "env/.installed",
        text: ""
      }
    }
  ]
};
