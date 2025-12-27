module.exports = {
  version: '5.3.0',
  title: 'Virtual Model Emulator',
  description: 'OpenAI-compatible endpoint powered by LiteLLM. Supports 100+ AI providers.',
  icon: 'icon.png',
  menu: async (kernel, info) => {
    const updateItem = { text: 'Update', icon: 'fa-solid fa-rotate', href: 'update.js' };

    const installing = info.running('install.js');
    if (installing) {
      return [
        { text: 'Installing...', icon: 'fa-solid fa-spinner', href: 'install.js' },
        updateItem
      ];
    }

    const installed = info.exists('env/.installed');
    if (!installed) {
      return [
        { text: 'Install', icon: 'fa-solid fa-download', href: 'install.js', default: true },
        updateItem
      ];
    }

    const running = info.running('start.js');
    if (!running) {
      return [
        { text: 'Start', icon: 'fa-solid fa-play', href: 'start.js', default: true },
        updateItem
      ];
    }

    const mem = info.local('start.js');
    const url = mem && mem.url;

    if (!url) {
      return [
        { text: 'Starting...', icon: 'fa-solid fa-spinner', href: 'start.js' },
        updateItem
      ];
    }

    return [
      { text: 'Connect', icon: 'fa-solid fa-plug', href: url.replace('config.html', 'connect.html') },
      { text: 'Emulator', icon: 'fa-solid fa-robot', href: url, default: true },
      updateItem
    ];
  }
};
