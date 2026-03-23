<template>
  <div class="page-card page">
    <div class="toolbar">
      <div>
        <h2 class="section-title">数据源管理</h2>
        <p class="subtitle">支持新增、编辑、测试连接和软删除。</p>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="openCreate">添加数据源</el-button>
        <el-button @click="loadData">刷新</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="datasources" stripe>
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="type" label="类型" width="140" />
      <el-table-column label="连接信息" min-width="240">
        <template #default="{ row }">{{ row.host }}:{{ row.port }} / {{ row.database || '-' }}</template>
      </el-table-column>
      <el-table-column prop="username" label="用户名" width="160" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="success" @click="testConnection(row.id)">测试</el-button>
          <el-button link type="danger" @click="removeDatasource(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑数据源' : '新增数据源'" width="760px">
      <DataSourceForm v-model="form" :datasource-types="datasourceTypes" :disabled-type="Boolean(editingId)" />
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">
          {{ editingId ? '保存修改' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import DataSourceForm from '@/components/DataSourceForm.vue'
import type { Datasource, DatasourcePayload } from '@/types'

const loading = ref(false)
const submitting = ref(false)
const dialogOpen = ref(false)
const editingId = ref<number>()
const datasources = ref<Datasource[]>([])
const datasourceTypes = ref<string[]>(['postgres'])
const form = ref<DatasourcePayload>(defaultForm())

onMounted(async () => {
  await Promise.all([loadData(), loadTypes()])
})

function defaultForm(): DatasourcePayload {
  return {
    name: '',
    type: 'postgres',
    host: '',
    port: 5432,
    database: '',
    username: '',
    password: '',
    extra_config: {}
  }
}

async function loadTypes() {
  try {
    datasourceTypes.value = await api.listDatasourceTypes()
  } catch (error: unknown) {
    datasourceTypes.value = ['postgres', 'clickhouse', 'doris', 'redis', 'redis-cluster', 'elasticsearch', 'minio']
  }
}

async function loadData() {
  loading.value = true
  try {
    datasources.value = await api.listDatasources()
  } catch (error: unknown) {
    ElMessage.error('加载数据源失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = undefined
  form.value = defaultForm()
  dialogOpen.value = true
}

function openEdit(item: Datasource) {
  editingId.value = item.id
  form.value = {
    name: item.name,
    type: item.type,
    host: item.host,
    port: item.port,
    database: item.database || '',
    username: item.username || '',
    password: '',
    extra_config: item.extra_config || {}
  }
  dialogOpen.value = true
}

async function submitForm() {
  submitting.value = true
  try {
    if (editingId.value) {
      await api.updateDatasource(editingId.value, form.value)
      ElMessage.success('数据源已更新')
    } else {
      await api.createDatasource(form.value)
      ElMessage.success('数据源已创建')
    }
    dialogOpen.value = false
    await loadData()
  } catch (error: unknown) {
    ElMessage.error('保存数据源失败')
  } finally {
    submitting.value = false
  }
}

async function testConnection(id: number) {
  try {
    const result = await api.testDatasource(id)
    ElMessage[result.status === 'success' ? 'success' : 'warning'](result.message)
  } catch (error: unknown) {
    ElMessage.error('测试连接失败')
  }
}

async function removeDatasource(id: number) {
  try {
    await ElMessageBox.confirm('确认删除该数据源？', '删除确认', { type: 'warning' })
    await api.deleteDatasource(id)
    ElMessage.success('数据源已删除')
    await loadData()
  } catch (error: unknown) {
    if (error) {
      ElMessage.error('删除数据源失败')
    }
  }
}
</script>

<style scoped>
.page {
  padding: 24px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
}

.subtitle {
  margin: 0;
  color: #64748b;
}
</style>
