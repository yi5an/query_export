<template>
  <div class="query-page">
    <section class="page-card hero">
      <div class="hero-top">
        <div>
          <h2 class="section-title">{{ editorTitle }}</h2>
          <p class="subtitle">{{ editorSubtitle }}</p>
        </div>
        <div class="top-actions">
          <el-select v-model="selectedDatasourceId" filterable placeholder="选择数据源" style="width: 260px">
            <el-option v-for="item in datasources" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-button @click="refreshSidePanels">刷新面板</el-button>
          <el-button @click="showAiDrawer = true">AI 生成</el-button>
        </div>
      </div>

      <div class="toolbar">
        <el-button type="primary" :loading="executing" @click="executeQuery">执行</el-button>
        <el-button @click="formatQuery">格式化</el-button>
        <el-button @click="validateQuery">校验</el-button>
        <el-button @click="showSaveDialog = true">保存 SQL</el-button>
        <el-button @click="showExportDialog = true">导出</el-button>
        <el-button @click="clearEditor">清空</el-button>
      </div>

      <div class="samples" v-if="currentExamples.length">
        <div class="samples-header">
          <span class="samples-label">查询样例</span>
          <span class="samples-hint">切换数据源后，可直接插入对应类型的示例。</span>
        </div>
        <div class="sample-list">
          <el-button
            v-for="example in currentExamples"
            :key="`${currentDatasource?.type}-${example.label}`"
            size="small"
            plain
            @click="applyExample(example.query)"
          >
            {{ example.label }}
          </el-button>
        </div>
      </div>

      <SqlEditor v-model="sql" height="210px" />
    </section>

    <ResultTable v-if="queryResult" :result="queryResult" />

    <section class="bottom-grid">
      <SavedSqlPanel
        :datasource-id="selectedDatasourceId"
        :refresh-key="panelRefreshKey"
        title="保存的 SQL"
        subtitle="选中即回填到编辑器。"
        @use-sql="handleUseSavedSql"
      />
      <ExportTaskPanel
        :refresh-key="panelRefreshKey"
        title="导出任务"
        subtitle="创建导出后可在这里查看状态和下载。"
      />
    </section>

    <SaveSqlDialog
      v-model="showSaveDialog"
      :datasource-id="selectedDatasourceId"
      :sql-text="sql"
      @saved="refreshSidePanels"
    />
    <ExportModal
      v-model="showExportDialog"
      :datasource-id="selectedDatasourceId"
      :sql-text="sql"
      @created="refreshSidePanels"
    />

    <el-drawer v-model="showAiDrawer" title="AI 生成 SQL" size="42%">
      <AiChat :datasource-id="selectedDatasourceId" @apply-sql="applyAiSql" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import AiChat from '@/components/AiChat.vue'
import ExportTaskPanel from '@/components/ExportTaskPanel.vue'
import ExportModal from '@/components/ExportModal.vue'
import ResultTable from '@/components/ResultTable.vue'
import SavedSqlPanel from '@/components/SavedSqlPanel.vue'
import SaveSqlDialog from '@/components/SaveSqlDialog.vue'
import SqlEditor from '@/components/SqlEditor.vue'
import type { Datasource, QueryResult } from '@/types'

interface QueryExample {
  label: string
  query: string
}

