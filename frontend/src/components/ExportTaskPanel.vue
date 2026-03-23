<template>
  <div class="page-card panel">
    <div class="toolbar">
      <div>
        <h2 class="section-title">{{ title }}</h2>
        <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
      </div>
      <el-button @click="loadTasks">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="tasks" stripe max-height="420">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="export_format" label="格式" width="88" />
      <el-table-column prop="status" label="状态" width="92">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="row_count" label="行数" width="76" />
      <el-table-column prop="created_at" label="创建时间" min-width="150" />
      <el-table-column label="剩余保留时间" min-width="140">
        <template #default="{ row }">
          {{ formatRetention(row) }}
        </template>
      </el-table-column>
      <el-table-column label="SQL" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">{{ row.sql_text }}</template>
      </el-table-column>
      <el-table-column label="操作" width="124" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'completed'"
            link
            type="primary"
            @click="downloadTask(row.id)"
          >
            下载
          </el-button>
          <el-button link type="danger" @click="removeTask(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import type { ExportTask } from '@/types'

const props = withDefaults(
  defineProps<{
    title?: string
    subtitle?: string
    refreshKey?: number
  }>(),
  {
    title: '导出任务',
    subtitle: '导出文件默认保留 7 天，过期后自动清理。',
    refreshKey: 0
  }
)

const loading = ref(false)
const tasks = ref<ExportTask[]>([])

onMounted(loadTasks)

watch(
  () => props.refreshKey,
  () => {
    void loadTasks()
  }
)

async function loadTasks() {
  loading.value = true
  try {
    tasks.value = await api.listExports()
  } catch (error: unknown) {
    ElMessage.error('加载导出任务失败')
  } finally {
    loading.value = false
  }
}

async function removeTask(id: number) {
  try {
    await ElMessageBox.confirm('确认删除该导出任务？', '删除确认', { type: 'warning' })
    await api.deleteExport(id)
    ElMessage.success('任务已删除')
    await loadTasks()
  } catch (error: unknown) {
    if (error) {
      ElMessage.error('删除任务失败')
    }
  }
}

function downloadTask(id: number) {
  window.open(api.exportDownloadUrl(id), '_blank', 'noopener,noreferrer')
}

function statusType(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return 'info'
}

function formatRetention(task: ExportTask) {
  if (task.status === 'pending' || task.status === 'running') {
    return '生成中'
  }
  if (task.remaining_seconds == null) {
    return '-'
  }
  if (task.remaining_seconds <= 0) {
    return '即将清理'
  }

  const days = Math.floor(task.remaining_seconds / 86400)
  const hours = Math.floor((task.remaining_seconds % 86400) / 3600)
  const minutes = Math.floor((task.remaining_seconds % 3600) / 60)

  if (days > 0) {
    return `${days}天${hours}小时`
  }
  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  }
  return `${Math.max(minutes, 1)}分钟`
}
</script>

<style scoped>
.panel {
  padding: 18px 18px 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.subtitle {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}
</style>
