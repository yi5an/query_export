<template>
  <el-dialog v-model="visible" title="导出数据" width="480px">
    <el-form label-position="top">
      <el-form-item label="导出格式">
        <el-select v-model="form.format">
          <el-option v-for="item in formats" :key="item" :label="item.toUpperCase()" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="执行模式">
        <el-radio-group v-model="form.mode">
          <el-radio-button value="async">异步任务</el-radio-button>
        </el-radio-group>
        <div class="tip">当前真实后端统一按任务模式创建导出，完成后请到下方任务列表下载。</div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">创建任务</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import axios from 'axios'
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'

const props = defineProps<{
  modelValue: boolean
  datasourceId?: number
  sqlText: string
  formats?: string[]
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'created'): void
}>()

const visible = ref(false)
const submitting = ref(false)
const formats = props.formats?.length ? props.formats : ['csv', 'excel', 'sql']
const form = reactive({
  format: formats[0],
  mode: 'async'
})

watch(
  () => props.modelValue,
  (value) => {
    visible.value = value
  },
  { immediate: true }
)

watch(visible, (value) => emit('update:modelValue', value))

async function submit() {
  if (!props.datasourceId) {
    ElMessage.warning('请先选择数据源')
    return
  }
  if (!props.sqlText.trim()) {
    ElMessage.warning('请先输入 SQL')
    return
  }

  submitting.value = true
  try {
    await api.createExport({
      datasource_id: props.datasourceId,
      sql: props.sqlText,
      format: form.format
    })
    ElMessage.success('导出任务已创建')
    visible.value = false
    emit('created')
  } catch (error: unknown) {
    const message = axios.isAxiosError(error) ? error.response?.data?.detail : ''
    ElMessage.error(message || '创建导出任务失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.tip {
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
}
</style>
