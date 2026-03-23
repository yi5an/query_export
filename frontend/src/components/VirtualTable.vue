<template>
  <div class="virtual-shell">
    <div class="virtual-table" :style="{ minWidth: `${tableWidth}px` }">
      <div class="table-header" :style="{ gridTemplateColumns }">
        <div v-for="column in columns" :key="column" class="head-cell">
          <el-tooltip :content="column" placement="top">
            <span class="cell-text">{{ column }}</span>
          </el-tooltip>
        </div>
      </div>
      <RecycleScroller
        class="scroller"
        :items="normalizedRows"
        :item-size="rowHeight"
        :key-field="'__rowId'"
        v-slot="{ item, index }"
      >
        <div class="table-row" :style="{ gridTemplateColumns, height: `${rowHeight}px` }">
          <div v-for="(column, colIndex) in columns" :key="`${index}-${column}`" class="body-cell">
            <el-tooltip :content="formatCell(getCell(item, colIndex))" placement="top-start">
              <span class="cell-text">{{ formatCell(getCell(item, colIndex)) }}</span>
            </el-tooltip>
          </div>
        </div>
      </RecycleScroller>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'

const props = withDefaults(
  defineProps<{
    columns: string[]
    rows: Array<Array<string | number | boolean | null>>
    rowHeight?: number
  }>(),
  {
    rowHeight: 42
  }
)

const gridTemplateColumns = computed(() => `repeat(${Math.max(props.columns.length, 1)}, minmax(160px, 1fr))`)
const tableWidth = computed(() => Math.max(props.columns.length, 1) * 180)
const normalizedRows = computed(() =>
  props.rows.map((row, index) => ({
    __rowId: index,
    values: row
  }))
)

function getCell(item: unknown, colIndex: number) {
  if (!item || typeof item !== 'object' || !('values' in item)) {
    return ''
  }
  const row = (item as { values: Array<string | number | boolean | null> }).values
  return row[colIndex]
}

function formatCell(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined) {
    return ''
  }
  return String(value)
}
</script>

<style scoped>
.virtual-shell {
  overflow-x: auto;
}

.virtual-table {
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
}

.table-header,
.table-row {
  display: grid;
}

.table-header {
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-weight: 700;
}

.head-cell,
.body-cell {
  padding: 10px 12px;
}

.table-row {
  border-bottom: 1px solid #f1f5f9;
}

.table-row:nth-child(even) {
  background: #fcfdff;
}

.scroller {
  height: 420px;
}

.cell-text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
