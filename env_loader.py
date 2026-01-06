"""Environment variable loader with safe defaults."""
import os


def load_env(env_file='.env'):
    """Load environment variables from .env file with graceful fallback."""
    env_vars = os.environ.copy()

    if not os.path.exists(env_file):
        print(f'[INFO] {env_file} not found, using defaults', flush=True)
        # Provide defaults for first-time setup
        env_vars.setdefault('API_SERVER_PORT', '8775')
        return env_vars

    try:
        with open(env_file, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove surrounding quotes
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    env_vars[key] = value
        return env_vars
    except Exception as e:
        print(f'[WARN] Error loading {env_file}: {e}', flush=True)
        return env_vars
