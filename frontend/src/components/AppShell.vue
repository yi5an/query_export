<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">QueryExport</div>
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        class="nav-item"
        :class="{ active: route.path === item.to }"
        :to="item.to"
      >
        {{ item.label }}
      </RouterLink>
    </aside>

    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { to: '/query', label: 'SQL 查询' },
  { to: '/datasources', label: '数据源管理' },
  { to: '/saved-sqls', label: '保存的 SQL' },
  { to: '/tasks', label: '导出任务' },
  { to: '/settings', label: '设置' }
]
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 176px minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 20px 12px;
  background: linear-gradient(180deg, #162333 0%, #24364d 100%);
}

.brand {
  margin-bottom: 10px;
  color: #fff;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.nav-item {
  border-radius: 10px;
  padding: 10px 12px;
  color: rgba(227, 236, 246, 0.78);
  text-decoration: none;
  transition: 0.2s ease;
  font-size: 14px;
}

.nav-item:hover,
.nav-item.active {
  background: rgba(70, 144, 247, 0.16);
  color: #8fc1ff;
}

.content {
  padding: 20px 22px;
}

@media (max-width: 960px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
  }

  .brand {
    width: 100%;
  }
}
</style>
