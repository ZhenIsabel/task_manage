module.exports = {
    plugins: {
      tailwindcss: {},
      autoprefixer: {},
      // 如果需要将 Tailwind 的默认 rem 单位转为 rpx
      'postcss-rem-to-responsive-pixel': {
        rootValue: 32,
        propList: ['*'],
        transformUnit: 'rpx',
      },
    },
  }
  