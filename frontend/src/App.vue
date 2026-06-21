<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <el-config-provider>
    <div class="app-container">
      <header class="app-header">
        <h1>📝 中小学单元测试卷自动生成系统</h1>
      </header>
      <main class="app-main">
        <RouterView />
      </main>
    </div>
  </el-config-provider>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.app-header {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  padding: 16px 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.app-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.app-main {
  flex: 1;
  padding: 24px;
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}
</style>
