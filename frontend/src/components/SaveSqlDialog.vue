<template>
  <el-dialog v-model="visible" title="保存 SQL" width="520px">
    <el-form label-position="top">
      <el-form-item label="名称">
        <el-input v-model="form.name" placeholder="例如：最近 7 天订单汇总" />
      </el-form-item>
      <el-form-item label="注释">
        <el-input
          v-model="form.comment"
          type="textarea"
          :rows="3"
          placeholder="描述用途，方便后续检索和 AI 匹配"
        />
      </el-form-item>
      <el-form-item label="标签">
        <el-select v-model="form.tags" multiple filterable allow-create default-first-option>
          <el-option v-for="tag in commonTags" :key="tag" :label="tag" :value="tag" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
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
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'saved'): void
}>()

const visible = ref(false)
const saving = ref(false)
const commonTags = ['报表', '数据导出', '统计分析', '例行任务']
const form = reactive({
  name: '',
  comment: '',
  tags: [] as string[]
})

watch(
  () => props.modelValue,
  (value) => {
    visible.value = value
    if (value) {
      form.name = ''
      form.comment = ''
      form.tags = []
    }
  },
  { immediate: true }
)

watch(visible, (value) => emit('update:modelValue', value))

async function handleSave() {
  if (!props.datasourceId) {
    ElMessage.warning('请先选择数据源')
    return
  }
  if (!props.sqlText.trim()) {
    ElMessage.warning('SQL 不能为空')
    return
  }
  if (!form.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }

  saving.value = true
  try {
    await api.createSavedSql({
      datasource_id: props.datasourceId,
      name: form.name.trim(),
      sql_text: props.sqlText,
      comment: form.comment.trim(),
      tags: form.tags
    })
    ElMessage.success('SQL 已保存')
    visible.value = false
    emit('saved')
  } catch (error: unknown) {
    const message = axios.isAxiosError(error) ? error.response?.data?.detail : ''
    ElMessage.error(message || '保存 SQL 失败')
  } finally {
    saving.value = false
  }
}
</script>
