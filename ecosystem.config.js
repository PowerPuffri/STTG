module.exports = {
  apps: [
    {
      name: "SillyTavern",
      script: "server.js",
      cwd: "./SillyTavern",
      interpreter: "node",
      args: "",
      env: {
        NODE_ENV: "production",
        PORT: 8000
      },
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: "../logs/st-error.log",
      out_file: "../logs/st-out.log"
    },
    {
      name: "ChatBridge-Forwarder",
      script: "SillyTavern/public/scripts/extensions/third-party/SillyTavern-Extension-ChatBridge/ChatBridge_APIHijackForwarder.py",
      interpreter: "python3",
      cwd: ".",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: "./logs/bridge-error.log",
      out_file: "./logs/bridge-out.log"
    },
    {
      name: "Telegram-Adapter",
      script: "telegram_adapter.py",
      interpreter: "python3",
      cwd: ".",
      // 使用环境变量获取 Token，避免硬编码
      // 请在启动前设置 ST_BOT_TOKEN 环境变量，或者在 secrets.json 中配置
      args: "--token " + (process.env.ST_BOT_TOKEN || "YOUR_BOT_TOKEN_HERE") + " --admin_pass " + (process.env.ST_ADMIN_PASS || "123456"),
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: "./logs/bot-error.log",
      out_file: "./logs/bot-out.log"
    }
  ]
};
