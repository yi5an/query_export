import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '@/components/AppShell.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppShell,
      children: [
        {
          path: '',
          redirect: '/query'
        },
        {
          path: 'query',
          name: 'query',
          component: () => import('@/views/QueryEditor.vue')
        },
        {
          path: 'datasources',
          name: 'datasources',
          component: () => import('@/views/DataSourceManage.vue')
        },
        {
          path: 'saved-sqls',
          name: 'saved-sqls',
          component: () => import('@/views/SavedSqlList.vue')
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('@/views/TaskList.vue')
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/Settings.vue')
        }
      ]
    }
  ]
})

export default router
