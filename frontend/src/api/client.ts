import axios from 'axios'
import type {
  AiConfig,
  AiGenerateResponse,
  Datasource,
  DatasourcePayload,
  ExportTask,
  QueryResult,
  SavedSql
} from '@/types'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000
})

http.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
)

export const api = {
  async listDatasources() {
    return (await http.get<Datasource[]>('/datasources/')).data
  },
  async listDatasourceTypes() {
    return (await http.get<{ types: string[] }>('/datasources/types')).data.types
  },
  async createDatasource(payload: DatasourcePayload) {
    return (await http.post<Datasource>('/datasources/', payload)).data
  },
  async updateDatasource(id: number, payload: Partial<DatasourcePayload>) {
    return (await http.put<Datasource>(`/datasources/${id}`, payload)).data
  },
  async deleteDatasource(id: number) {
    await http.delete(`/datasources/${id}`)
  },
  async testDatasource(id: number) {
    return (await http.post<{ status: string; message: string }>(`/datasources/${id}/test`)).data
  },
  async executeQuery(payload: { datasource_id: number; sql: string; limit?: number }) {
    return (await http.post<QueryResult>('/query/execute', payload)).data
  },
  async formatQuery(payload: { sql: string; dialect?: string }) {
    return (await http.post<{ formatted_sql: string }>('/query/format', payload)).data
  },
  async validateQuery(payload: { datasource_id: number; sql: string }) {
    return (await http.post<{ is_valid: boolean; error?: string | null }>('/query/validate', payload)).data
  },
  async listSavedSqls(params?: { search?: string; datasource_id?: number }) {
    return (await http.get<SavedSql[]>('/saved-sqls/', { params })).data
  },
  async createSavedSql(payload: {
    datasource_id: number
    name: string
    sql_text: string
    comment?: string
    tags?: string[]
  }) {
    return (await http.post<SavedSql>('/saved-sqls/', payload)).data
  },
  async deleteSavedSql(id: number) {
    await http.delete(`/saved-sqls/${id}`)
  },
  async runSavedSql(id: number, limit = 10) {
    return (
      await http.post<QueryResult>(`/saved-sqls/${id}/run`, null, {
        params: { limit }
      })
    ).data
  },
  async createExport(payload: { datasource_id: number; sql: string; format: string }) {
    return (
      await http.post('/exports/', {
        datasource_id: payload.datasource_id,
        sql_text: payload.sql,
        export_format: payload.format
      })
    ).data
  },
  async listExports() {
    return (await http.get<ExportTask[]>('/exports/')).data
  },
  exportDownloadUrl(taskId: number) {
    return `${http.defaults.baseURL}/exports/${taskId}/download`
  },
  async deleteExport(taskId: number) {
    await http.delete(`/exports/${taskId}`)
  },
  async generateSql(payload: { datasource_id: number; description: string }) {
    return (await http.post<AiGenerateResponse>('/ai/generate', payload)).data
  },
  async getAiConfig() {
    return (await http.get<AiConfig>('/ai/config')).data
  },
  async updateAiConfig(payload: AiConfig) {
    return (await http.put<AiConfig>('/ai/config', payload)).data
  }
}
