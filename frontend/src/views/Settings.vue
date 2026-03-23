<template>
  <div class="page-card page">
    <div class="toolbar">
      <div>
        <h2 class="section-title">设置</h2>
        <p class="subtitle">配置 AI Provider，用于 SQL 生成。</p>
      </div>
      <el-tag :type="form.is_active ? 'success' : 'info'">
        {{ form.is_active ? 'AI 已启用' : 'AI 未启用' }}
      </el-tag>
    </div>

    <el-form label-position="top" class="settings-form">
      <el-form-item label="启用 AI">
        <div class="switch-row">
          <el-switch v-model="form.is_active" />
          <span class="switch-text">
            {{ form.is_active ? '已启用，查询页可直接使用 AI 生成 SQL' : '已停用，保存后 AI 生成功能将不可用' }}
          </span>
        </div>
      </el-form-item>

      <div class="grid">
        <el-form-item label="Provider">
          <el-select v-model="form.provider">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Claude" value="claude" />
            <el-option label="Ollama" value="ollama" />
          </el-select>
        </el-form-item>
        <el-form-item label="Model">
          <el-input v-model="form.model_name" placeholder="例如 gpt-4.1" />
        </el-form-item>
      </div>

      <el-form-item label="Base URL">
        <el-input v-model="form.base_url" placeholder="可选，自定义网关或代理地址" />
      </el-form-item>

      <el-form-item label="API Key">
        <el-input v-model="form.api_key" type="password" show-password placeholder="本地部署模型可留空" />
        <div class="key-status">
          {{ hasApiKeyConfigured || form.api_key.trim() ? '当前已配置 API Key' : '当前未配置 API Key，本地部署模型可留空' }}
        </div>
      </el-form-item>

      <el-divider>Embedding</el-divider>

      <div class="grid">
        <el-form-item label="Embedding 算法">
          <el-select v-model="form.embedding_algorithm">
            <el-option label="Local Hash" value="local_hash" />
            <el-option label="OpenAI Compatible" value="openai_compatible" />
          </el-select>
        </el-form-item>
        <el-form-item label="Embedding Model">
          <el-input
            v-model="form.embedding_model"
            :disabled="form.embedding_algorithm === 'local_hash'"
            placeholder="例如 text-embedding-3-small"
          />
        </el-form-item>
      </div>

      <el-form-item label="Embedding Base URL">
        <el-input
          v-model="form.embedding_base_url"
          :disabled="form.embedding_algorithm === 'local_hash'"
          placeholder="例如 http://127.0.0.1:11434/v1"
        />
      </el-form-item>

      <el-form-item label="Embedding API Key">
        <el-input
          v-model="form.embedding_api_key"
          type="password"
          show-password
          :disabled="form.embedding_algorithm === 'local_hash'"
          placeholder="本地部署 embedding 服务可留空"
        />
        <div class="key-status">
          {{
            form.embedding_algorithm === 'local_hash'
              ? 'Local Hash 不需要额外配置 Key'
              : hasEmbeddingApiKeyConfigured || form.embedding_api_key.trim()
                ? '当前已配置 Embedding API Key'
                : '当前未配置 Embedding API Key，本地部署服务可留空'
          }}
        </div>
      </el-form-item>

      <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'

const saving = ref(false)
const hasApiKeyConfigured = ref(false)
const hasEmbeddingApiKeyConfigured = ref(false)
const STORAGE_KEY = 'queryexport.ai-config'
const form = reactive({
  provider: 'openai',
  model_name: '',
  base_url: '',
  api_key: '',
  embedding_algorithm: 'local_hash',
  embedding_model: '',
  embedding_base_url: '',
  embedding_api_key: '',
  is_active: true
})

onMounted(loadConfig)

async function loadConfig() {
  try {
    const config = await api.getAiConfig()
    form.provider = config.provider || 'openai'
    form.model_name = config.model_name || ''
    form.base_url = config.base_url || ''
    form.is_active = config.is_active ?? true
    form.embedding_algorithm = config.embedding_algorithm || 'local_hash'
    form.embedding_model = config.embedding_model || ''
    form.embedding_base_url = config.embedding_base_url || ''
    hasApiKeyConfigured.value = config.has_api_key ?? false
    hasEmbeddingApiKeyConfigured.value = config.has_embedding_api_key ?? false
  } catch (error: unknown) {
    const cached = readCachedConfig()
    if (cached) {
      form.provider = cached.provider || 'openai'
      form.model_name = cached.model_name || ''
      form.base_url = cached.base_url || ''
      form.is_active = cached.is_active ?? false
      form.embedding_algorithm = cached.embedding_algorithm || 'local_hash'
      form.embedding_model = cached.embedding_model || ''
      form.embedding_base_url = cached.embedding_base_url || ''
      hasApiKeyConfigured.value = Boolean(cached.api_key)
      hasEmbeddingApiKeyConfigured.value = Boolean(cached.embedding_api_key)
      ElMessage.info('已加载本地保存的 AI 配置')
      return
    }
    ElMessage.info('当前没有激活的 AI 配置')
  }
}

async function save() {
  saving.value = true
  try {
    const payload = {
      provider: form.provider,
      model_name: form.model_name,
      base_url: form.base_url,
      api_key: form.api_key,
      embedding_algorithm: form.embedding_algorithm,
      embedding_model: form.embedding_model,
      embedding_base_url: form.embedding_base_url,
      embedding_api_key: form.embedding_api_key,
      is_active: form.is_active
    }
    const saved = await api.updateAiConfig(payload)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    hasApiKeyConfigured.value = saved.has_api_key ?? (hasApiKeyConfigured.value || Boolean(form.api_key.trim()))
    hasEmbeddingApiKeyConfigured.value =
      saved.has_embedding_api_key ?? (hasEmbeddingApiKeyConfigured.value || Boolean(form.embedding_api_key.trim()))
    form.api_key = ''
    form.embedding_api_key = ''
    ElMessage.success(form.is_active ? 'AI 配置已保存并启用' : 'AI 配置已保存并停用')
  } catch (error: unknown) {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        provider: form.provider,
        model_name: form.model_name,
        base_url: form.base_url,
        api_key: form.api_key,
        embedding_algorithm: form.embedding_algorithm,
        embedding_model: form.embedding_model,
        embedding_base_url: form.embedding_base_url,
        embedding_api_key: form.embedding_api_key,
        is_active: form.is_active
      })
    )
    const message = axios.isAxiosError(error) ? error.response?.data?.detail : ''
    ElMessage.warning(message || '后端 AI 配置接口不可用，已保存到本地')
  } finally {
    saving.value = false
  }
}

function readCachedConfig() {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as {
      provider?: string
      model_name?: string
      base_url?: string
      api_key?: string
      embedding_algorithm?: string
      embedding_model?: string
      embedding_base_url?: string
      embedding_api_key?: string
      is_active?: boolean
    }
  } catch {
    return null
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

.subtitle {
  margin: 0;
  color: #64748b;
}

.settings-form {
  max-width: 720px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.switch-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch-text {
  color: #64748b;
  font-size: 13px;
}

.key-status {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}
</style>
