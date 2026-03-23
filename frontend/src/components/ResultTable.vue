<template>
  <div class="page-card result-card">
    <div class="header">
      <div>
        <h3 class="section-title">查询结果</h3>
        <div class="meta">
          <span>{{ result.row_count }} 行</span>
          <span v-if="result.execution_time_ms !== undefined">{{ result.execution_time_ms.toFixed(1) }} ms</span>
        </div>
      </div>
    </div>

    <div class="table-shell">
      <VirtualTable v-if="result.rows.length > 200" :columns="result.columns" :rows="result.rows" />
      <el-table
        v-else
        :data="tableRows"
        stripe
        border
        max-height="420"
        :style="{ width: `${tableMinWidth}px` }"
      >
        <el-table-column
          v-for="(column, index) in result.columns"
          :key="column + index"
          :prop="String(index)"
          :label="column"
          min-width="180"
          show-overflow-tooltip
        />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { QueryResult } from '@/types'
import VirtualTable from '@/components/VirtualTable.vue'

const props = defineProps<{
  result: QueryResult
}>()

const tableMinWidth = computed(() => Math.max(props.result.columns.length, 1) * 180)
const tableRows = computed(() =>
  props.result.rows.map((row) =>
    Object.fromEntries(row.map((value, index) => [String(index), value]))
  )
)
</script>

<style scoped>
.result-card {
  padding: 20px;
  min-width: 0;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.meta {
  display: flex;
  gap: 12px;
  color: #64748b;
  font-size: 13px;
}

.table-shell {
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  min-width: 0;
}

:deep(.el-table) {
  display: block;
  max-width: none;
  width: max-content !important;
  min-width: 100%;
}

:deep(.el-table .cell) {
  white-space: nowrap;
}
</style>
