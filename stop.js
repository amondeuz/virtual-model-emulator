module.exports = {
  run: [
    {
      method: "process.kill",
      params: {
        pid: "start.js"
      }
    },
    {
      method: "notify",
      params: {
        title: "Virtual Model Emulator",
        body: "Service stopped"
      }
    }
  ]
};
