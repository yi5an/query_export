<template>
  <div class="chat-wrap">
    <div class="messages">
      <div v-for="(message, index) in messages" :key="index" class="message" :class="message.role">
        <div class="bubble">
          <template v-if="message.role === 'assistant' && message.sql">
            <div class="assistant-title">{{ message.content }}</div>
            <pre>{{ message.sql }}</pre>
            <div v-if="message.matchedSql" class="hint">参考 SQL: {{ message.matchedSql.name }}</div>
            <el-button size="small" type="primary" @click="$emit('applySql', message.sql)">使用此 SQL</el-button>
          </template>
          <template v-else>
            {{ message.content }}
          </template>
        </div>
      </div>
    </div>

    <div class="composer">
      <el-input
        v-model="prompt"
        type="textarea"
        :rows="3"
        placeholder="例如：查询最近 7 天各渠道订单总额"
        @keydown.ctrl.enter.prevent="generate"
      />
      <el-button type="primary" :loading="loading" @click="generate">生成 SQL</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'

interface MessageItem {
  role: 'user' | 'assistant'
  content: string
  sql?: string
  matchedSql?: { name: string } | null
}

const props = defineProps<{
  datasourceId?: number
}>()

defineEmits<{
  (event: 'applySql', sql: string): void
}>()

const prompt = ref('')
const loading = ref(false)
const messages = ref<MessageItem[]>([])

async function generate() {
  if (!prompt.value.trim()) {
    return
  }
  if (!props.datasourceId) {
    ElMessage.warning('请先选择数据源')
    return
  }

  const description = prompt.value.trim()
  messages.value.push({ role: 'user', content: description })
  prompt.value = ''
  loading.value = true

  try {
    const response = await api.generateSql({
      datasource_id: props.datasourceId,
      description
    })
    messages.value.push({
      role: 'assistant',
      content: '已生成 SQL',
      sql: response.sql,
      matchedSql: response.matched_sql
    })
  } catch (error: unknown) {
    messages.value.push({
      role: 'assistant',
      content: '生成 SQL 失败，请确认 AI 配置已启用。'
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.chat-wrap {
  display: grid;
  grid-template-rows: 1fr auto;
  gap: 16px;
  min-height: 420px;
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
}

.message {
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 88%;
  border-radius: 16px;
  padding: 12px 14px;
  background: #edf4fb;
}

.message.user .bubble {
  background: #d9ecff;
}

.assistant-title {
  margin-bottom: 8px;
  font-weight: 600;
}

pre {
  overflow: auto;
  border-radius: 12px;
  padding: 12px;
  background: #122033;
  color: #dbeafe;
}

.hint {
  margin: 8px 0 12px;
  color: #64748b;
  font-size: 12px;
}

.composer {
  display: grid;
  gap: 12px;
}
</style>
