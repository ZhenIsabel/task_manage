<script>
export default {
  onLaunch: function () {
    console.log('App Launch')
  },
  onShow: function () {
    console.log('App Show')
  },
  onHide: function () {
    console.log('App Hide')
  },
}
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;
/*每个页面公共css */
@import 'tailwindcss/base';
@import 'tailwindcss/components';
@import 'tailwindcss/utilities';


html, body {
  margin: 0;
  padding: 0;
}

page {
  background-color: #f2f2f7;
}

/* 公共 Glass 卡片 */
.glass-card {
  background: $glass-bg;
  border: 1px solid $glass-border;
  box-shadow: $shadow;
  border-radius: 20px;
  overflow: hidden;
}

/* 子页面公共导航样式（edit / archive / settings 根节点加 page-with-nav） */
.page-with-nav .nav-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}
.page-with-nav .glass-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.page-with-nav .nav-title {
  font-size: 17px;
  font-weight: 600;
  color: #111827;
}
.page-with-nav .header-text-col {
  flex: 1;
  margin-left: 12px;
}
</style>
