/** @type {import('tailwindcss').Config} */
module.exports = {
  // 指定需要扫描的文件
  content: [
    './index.html', 
    './src/**/*.{html,js,ts,jsx,tsx,vue}', 
    './pages/**/*.{html,js,ts,jsx,tsx,vue}', 
    './components/**/*.{html,js,ts,jsx,tsx,vue}'
  ],
  theme: {
    extend: {},
  },
  // 核心配置：禁用 preflight，防止覆盖 UniApp 基础样式
  corePlugins: {
    preflight: false,
  },
}