const QUERY_EXAMPLES: Record<string, QueryExample[]> = {
  postgres: [
    { label: '查询前 10 行', query: 'SELECT * FROM users ORDER BY id DESC LIMIT 10;' },
    { label: '按日期过滤', query: "SELECT * FROM orders WHERE created_at >= CURRENT_DATE - INTERVAL '7 day' ORDER BY created_at DESC LIMIT 20;" }
  ],
  postgresql: [
    { label: '查询前 10 行', query: 'SELECT * FROM users ORDER BY id DESC LIMIT 10;' }
  ],
  clickhouse: [
    { label: '查询前 10 行', query: 'SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;' },
    { label: '按天聚合', query: "SELECT toDate(timestamp) AS day, count() AS total FROM events GROUP BY day ORDER BY day DESC LIMIT 7;" }
  ],
  doris: [
    { label: '查询前 10 行', query: 'SELECT * FROM fact_orders ORDER BY create_time DESC LIMIT 10;' },
    { label: '汇总统计', query: 'SELECT shop_id, COUNT(*) AS total_orders, SUM(pay_amount) AS total_amount FROM fact_orders GROUP BY shop_id ORDER BY total_amount DESC LIMIT 20;' }
  ],
  redis: [
    { label: '查看单个 key', query: 'GET session:user:1001' },
    { label: '查看 Hash', query: 'HGETALL user:1001' },
    { label: '匹配键名', query: 'KEYS user:*' }
  ],
  'redis-cluster': [
    { label: '查看单个 key', query: 'GET session:user:1001' },
    { label: '查看 Hash', query: 'HGETALL user:1001' },
    { label: '匹配键名', query: 'KEYS user:*' }
  ],
  elasticsearch: [
    { label: '全文搜索', query: '{"query":{"match":{"title":"新闻"}},"size":10}' },
    { label: '时间范围过滤', query: '{"query":{"range":{"published_at":{"gte":"2025-01-01","lte":"2025-01-02"}}},"sort":[{"published_at":"desc"}],"size":20}' }
  ],
  minio: [
    { label: '列出 bucket', query: 'my-bucket/' },
    { label: '列出目录前缀', query: 'my-bucket/reports/2025/' }
  ]
}

const datasources = ref<Datasource[]>([])
const selectedDatasourceId = ref<number>()
const sql = ref('SELECT * FROM users LIMIT 10;')
const queryResult = ref<QueryResult>()
const executing = ref(false)
const showSaveDialog = ref(false)
const showExportDialog = ref(false)
const showAiDrawer = ref(false)
const panelRefreshKey = ref(0)
const STORAGE_KEY = 'queryexport.query-draft'
const currentDatasource = computed(() => datasources.value.find((item) => item.id === selectedDatasourceId.value))
const currentDatasourceType = computed(() => currentDatasource.value?.type || 'postgres')
const currentExamples = computed(() => QUERY_EXAMPLES[currentDatasourceType.value] || QUERY_EXAMPLES.postgres)
const editorTitle = computed(() => {
  if (currentDatasourceType.value === 'redis' || currentDatasourceType.value === 'redis-cluster') {
    return '命令查询'
  }
  if (currentDatasourceType.value === 'elasticsearch') {
    return 'Query DSL 查询'
  }
  if (currentDatasourceType.value === 'minio') {
    return '对象查询'
  }
  return 'SQL 查询'
})
const editorSubtitle = computed(() => {
  if (currentDatasourceType.value === 'redis' || currentDatasourceType.value === 'redis-cluster') {
    return '选择 Redis 数据源后，直接输入命令并执行试运行。'
  }
  if (currentDatasourceType.value === 'elasticsearch') {
    return '选择 Elasticsearch 数据源后，可输入 Query DSL JSON 或简单查询语句。'
  }
  if (currentDatasourceType.value === 'minio') {
    return '选择 MinIO 数据源后，可输入 bucket/prefix 路径列出对象。'
  }
  return '选择数据源，执行试运行，保存 SQL，并创建导出任务。'
})

onMounted(async () => {
  restoreDraft()
  await loadDatasources()
})

watch(
  [selectedDatasourceId, sql],
  () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        datasourceId: selectedDatasourceId.value,
        sql: sql.value
      })
    )
  },
  { deep: true }
)

