module.exports = async (kernel, info, { onCancel }) => {
  let cwd = info.cwd;

  // 1. Install core dependencies
  await kernel.run({
    command: 'pip install -r requirements.txt',
    cwd: cwd,
    env: {},
    onCancel: onCancel
  });

  await kernel.run({
    command: 'pip install prisma',
    cwd: cwd,
    env: {},
    onCancel: onCancel
  });

  // 2. CRITICAL FIX: Generate Prisma client INSIDE the package directory
  // This ensures the generated files are placed where the Python import system can find them.
  await kernel.run({
    command: 'cd "env\\Lib\\site-packages\\litellm_proxy_extras" && prisma generate',
    cwd: cwd,
    env: {},
    onCancel: onCancel
  });

  // 3. Generate config.yaml with wildcard models for all 9 providers
  await kernel.run({
    command: 'python -c "import secrets; key=\'sk-\'+secrets.token_hex(16); open(\'config.yaml\',\'w\').write(\'model_list:\\n  - model_name: \\\"cerebras/*\\\"\\n    litellm_params:\\n      model: \\\"cerebras/*\\\"\\n      api_key: \\\"os.environ/CEREBRAS_API_KEY\\\"\\n  - model_name: \\\"groq/*\\\"\\n    litellm_params:\\n      model: \\\"groq/*\\\"\\n      api_key: \\\"os.environ/GROQ_API_KEY\\\"\\n  - model_name: \\\"bytez/*\\\"\\n    litellm_params:\\n      model: \\\"bytez/*\\\"\\n      api_key: \\\"os.environ/BYTEZ_API_KEY\\\"\\n  - model_name: \\\"deepseek/*\\\"\\n    litellm_params:\\n      model: \\\"deepseek/*\\\"\\n      api_key: \\\"os.environ/DEEPSEEK_API_KEY\\\"\\n  - model_name: \\\"gemini/*\\\"\\n    litellm_params:\\n      model: \\\"gemini/*\\\"\\n      api_key: \\\"os.environ/GEMINI_API_KEY\\\"\\n  - model_name: \\\"huggingface/*\\\"\\n    litellm_params:\\n      model: \\\"huggingface/*\\\"\\n      api_key: \\\"os.environ/HF_TOKEN\\\"\\n  - model_name: \\\"openrouter/*\\\"\\n    litellm_params:\\n      model: \\\"openrouter/*\\\"\\n      api_key: \\\"os.environ/OPENROUTER_API_KEY\\\"\\n  - model_name: \\\"aiml/*\\\"\\n    litellm_params:\\n      model: \\\"aiml/*\\\"\\n      api_key: \\\"os.environ/AIML_API_KEY\\\"\\n  - model_name: \\\"cloudflare/*\\\"\\n    litellm_params:\\n      model: \\\"cloudflare/*\\\"\\n      api_key: \\\"os.environ/CLOUDFLARE_API_KEY\\\"\\n\\ngeneral_settings:\\n  master_key: \'+key+\'\\n  database_url: \\\"sqlite:///./litellm.db\\\"\\n\\nlitellm_settings:\\n  drop_params: true\\n  check_provider_endpoint: true\\n\')"',
    cwd: cwd,
    env: {},
    onCancel: onCancel
  });

  // 4. Create installation marker
  await kernel.write('env/.installed', '');
  return true;
};
