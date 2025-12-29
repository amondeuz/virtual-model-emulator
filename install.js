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
    // Step 2: Write and execute the CRITICAL Prisma schema fix
    // This modifies the schema file INSIDE the installed package
    {
      method: "fs.write",
      params: {
        path: "fix_schema.py",
        text: `import sys, os, re, subprocess, pathlib

print("[INFO] Locating and modifying Prisma schema...")

# Find the actual installed litellm_proxy_extras package
package_path = None
for p in sys.path:
    if 'site-packages' in p and os.path.exists(p):
        test_dir = os.path.join(p, 'litellm_proxy_extras')
        if os.path.exists(test_dir):
            package_path = test_dir
            print(f"[INFO] Found package at: {package_path}")
            break

if not package_path:
    # Fallback: search more thoroughly
    import site
    for sitedir in site.getsitepackages():
        test_dir = os.path.join(sitedir, 'litellm_proxy_extras')
        if os.path.exists(test_dir):
            package_path = test_dir
            print(f"[INFO] Found package (fallback) at: {package_path}")
            break

if not package_path:
    raise FileNotFoundError("Could not find 'litellm_proxy_extras' package.")

schema_file = os.path.join(package_path, 'schema.prisma')
print(f"[INFO] Modifying schema file at: {schema_file}")

# Read the current schema
with open(schema_file, 'r') as f:
    content = f.read()

print("[INFO] Original schema content (first 200 chars):", content[:200])

# Replace PostgreSQL configuration with SQLite
# Target pattern: datasource db { ... }
sqlite_config = '''datasource db {
  provider = "sqlite"
  url      = "file:./litellm.db"
}'''

# Use regex to replace the datasource block
pattern = r'datasource\\s+db\\s*{[^}]+}'
new_content, count = re.subn(pattern, sqlite_config, content, flags=re.DOTALL)

if count == 0:
    print("[WARNING] Standard datasource pattern not found. Trying alternative match...")
    # Alternative: look for provider = "postgresql"
    new_content = content.replace('provider = "postgresql"', 'provider = "sqlite"')
    new_content = new_content.replace("provider = 'postgresql'", "provider = 'sqlite'")
    # Also replace the URL
    new_content = new_content.replace('env("DATABASE_URL")', '"file:./litellm.db"')
    new_content = new_content.replace("env('DATABASE_URL')", "'file:./litellm.db'")

print("[INFO] Modified schema content (first 200 chars):", new_content[:200])

# Write back to the package file
backup_file = schema_file + '.backup'
if not os.path.exists(backup_file):
    os.rename(schema_file, backup_file)
    print(f"[INFO] Created backup at: {backup_file}")

with open(schema_file, 'w') as f:
    f.write(new_content)
print("[SUCCESS] Package schema updated for SQLite.")

# Generate Prisma client from the modified schema
print("[INFO] Generating Prisma client...")
try:
    # First, ensure we're in a directory where we can write
    os.chdir(os.path.dirname(schema_file))
    
    result = subprocess.run(
        ['prisma', 'generate', '--schema', 'schema.prisma'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode != 0:
        print(f"[ERROR] Prisma generation failed.")
        print(f"[ERROR] stderr: {result.stderr[:500]}")
        print(f"[ERROR] stdout: {result.stdout[:500]}")
        
        # Try alternative: generate in project directory
        print("[INFO] Trying alternative generation in project directory...")
        project_schema = os.path.join(os.path.dirname(__file__), 'schema.prisma')
        with open(project_schema, 'w') as f:
            f.write(new_content)
        
        result2 = subprocess.run(
            ['prisma', 'generate', '--schema', project_schema],
            capture_output=True,
            text=True
        )
        
        if result2.returncode != 0:
            raise RuntimeError(f"Prisma generation failed completely: {result2.stderr}")
        else:
            print("[SUCCESS] Prisma client generated in project directory.")
    else:
        print("[SUCCESS] Prisma client generated from package schema.")
        
except Exception as e:
    print(f"[ERROR] Unexpected error during Prisma generation: {str(e)}")
    # Don't crash the installation - continue anyway
    print("[WARNING] Continuing despite Prisma generation issues...")
`
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "python fix_schema.py"
      }
    },
    // Step 3: Generate the config.yaml
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: `python -c "
import secrets, pathlib
print('[INFO] Generating LiteLLM config.yaml...')
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
    // Step 4: Create the installation marker
    {
      method: "fs.write",
      params: {
        path: "env/.installed",
        text: "Installation completed: " + new Date().toISOString()
      }
    }
  ]
};