watch(
  () => currentDatasourceType.value,
  (nextType, previousType) => {
    const nextDefault = QUERY_EXAMPLES[nextType]?.[0]?.query
    if (!nextDefault) return

    const previousExamples = previousType ? QUERY_EXAMPLES[previousType] || [] : []
    const knownExampleQueries = new Set(
      Object.values(QUERY_EXAMPLES)
        .flat()
        .map((item) => item.query)
    )
    const shouldReplace =
      !sql.value.trim() ||
      sql.value === 'SELECT * FROM users LIMIT 10;' ||
      previousExamples.some((item) => item.query === sql.value) ||
      knownExampleQueries.has(sql.value)

    if (shouldReplace) {
      sql.value = nextDefault
      queryResult.value = undefined
    }
  },
  { immediate: true }
)

async function loadDatasources() {
  try {
    datasources.value = await api.listDatasources()
    if (!selectedDatasourceId.value && datasources.value.length > 0) {
      selectedDatasourceId.value = datasources.value[0].id
    }
  } catch (error: unknown) {
    ElMessage.error('加载数据源失败')
  }
}

async function executeQuery() {
  if (!selectedDatasourceId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }

  executing.value = true
  try {
    queryResult.value = await api.executeQuery({
      datasource_id: selectedDatasourceId.value,
      sql: sql.value,
      limit: 10
    })
    ElMessage.success('查询成功')
  } catch (error: unknown) {
    ElMessage.error('查询失败')
  } finally {
    executing.value = false
  }
}

async function formatQuery() {
  try {
    const result = await api.formatQuery({ sql: sql.value })
    sql.value = result.formatted_sql
  } catch (error: unknown) {
    ElMessage.error('格式化失败')
  }
}

async function validateQuery() {
  if (!selectedDatasourceId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }

  try {
    const result = await api.validateQuery({
      datasource_id: selectedDatasourceId.value,
      sql: sql.value
    })
    if (result.is_valid) {
      ElMessage.success('SQL 校验通过')
    } else {
      ElMessage.warning(result.error || 'SQL 校验未通过')
    }
  } catch (error: unknown) {
    ElMessage.error('SQL 校验失败')
  }
}

function clearEditor() {
  sql.value = ''
  queryResult.value = undefined
}

function applyExample(example: string) {
  sql.value = example
  queryResult.value = undefined
}

function applyAiSql(nextSql: string) {
  sql.value = nextSql
  showAiDrawer.value = false
}

function handleUseSavedSql(nextSql: string, datasourceId?: number) {
  sql.value = nextSql
  if (datasourceId) {
    selectedDatasourceId.value = datasourceId
  }
  ElMessage.success('已将保存的 SQL 回填到编辑器')
}

function refreshSidePanels() {
  panelRefreshKey.value += 1
  ElMessage.success('列表已刷新')
}

function restoreDraft() {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return
  try {
    const draft = JSON.parse(raw) as { datasourceId?: number; sql?: string }
    if (typeof draft.datasourceId === 'number') {
      selectedDatasourceId.value = draft.datasourceId
    }
    if (typeof draft.sql === 'string' && draft.sql.trim()) {
      sql.value = draft.sql
    }
  } catch {
    localStorage.removeItem(STORAGE_KEY)
  }
}
</script>

<style scoped>
.query-page {
  display: grid;
  gap: 16px;
  max-width: 1360px;
  margin: 0 auto;
  min-width: 0;
}

.query-page > * {
  min-width: 0;
}

.hero {
  padding: 18px 20px 16px;
}

.hero-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.subtitle {
  margin: 0;
  color: #64748b;
}

.top-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.samples {
  margin-bottom: 12px;
}

.samples-header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  align-items: center;
  margin-bottom: 8px;
}

.samples-label {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.samples-hint {
  font-size: 12px;
  color: #64748b;
}

.sample-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.bottom-grid {
  display: grid;
  grid-template-columns: minmax(340px, 0.88fr) minmax(520px, 1.12fr);
  gap: 16px;
  align-items: start;
}

@media (max-width: 1200px) {
  .bottom-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .hero-top {
    flex-direction: column;
  }

  .top-actions {
    flex-wrap: wrap;
  }
}
</style>
