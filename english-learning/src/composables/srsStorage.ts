/**
 * SRS 存储适配器：登录用户 → 云端 API；游客 → localStorage。
 * 同一接口，逻辑一致。SRS 状态机本身在 srsEngine.ts，本模块只负责读写。
 */
import {
  completeDay as apiCompleteDay,
  getSrsState,
  onboarding as apiOnboarding,
  resetBook as apiResetBook,
  saveSrsState,
  syncGuest as apiSyncGuest,
} from '@/api/english'
import type {
  CompleteResult,
  MemoryRow,
  SrsSessionState,
  SrsSettings,
  SrsState,
} from '@/types'

export interface SrsStorageAdapter {
  loadState(bookId: number): Promise<SrsState>
  saveState(bookId: number, memory: MemoryRow[], session: SrsSessionState | null): Promise<void>
  completeDay(payload: {
    book_id: number
    study_date: string
    review_count: number
    new_count: number
    wrong_count: number
  }): Promise<CompleteResult>
  syncGuest(bookId: number, memory: MemoryRow[], wordbook: number[]): Promise<unknown>
  reset(bookId: number): Promise<void>
}

// ── 游客 localStorage keys ─────────────────────────────────────────

export const GUEST_SETTINGS_KEY = 'english_guest_settings'
export const GUEST_MEMORY_KEY = (bookId: number) => `english_guest_memory_${bookId}`
export const GUEST_SESSION_KEY = (bookId: number) => `english_guest_session_${bookId}`
export const GUEST_WORDBOOK_KEY = (bookId: number) => `english_guest_wordbook_${bookId}`
export const GUEST_CHECKIN_KEY = 'english_guest_checkin'

export function guestKeysExist(): boolean {
  return Object.keys(localStorage).some((k) => k.startsWith('english_guest_'))
}

export function clearGuestData(): void {
  for (const k of Object.keys(localStorage)) {
    if (k.startsWith('english_guest_')) localStorage.removeItem(k)
  }
}

export function guestCompletedDates(): string[] {
  try {
    return JSON.parse(localStorage.getItem(GUEST_CHECKIN_KEY) || '[]') as string[]
  } catch {
    return []
  }
}

// ── 云端适配器 ─────────────────────────────────────────────────────

export const cloudAdapter: SrsStorageAdapter = {
  async loadState(bookId) {
    return getSrsState(bookId || undefined)
  },
  async saveState(bookId, memory, session) {
    await saveSrsState({ book_id: bookId, memory, session })
  },
  async completeDay(payload) {
    return apiCompleteDay(payload)
  },
  async syncGuest(bookId, memory, wordbook) {
    return apiSyncGuest({ book_id: bookId, memory, wordbook })
  },
  async reset(bookId) {
    await apiResetBook(bookId)
  },
}

// ── 本地适配器 ─────────────────────────────────────────────────────

export const localAdapter: SrsStorageAdapter = {
  async loadState(_bookId) {
    let settings: SrsSettings | null = null
    try {
      const raw = localStorage.getItem(GUEST_SETTINGS_KEY)
      if (raw) settings = JSON.parse(raw) as SrsSettings
    } catch {
      /* ignore */
    }
    const memory: MemoryRow[] = []
    let session: SrsSessionState | null = null
    const memRaw = localStorage.getItem(GUEST_MEMORY_KEY(_bookId))
    if (memRaw) {
      try {
        memory.push(...(JSON.parse(memRaw) as MemoryRow[]))
      } catch {
        /* ignore */
      }
    }
    const sessRaw = localStorage.getItem(GUEST_SESSION_KEY(_bookId))
    if (sessRaw) {
      try {
        const parsed = JSON.parse(sessRaw) as SrsSessionState
        if (parsed && (parsed.date || parsed.phase)) session = parsed
      } catch {
        /* ignore */
      }
    }
    return { settings, memory, session }
  },
  async saveState(bookId, memory, session) {
    localStorage.setItem(GUEST_MEMORY_KEY(bookId), JSON.stringify(memory))
    if (session) localStorage.setItem(GUEST_SESSION_KEY(bookId), JSON.stringify(session))
  },
  async completeDay(payload) {
    const dates = guestCompletedDates()
    if (!dates.includes(payload.study_date)) dates.push(payload.study_date)
    localStorage.setItem(GUEST_CHECKIN_KEY, JSON.stringify(dates))
    // 本地打卡返回与云端同形状
    const streak = computeLocalStreak(dates)
    return {
      checkin: { streak_days: streak, total_days: dates.length, today_done: true },
      summary: { total_studied: 0, wordbook_count: 0, mastered_count: 0, streak_days: streak },
    }
  },
  async syncGuest(_bookId, _memory, _wordbook) {
    return { memory_merged: 0, wordbook_merged: 0 }
  },
  async reset(bookId) {
    localStorage.removeItem(GUEST_MEMORY_KEY(bookId))
    localStorage.removeItem(GUEST_SESSION_KEY(bookId))
    localStorage.removeItem(GUEST_WORDBOOK_KEY(bookId))
    const settingsRaw = localStorage.getItem(GUEST_SETTINGS_KEY)
    if (settingsRaw) {
      try {
        const s = JSON.parse(settingsRaw) as SrsSettings
        s.onboarding_done = false
        localStorage.setItem(GUEST_SETTINGS_KEY, JSON.stringify(s))
      } catch {
        /* ignore */
      }
    }
  },
}

