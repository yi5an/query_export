<template>
  <div class="page-card panel">
    <div class="toolbar">
      <div>
        <h2 class="section-title">{{ title }}</h2>
        <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
      </div>
      <div class="toolbar-actions">
        <el-input
          v-model="search"
          clearable
          placeholder="搜索 SQL"
          size="small"
          @change="loadList"
        />
        <el-select
          v-model="datasourceId"
          clearable
          placeholder="筛选数据源"
          size="small"
          @change="loadList"
        >
          <el-option v-for="item in datasources" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </div>
    </div>

    <el-table v-loading="loading" :data="savedSqls" stripe max-height="320">
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="comment" label="注释" min-width="200" show-overflow-tooltip />
      <el-table-column label="标签" min-width="160">
        <template #default="{ row }">
          <el-space wrap>
            <el-tag v-for="tag in row.tags || []" :key="tag" size="small">{{ tag }}</el-tag>
          </el-space>
        </template>
      </el-table-column>
      <el-table-column prop="run_count" label="运行次数" width="86" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openSql(row)">查看</el-button>
          <el-button link type="success" @click="useSql(row)">使用</el-button>
          <el-button link type="danger" @click="removeSql(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="drawerOpen" title="SQL 详情" size="48%">
      <h3>{{ activeSql?.name }}</h3>
      <p>{{ activeSql?.comment || '无注释' }}</p>
      <pre class="code-block">{{ activeSql?.sql_text }}</pre>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import type { Datasource, SavedSql } from '@/types'

const props = withDefaults(
  defineProps<{
    title?: string
    subtitle?: string
    datasourceId?: number
    refreshKey?: number
  }>(),
  {
    title: '保存的 SQL',
    subtitle: '',
    refreshKey: 0
  }
)

const emit = defineEmits<{
  (event: 'useSql', sql: string, datasourceId?: number): void
}>()

const loading = ref(false)
const search = ref('')
const datasourceId = ref<number | undefined>(props.datasourceId)
const savedSqls = ref<SavedSql[]>([])
const datasources = ref<Datasource[]>([])
const drawerOpen = ref(false)
const activeSql = ref<SavedSql | null>(null)

onMounted(async () => {
  await Promise.all([loadDatasources(), loadList()])
})

watch(
  () => props.datasourceId,
  (value) => {
    datasourceId.value = value
    void loadList()
  }
)

watch(
  () => props.refreshKey,
  () => {
    void loadList()
  }
)

async function loadDatasources() {
  datasources.value = await api.listDatasources()
}

async function loadList() {
  loading.value = true
  try {
    savedSqls.value = await api.listSavedSqls({
      search: search.value || undefined,
      datasource_id: datasourceId.value
    })
  } catch (error: unknown) {
    ElMessage.error('加载保存 SQL 列表失败')
  } finally {
    loading.value = false
  }
}

function openSql(row: SavedSql) {
  activeSql.value = row
  drawerOpen.value = true
}

function useSql(row: SavedSql) {
  emit('useSql', row.sql_text, row.datasource_id)
}

async function removeSql(id: number) {
  try {
    await ElMessageBox.confirm('确认删除这条保存的 SQL？', '删除确认', { type: 'warning' })
    await api.deleteSavedSql(id)
    ElMessage.success('已删除')
    await loadList()
  } catch (error: unknown) {
    if (error) {
      ElMessage.error('删除失败')
    }
  }
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
  gap: 12px;
  margin-bottom: 12px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  flex: 0 0 320px;
  max-width: 320px;
}

.toolbar-actions :deep(.el-input) {
  width: 148px;
}

.toolbar-actions :deep(.el-select) {
  width: 164px;
}

.subtitle {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.code-block {
  overflow: auto;
  border-radius: 12px;
  padding: 16px;
  background: #0f172a;
  color: #dbeafe;
}

@media (max-width: 1180px) {
  .toolbar {
    flex-direction: column;
  }

  .toolbar-actions {
    flex: none;
    width: 100%;
    max-width: none;
    justify-content: flex-start;
  }
}
</style>
