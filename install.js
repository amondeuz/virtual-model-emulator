module.exports = async (kernel, info, onCancel) => {
  let cwd = info.cwd;

  // 1. Install core dependencies
  await kernel.execute({
    command: 'pip install "litellm[proxy]"',
    cwd: cwd,
    env: {},
    onCancel: onCancel
  });

  await kernel.execute({
    command: 'pip install prisma',
    cwd: cwd,
    env: {},
    onCancel: onCancel
  });

  // 2. Generate Prisma client - FIXED PATH ISSUE
  await kernel.execute({
    command: 'npx prisma generate',
    cwd: cwd,
    env: {},
    onCancel: onCancel
  });

  // 3. Create installation marker
  await kernel.write('env/.installed', '');
  return true;
};