function computeLocalStreak(dates: string[]): number {
  const set = new Set(dates)
  let streak = 0
  const d = new Date()
  const iso = (dt: Date) => `${dt.getFullYear()}-${`${dt.getMonth() + 1}`.padStart(2, '0')}-${`${dt.getDate()}`.padStart(2, '0')}`
  if (!set.has(iso(d))) d.setDate(d.getDate() - 1)
  while (set.has(iso(d))) {
    streak += 1
    d.setDate(d.getDate() - 1)
  }
  return streak
}

// ── 游客设置 / 生词本读写 ─────────────────────────────────────────

export function loadGuestSettings(): SrsSettings | null {
  try {
    const raw = localStorage.getItem(GUEST_SETTINGS_KEY)
    return raw ? (JSON.parse(raw) as SrsSettings) : null
  } catch {
    return null
  }
}

export function saveGuestSettings(settings: SrsSettings): void {
  localStorage.setItem(GUEST_SETTINGS_KEY, JSON.stringify(settings))
}

export function loadGuestWordbook(bookId: number): number[] {
  try {
    return JSON.parse(localStorage.getItem(GUEST_WORDBOOK_KEY(bookId)) || '[]') as number[]
  } catch {
    return []
  }
}

export function saveGuestWordbook(bookId: number, wordIds: number[]): void {
  localStorage.setItem(GUEST_WORDBOOK_KEY(bookId), JSON.stringify(wordIds))
}

// ── 游客单词分类 ─────────────────────────────────────────────────

export const GUEST_TAGS_KEY = (bookId: number) => `english_guest_tags_${bookId}`

export function loadGuestTags(bookId: number): Record<number, string> {
  try {
    return JSON.parse(localStorage.getItem(GUEST_TAGS_KEY(bookId)) || '{}') as Record<number, string>
  } catch {
    return {}
  }
}

export function saveGuestTag(bookId: number, wordId: number, tag: string | null): void {
  const tags = loadGuestTags(bookId)
  if (tag) tags[wordId] = tag
  else delete tags[wordId]
  localStorage.setItem(GUEST_TAGS_KEY(bookId), JSON.stringify(tags))
}

/** 游客 bookWords 合并本地分类标签 */
export function mergeGuestTags<T extends { id: number; tag: string | null }>(bookId: number, words: T[]): T[] {
  const tags = loadGuestTags(bookId)
  return words.map((w) => ({ ...w, tag: tags[w.id] ?? null }))
}

export function guestInitBook(bookId: number, allWordIds: number[], settings: SrsSettings): void {
  localStorage.setItem(
    GUEST_MEMORY_KEY(bookId),
    JSON.stringify(allWordIds.map((word_id) => ({ word_id, status: 0, next_review_date: null, interval: 0, wrong_count: 0 }))),
  )
  localStorage.setItem(GUEST_SESSION_KEY(bookId), JSON.stringify(null))
  saveGuestSettings({ ...settings, onboarding_done: true })
}

// 适配器选择
export function getAdapter(loggedIn: boolean): SrsStorageAdapter {
  return loggedIn ? cloudAdapter : localAdapter
}
