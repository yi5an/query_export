export interface Datasource {
  id: number
  name: string
  type: string
  host: string
  port: number
  database?: string | null
  username?: string | null
  is_active?: boolean
  extra_config?: Record<string, unknown> | null
}

export interface DatasourcePayload {
  name: string
  type: string
  host: string
  port: number
  database?: string | null
  username?: string | null
  password?: string | null
  extra_config?: Record<string, unknown>
}

export interface QueryResult {
  columns: string[]
  rows: Array<Array<string | number | boolean | null>>
  row_count: number
  execution_time_ms?: number
}

export interface SavedSql {
  id: number
  datasource_id: number
  name: string
  sql_text: string
  comment?: string | null
  tags?: string[]
  run_count: number
  created_at?: string
  updated_at?: string
  last_run_at?: string | null
}

export interface ExportTask {
  id: number
  datasource_id: number
  saved_sql_id?: number | null
  sql_text: string
  export_format: string
  status: string
  file_path?: string | null
  row_count?: number | null
  error_message?: string | null
  created_at?: string
  completed_at?: string | null
  expires_at?: string | null
  remaining_seconds?: number | null
}

export interface AiConfig {
  id?: number
  provider: string
  model_name: string
  base_url?: string
  api_key?: string
  embedding_algorithm?: string
  embedding_model?: string
  embedding_base_url?: string
  embedding_api_key?: string
  is_active?: boolean
  has_api_key?: boolean
  has_embedding_api_key?: boolean
}

export interface AiGenerateResponse {
  sql: string
  matched_sql?: { name: string } | null
}
