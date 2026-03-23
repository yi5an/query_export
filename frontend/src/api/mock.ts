import type {
  AiConfig,
  AiGenerateResponse,
  Datasource,
  DatasourcePayload,
  ExportTask,
  QueryResult,
  SavedSql
} from '@/types'

const STORAGE_KEYS = {
  datasources: 'queryexport.mock.datasources',
  savedSqls: 'queryexport.mock.saved-sqls',
  exports: 'queryexport.mock.exports',
  aiConfig: 'queryexport.mock.ai-config'
}

const datasourceTypes = ['postgres', 'clickhouse', 'doris', 'redis', 'redis-cluster', 'elasticsearch', 'minio']

function readJson<T>(key: string, fallback: T): T {
  const raw = localStorage.getItem(key)
  if (!raw) return fallback
  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function writeJson<T>(key: string, value: T) {
  localStorage.setItem(key, JSON.stringify(value))
}

function nextId(items: Array<{ id: number }>) {
  return items.length ? Math.max(...items.map((item) => item.id)) + 1 : 1
}

function seedDatasources(): Datasource[] {
  const current = readJson<Datasource[]>(STORAGE_KEYS.datasources, [])
  if (current.length) return current

  const seeded: Datasource[] = [
    {
      id: 1,
      name: 'test-pg',
      type: 'postgres',
      host: 'postgres',
      port: 5432,
      database: 'queryexport',
      username: 'queryexport',
      is_active: true,
      extra_config: { ssl: false }
    }
  ]
  writeJson(STORAGE_KEYS.datasources, seeded)
  return seeded
}

function fakeRows(sql: string, limit = 10): QueryResult {
  const normalized = sql.trim().toLowerCase()
  const rowCount = Math.max(1, Math.min(limit, 8))

  if (normalized.includes('order')) {
    return {
      columns: ['date', 'channel', 'order_total', 'order_count'],
      rows: [
        ['2026-03-13', 'web', 12880, 76],
        ['2026-03-14', 'app', 14320, 82],
        ['2026-03-15', 'miniapp', 9850, 61],
        ['2026-03-16', 'web', 15790, 91],
        ['2026-03-17', 'app', 16430, 94]
      ].slice(0, rowCount),
      row_count: Math.min(5, rowCount),
      execution_time_ms: 8.4
    }
  }

  if (normalized.includes('user')) {
    return {
      columns: ['id', 'name', 'email', 'created_at'],
      rows: [
        [1, '张三', 'zhangsan@example.com', '2026-03-19T06:02:11'],
        [2, '李四', 'lisi@example.com', '2026-03-19T06:02:18'],
        [3, '王五', 'wangwu@example.com', '2026-03-19T06:02:29']
      ].slice(0, rowCount),
      row_count: Math.min(3, rowCount),
      execution_time_ms: 1.7
    }
  }

  return {
    columns: ['result'],
    rows: Array.from({ length: rowCount }, (_, index) => [`mock-row-${index + 1}`]),
    row_count: rowCount,
    execution_time_ms: 2.4
  }
}

function createBlobUrl(content: string, mime = 'text/plain;charset=utf-8') {
  const blob = new Blob([content], { type: mime })
  return URL.createObjectURL(blob)
}

export const mockApi = {
  listDatasources() {
    return Promise.resolve(seedDatasources())
  },
  listDatasourceTypes() {
    return Promise.resolve(datasourceTypes)
  },
  createDatasource(payload: DatasourcePayload) {
    const list = seedDatasources()
    const created: Datasource = {
      id: nextId(list),
      name: payload.name,
      type: payload.type,
      host: payload.host,
      port: payload.port,
      database: payload.database || null,
      username: payload.username || null,
      is_active: true,
      extra_config: payload.extra_config || {}
    }
    const next = [created, ...list]
    writeJson(STORAGE_KEYS.datasources, next)
    return Promise.resolve(created)
  },
  updateDatasource(id: number, payload: Partial<DatasourcePayload>) {
    const list = seedDatasources()
    const next = list.map((item) => (item.id === id ? { ...item, ...payload } : item))
    const updated = next.find((item) => item.id === id)!
    writeJson(STORAGE_KEYS.datasources, next)
    return Promise.resolve(updated)
  },
  deleteDatasource(id: number) {
    const next = seedDatasources().filter((item) => item.id !== id)
    writeJson(STORAGE_KEYS.datasources, next)
    return Promise.resolve()
  },
  testDatasource() {
    return Promise.resolve({ status: 'success', message: 'Mock connection successful' })
  },
  executeQuery(payload: { sql: string; limit?: number }) {
    return Promise.resolve(fakeRows(payload.sql, payload.limit))
  },
  formatQuery(payload: { sql: string }) {
    const formatted = payload.sql
      .replace(/\s+/g, ' ')
      .replace(/select/gi, 'SELECT')
      .replace(/from/gi, 'FROM')
      .replace(/where/gi, 'WHERE')
      .replace(/limit/gi, 'LIMIT')
      .trim()
    return Promise.resolve({ formatted_sql: formatted })
  },
  validateQuery(payload: { sql: string }) {
    const valid = /\b(select|insert|update|delete|show|describe|with)\b/i.test(payload.sql)
    return Promise.resolve({
      is_valid: valid,
      error: valid ? null : 'No valid SQL keyword found'
    })
  },
  listSavedSqls(params?: { search?: string; datasource_id?: number }) {
    let list = readJson<SavedSql[]>(STORAGE_KEYS.savedSqls, [])
    if (params?.datasource_id) {
      list = list.filter((item) => item.datasource_id === params.datasource_id)
    }
    if (params?.search) {
      const keyword = params.search.toLowerCase()
      list = list.filter((item) =>
        [item.name, item.comment, item.sql_text].some((field) => String(field || '').toLowerCase().includes(keyword))
      )
    }
    return Promise.resolve(list)
  },
  createSavedSql(payload: { datasource_id: number; name: string; sql_text: string; comment?: string; tags?: string[] }) {
    const list = readJson<SavedSql[]>(STORAGE_KEYS.savedSqls, [])
    const now = new Date().toISOString()
    const created: SavedSql = {
      id: nextId(list),
      datasource_id: payload.datasource_id,
      name: payload.name,
      sql_text: payload.sql_text,
      comment: payload.comment || '',
      tags: payload.tags || [],
      run_count: 0,
      created_at: now,
      updated_at: now,
      last_run_at: null
    }
    writeJson(STORAGE_KEYS.savedSqls, [created, ...list])
    return Promise.resolve(created)
  },
  deleteSavedSql(id: number) {
    const next = readJson<SavedSql[]>(STORAGE_KEYS.savedSqls, []).filter((item) => item.id !== id)
    writeJson(STORAGE_KEYS.savedSqls, next)
    return Promise.resolve()
  },
  runSavedSql(id: number, limit = 10) {
    const list = readJson<SavedSql[]>(STORAGE_KEYS.savedSqls, [])
    const target = list.find((item) => item.id === id)
    if (!target) {
      return Promise.reject(new Error('Saved SQL not found'))
    }
    const next = list.map((item) =>
      item.id === id
        ? { ...item, run_count: item.run_count + 1, last_run_at: new Date().toISOString() }
        : item
    )
    writeJson(STORAGE_KEYS.savedSqls, next)
    return Promise.resolve(fakeRows(target.sql_text, limit))
  },
  createExport(payload: { datasource_id: number; sql: string; format: string }) {
    const list = readJson<ExportTask[]>(STORAGE_KEYS.exports, [])
    const id = nextId(list)
    const rows = fakeRows(payload.sql, 10)
    const extension = payload.format === 'excel' ? 'csv' : payload.format
    const fileContent =
      payload.format === 'json'
        ? JSON.stringify(rows.rows, null, 2)
        : [rows.columns.join(','), ...rows.rows.map((row) => row.join(','))].join('\n')
    const created: ExportTask = {
      id,
      datasource_id: payload.datasource_id,
      sql_text: payload.sql,
      export_format: payload.format,
      status: 'completed',
      row_count: rows.row_count,
      file_path: createBlobUrl(fileContent, payload.format === 'json' ? 'application/json' : 'text/csv'),
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString()
    }
    writeJson(STORAGE_KEYS.exports, [created, ...list])
    return Promise.resolve({ task_id: id, status: created.status, message: 'Mock export task created' })
  },
  listExports() {
    return Promise.resolve(readJson<ExportTask[]>(STORAGE_KEYS.exports, []))
  },
  exportDownloadUrl(taskId: number) {
    const item = readJson<ExportTask[]>(STORAGE_KEYS.exports, []).find((task) => task.id === taskId)
    return item?.file_path || '#'
  },
  deleteExport(taskId: number) {
    const next = readJson<ExportTask[]>(STORAGE_KEYS.exports, []).filter((item) => item.id !== taskId)
    writeJson(STORAGE_KEYS.exports, next)
    return Promise.resolve()
  },
  generateSql(payload: { description: string }): Promise<AiGenerateResponse> {
    const sql =
      payload.description.includes('最近7天') || payload.description.includes('7天')
        ? 'SELECT order_date, channel, SUM(amount) AS order_total FROM orders WHERE order_date >= CURRENT_DATE - INTERVAL \'7 days\' GROUP BY 1, 2 ORDER BY 1 DESC;'
        : `SELECT * FROM users WHERE name ILIKE '%${payload.description.trim()}%' LIMIT 10;`
    return Promise.resolve({
      sql,
      matched_sql: { name: 'Mock AI Recommendation' }
    })
  },
  getAiConfig() {
    const config = readJson<AiConfig | null>(STORAGE_KEYS.aiConfig, null)
    if (!config) {
      return Promise.reject(new Error('No active AI configuration'))
    }
    return Promise.resolve(config)
  },
  updateAiConfig(payload: AiConfig) {
    writeJson(STORAGE_KEYS.aiConfig, payload)
    return Promise.resolve(payload)
  }
}
