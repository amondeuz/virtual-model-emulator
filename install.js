module.exports = async (kernel, info, onCancel) => {
  let cwd = info.cwd;

  // 1. Install core dependencies
  await kernel.run({
    command: 'pip install litellm[proxy]', // Removed outer quotes
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

  // 2. Generate Prisma client from the project root
  await kernel.run({
    command: 'npx prisma generate',
    cwd: cwd, // Assuming schema.prisma is in the project root
    env: {},
    onCancel: onCancel
  });

  // 3. Create installation marker
  await kernel.write('env/.installed', '');
  return true;
};
