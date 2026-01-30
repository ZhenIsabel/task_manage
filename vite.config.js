import { defineConfig } from 'vite';
import path from 'path';
import uni from '@dcloudio/vite-plugin-uni';
// 引入插件
import { UnifiedViteWeappTailwindcssPlugin as uvtw } from 'weapp-tailwindcss/vite';

export default defineConfig({
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  plugins: [
    uni(),
    // 添加插件
    uvtw({
      rem2rpx: true, // 开启 rem 转 rpx
      disabled: false, // 是否禁用
      // 其他配置...
    })
  ],
});