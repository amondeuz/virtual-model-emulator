const title = 'Virtual Model Emulator';
const description = 'OpenAI-compatible endpoint powered by LiteLLM. Supports 100+ AI providers.';
const icon = 'icon.png';

module.exports = {
  version: '4.0',
  title,
  description,
  icon,
  menu: async (kernel, info) => {
    const updateItem = { text: 'Update', icon: 'fa-solid fa-rotate', href: 'update.js' };

    const installing = info.running('install.js');
    if (installing) {
      return [
        { text: 'Loading...', icon: 'fa-solid fa-robot', href: 'install.js' },
        updateItem
      ];
    }

    // Check if dependencies are installed (marker file exists means install.js completed successfully)
    const installed = info.exists('env/.installed');
    if (!installed) {
      return [
        { text: 'Install', icon: 'fa-solid fa-download', href: 'install.js', default: true },
        updateItem
      ];
    }

    const starting = info.running('start.js');
    if (!starting) {
      return [
        { text: 'Starting...', icon: 'fa-solid fa-robot', href: 'start.js', default: true },
        updateItem
      ];
    }

    const mem = info.local('start.js');
    const url = mem && mem.url;

    if (!url) {
      return [
        { text: 'Starting...', icon: 'fa-solid fa-robot', href: 'start.js' },
        updateItem
      ];
    }

    // Build the connect URL - same host as the main URL
    const connectUrl = url.replace('/config.html', '/connect.html');

    return [
      { text: 'Connect', icon: 'fa-solid fa-plug', href: connectUrl },
      { text: 'Emulator', icon: 'fa-solid fa-robot', href: url, default: true },
      updateItem
    ];
  }
};
