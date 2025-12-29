module.exports = async (kernel, info, onCancel) => {  // CORRECT: onCancel is the third parameter
  let cwd = info.cwd;

  // 1. Install core dependencies
  await kernel.run({
    command: 'pip install "litellm[proxy]"',
    cwd: cwd,
    env: {},
    onCancel: onCancel  // Pass the parameter directly
  });

  await kernel.run({
    command: 'pip install prisma',
    cwd: cwd,
    env: {},
    onCancel: onCancel  // Pass the parameter directly
  });

  // 2. Generate Prisma client INSIDE the package directory
  await kernel.run({
    command: 'cd "env\\Lib\\site-packages\\litellm_proxy_extras" && prisma generate',
    cwd: cwd,
    env: {},
    onCancel: onCancel  // Pass the parameter directly
  });

  // 3. Create installation marker
  await kernel.write('env/.installed', '');
  return true;
};
