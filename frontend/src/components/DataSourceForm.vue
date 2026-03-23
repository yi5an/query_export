<template>
  <el-form label-position="top">
    <el-form-item label="名称">
      <el-input v-model="state.name" />
    </el-form-item>
    <el-form-item label="类型">
      <el-select v-model="state.type" :disabled="disabledType">
        <el-option v-for="item in datasourceTypes" :key="item" :label="item" :value="item" />
      </el-select>
    </el-form-item>

    <div class="grid">
      <el-form-item label="主机">
        <el-input v-model="state.host" />
      </el-form-item>
      <el-form-item label="端口">
        <el-input-number v-model="state.port" :min="1" :max="65535" />
      </el-form-item>
      <el-form-item label="数据库 / 索引 / Bucket">
        <el-input v-model="state.database" />
      </el-form-item>
      <el-form-item label="用户名">
        <el-input v-model="state.username" />
      </el-form-item>
    </div>

    <el-form-item label="密码">
      <el-input v-model="state.password" type="password" show-password />
    </el-form-item>

    <template v-if="state.type === 'elasticsearch'">
      <div class="grid">
        <el-form-item label="Index Pattern">
          <el-input v-model="extra.index_pattern" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="extra.api_key" />
        </el-form-item>
      </div>
    </template>

    <template v-else-if="state.type === 'redis' || state.type === 'redis-cluster'">
      <el-form-item label="Cluster Nodes">
        <el-input v-model="extra.cluster_nodes" placeholder="host1:6379,host2:6379" />
      </el-form-item>
    </template>

    <template v-else-if="state.type === 'minio'">
      <div class="grid">
        <el-form-item label="Region">
          <el-input v-model="extra.region" />
        </el-form-item>
        <el-form-item label="Access Style">
          <el-select v-model="extra.access_style">
            <el-option label="path" value="path" />
            <el-option label="virtual" value="virtual" />
          </el-select>
        </el-form-item>
      </div>
    </template>

    <el-form-item>
      <el-checkbox v-model="extra.ssl">启用 SSL</el-checkbox>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import type { Datasource, DatasourcePayload } from '@/types'

const props = withDefaults(
  defineProps<{
    modelValue: DatasourcePayload
    datasourceTypes?: string[]
    disabledType?: boolean
  }>(),
  {
    datasourceTypes: () => ['postgres', 'clickhouse', 'doris', 'redis', 'redis-cluster', 'elasticsearch', 'minio'],
    disabledType: false
  }
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: DatasourcePayload): void
}>()

const state = reactive<DatasourcePayload>({
  name: '',
  type: 'postgres',
  host: '',
  port: 5432,
  database: '',
  username: '',
  password: '',
  extra_config: {}
})

const extra = reactive<Record<string, string | boolean | undefined>>({
  ssl: false,
  index_pattern: '',
  api_key: '',
  cluster_nodes: '',
  region: '',
  access_style: 'path'
})

watch(
  () => props.modelValue,
  (value) => {
    state.name = value.name || ''
    state.type = value.type || 'postgres'
    state.host = value.host || ''
    state.port = value.port || defaultPort(value.type || 'postgres')
    state.database = value.database || ''
    state.username = value.username || ''
    state.password = value.password || ''
    const config = value.extra_config || {}
    extra.ssl = Boolean(config.ssl)
    extra.index_pattern = String(config.index_pattern || '')
    extra.api_key = String(config.api_key || '')
    extra.cluster_nodes = Array.isArray(config.cluster_nodes)
      ? config.cluster_nodes.join(',')
      : String(config.cluster_nodes || '')
    extra.region = String(config.region || '')
    extra.access_style = String(config.access_style || 'path')
  },
  { immediate: true, deep: true }
)

watch(
  () => state.type,
  (nextType, previousType) => {
    const previousDefaultPort = defaultPort(previousType || 'postgres')
    if (!state.port || state.port === previousDefaultPort || state.port === 0) {
      state.port = defaultPort(nextType)
    }
  }
)

watch(
  [state, extra],
  () => {
    emit('update:modelValue', {
      ...state,
      extra_config: normalizeExtra(state.type)
    })
  },
  { deep: true }
)

function defaultPort(type: string) {
  const ports: Record<string, number> = {
    postgres: 5432,
    clickhouse: 8123,
    doris: 9030,
    redis: 6379,
    'redis-cluster': 6379,
    elasticsearch: 9200,
    minio: 9000
  }
  return ports[type] || 0
}

function normalizeExtra(type: string) {
  const base: Record<string, unknown> = {
    ssl: extra.ssl
  }

  if (type === 'elasticsearch') {
    base.index_pattern = extra.index_pattern || undefined
    base.api_key = extra.api_key || undefined
  }

  if (type === 'redis' || type === 'redis-cluster') {
    base.cluster_nodes = extra.cluster_nodes
      ? String(extra.cluster_nodes)
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean)
      : undefined
  }

  if (type === 'minio') {
    base.region = extra.region || undefined
    base.access_style = extra.access_style || undefined
  }

  return base
}
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 768px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
