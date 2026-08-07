/**
 * 轻量 fetch 封装
 *
 * 后端统一响应包裹 { code, data, message }，且业务错误一律返回 HTTP 200，
 * 因此这里必须按 body.code !== 0 判断失败，不能只看 resp.ok。
 * code === 401000 时自动清理登录态并弹出登录提示。
 */

export class ApiError extends Error {
  code: number
  constructor(code: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

export const ACCESS_KEY = 'english_access_token'
export const REFRESH_KEY = 'english_refresh_token'

export function getToken(): string {
  return localStorage.getItem(ACCESS_KEY) || ''
}

export function getRefreshToken(): string {
  return localStorage.getItem(REFRESH_KEY) || ''
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  /** 默认 true；登录/注册等公开接口传 false */
  auth?: boolean
  /** 查询参数 */
  query?: Record<string, string | number | undefined>
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true, query } = options

  let url = `/api/v1${path}`
  if (query) {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== '') params.append(k, String(v))
    }
    const qs = params.toString()
    if (qs) url += `?${qs}`
  }

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  const resp = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  let json: { code?: number; data?: T | null; message?: string } | null = null
  try {
    json = await resp.json()
  } catch {
    // 非 JSON 响应
  }

  if (!json || typeof json.code !== 'number') {
    throw new ApiError(-1, '服务器响应异常')
  }

  if (json.code !== 0) {
    if (json.code === 401000) {
      await handleUnauthorized()
    }
    throw new ApiError(json.code, json.message || '请求失败')
  }

  return json.data as T
}

async function handleUnauthorized(): Promise<void> {
  // 动态引入避免循环依赖
  const { useAuthStore } = await import('@/stores/auth')
  useAuthStore().handleUnauthorized()
}
