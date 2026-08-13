/** /api/v1/english 相关接口的封装 */
import { request } from './http'
import type {
  ActivityReport,
  Article,
  ArticleItem,
  Category,
  CheckinStats,
  CollectResult,
  CollectionItem,
  CompleteResult,
  DailyReadingToday,
  DailySummary,
  MemoryRow,
  Note,
  ReadingArchiveItem,
  ReadingQuiz,
  RegisterResponse,
  RewardOverview,
  SrsSessionState,
  SrsSettings,
  SrsState,
  SrsStats,
  ShopItem,
  StudyStats,
  TestQuestions,
  TokenPair,
  UserProfile,
  Word,
  WordBook,
  WordbookItem,
} from '@/types'

// ── 认证 ─────────────────────────────────────────────────────────

export function login(username: string, password: string): Promise<TokenPair> {
  return request<TokenPair>('/tenant/auth/login_with_tenant', {
    method: 'POST',
    auth: false,
    query: { tenant_code: 'english' },
    body: { username, password },
  })
}

export function register(data: {
  username: string
  email: string
  password: string
}): Promise<RegisterResponse> {
  return request<RegisterResponse>('/english/auth/register', {
    method: 'POST',
    auth: false,
    body: data,
  })
}

export function refreshToken(refresh_token: string): Promise<TokenPair> {
  return request<TokenPair>('/english/auth/refresh', {
    method: 'POST',
    auth: false,
    body: { refresh_token },
  })
}

export function getProfile(): Promise<UserProfile> {
  return request<UserProfile>('/english/auth/profile')
}

export function updateProfile(data: { nickname?: string; avatar?: string }): Promise<UserProfile> {
  return request<UserProfile>('/english/auth/profile', { method: 'PUT', body: data })
}

// ── 单词 / 词书 ──────────────────────────────────────────────────

export function listWords(params?: { book_id?: number; level?: string; skip?: number; limit?: number }): Promise<Word[]> {
  return request<Word[]>('/english/words', { query: params })
}

export function lookupWord(word: string): Promise<{ word: string; phonetic: string | null; definition: string; pos: string | null }> {
  return request('/english/words/lookup', { query: { word } })
}

export function listBooks(): Promise<WordBook[]> {
  return request<WordBook[]>('/english/srs/books', { auth: false })
}

// ── SRS 背单词 ────────────────────────────────────────────────────

export function getSrsState(book_id?: number): Promise<SrsState> {
  return request<SrsState>('/english/srs/state', { query: { book_id } })
}

export function saveSrsState(data: {
  book_id: number
  memory: MemoryRow[]
  session: SrsSessionState | null
}): Promise<{ saved: boolean }> {
  return request<{ saved: boolean }>('/english/srs/state', { method: 'POST', body: data })
}

export function onboarding(data: {
  target: string
  book_id: number
  daily_new_words: number
  pronunciation: string
  autoplay: boolean
}): Promise<SrsSettings> {
  return request<SrsSettings>('/english/srs/onboarding', { method: 'POST', body: data })
}

export function completeDay(data: {
  book_id: number
  study_date: string
  review_count: number
  new_count: number
  wrong_count: number
}): Promise<CompleteResult> {
  return request<CompleteResult>('/english/srs/complete', { method: 'POST', body: data })
}

export function syncGuest(data: { book_id: number; memory: MemoryRow[]; wordbook: number[] }): Promise<{ memory_merged: number; wordbook_merged: number }> {
  return request<{ memory_merged: number; wordbook_merged: number }>('/english/srs/sync', { method: 'POST', body: data })
}

export function resetBook(book_id: number): Promise<{ reset: boolean }> {
  return request<{ reset: boolean }>('/english/srs/reset', { method: 'POST', body: { book_id } })
}

export function getSrsStats(): Promise<SrsStats> {
  return request<SrsStats>('/english/srs/stats')
}

export function setWordTag(book_id: number, word_id: number, tag: string | null): Promise<{ word_id: number; tag: string | null }> {
  return request<{ word_id: number; tag: string | null }>('/english/srs/tag', { method: 'PUT', body: { book_id, word_id, tag } })
}

export function getCategories(book_id: number): Promise<Category[]> {
  return request<Category[]>('/english/srs/categories', { query: { book_id } })
}

export function getTestQuestions(params: {
  book_id: number
  module: 'choice' | 'fill'
  question_type: 'a' | 'b' | 'c' | 'd' | 'e'
  mode: 'today' | 'book' | 'wordbook' | 'reading_new'
  count: number
}): Promise<TestQuestions> {
  return request<TestQuestions>('/english/test/questions', { query: params })
}

// ── 每日一读 ─────────────────────────────────────────────────────

export function getDailyReadingToday(): Promise<DailyReadingToday> {
  return request<DailyReadingToday>('/english/daily-reading/today')
}

export function setReadingLevel(mode: 'auto' | 'manual', level?: 'basic' | 'cet4' | 'advanced'): Promise<{ saved: boolean; mode: string; level: string | null }> {
  return request('/english/daily-reading/level', { method: 'PUT', body: { mode, level } })
}

export function getReadingQuiz(article_id: number): Promise<ReadingQuiz> {
  return request<ReadingQuiz>('/english/daily-reading/quiz', { query: { article_id } })
}

export function submitReadingQuiz(
  article_id: number,
  answers: { word: string; type: string; correct: boolean; definition?: string }[],
): Promise<{ saved: boolean; correct: number; total: number }> {
  return request('/english/daily-reading/quiz', { method: 'POST', body: { article_id, answers } })
}

export function collectReadingWord(article_id: number, word: string, source: string, definition?: string): Promise<{ status: string; reason?: string; word_id?: number }> {
  return request('/english/daily-reading/words', { method: 'POST', body: { article_id, word, source, definition } })
}

export function setReadingBlacklist(word: string, blacklisted: boolean): Promise<{ saved: boolean; blacklisted: boolean }> {
  return request('/english/daily-reading/words/blacklist', { method: 'PUT', body: { word, blacklisted } })
}

export function completeDailyReading(article_id: number, duration_sec: number): Promise<{ saved: boolean; status: string }> {
  return request('/english/daily-reading/complete', { method: 'POST', body: { article_id, duration_sec } })
}

export function getReadingArchive(): Promise<ReadingArchiveItem[]> {
  return request<ReadingArchiveItem[]>('/english/daily-reading/archive')
}

// ── AI 每日学习总结 ──────────────────────────────────────────────

export function reportActivity(data: ActivityReport): Promise<{ saved: boolean }> {
  return request<{ saved: boolean }>('/english/activity', { method: 'POST', body: data })
}

export function getTodayActivity(): Promise<{ has_activity: boolean }> {
  return request<{ has_activity: boolean }>('/english/activity/today')
}

export function getDailySummary(): Promise<DailySummary> {
  return request<DailySummary>('/english/daily-summary')
}

export function generateDailySummary(): Promise<DailySummary> {
  return request<DailySummary>('/english/daily-summary/generate', { method: 'POST' })
}

// ── 生词本 ────────────────────────────────────────────────────────

export function listWordbook(book_id?: number): Promise<WordbookItem[]> {
  return request<WordbookItem[]>('/english/wordbook', { query: { book_id } })
}

export function addWordbook(word_id: number, book_id: number): Promise<WordbookItem> {
  return request<WordbookItem>('/english/wordbook', { method: 'POST', body: { word_id, book_id } })
}

export function removeWordbook(id: number): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>(`/english/wordbook/${id}`, { method: 'DELETE' })
}

export function clearWordbook(book_id: number): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>('/english/wordbook', { method: 'DELETE', query: { book_id } })
}

// ── 阅读 ─────────────────────────────────────────────────────────

export function listArticles(): Promise<ArticleItem[]> {
  return request<ArticleItem[]>('/english/reading/articles')
}

export function getArticle(id: number): Promise<Article> {
  return request<Article>(`/english/reading/articles/${id}`)
}

export function listNotes(): Promise<Note[]> {
  return request<Note[]>('/english/reading/notes')
}

export function createNote(article_id: number, content: string): Promise<Note> {
  return request<Note>('/english/reading/notes', { method: 'POST', body: { article_id, content } })
}

export function updateNote(id: number, content: string): Promise<Note> {
  return request<Note>(`/english/reading/notes/${id}`, { method: 'PUT', body: { content } })
}

export function deleteNote(id: number): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>(`/english/reading/notes/${id}`, { method: 'DELETE' })
}

// ── 收藏 ─────────────────────────────────────────────────────────

export function listCollections(item_type?: string): Promise<CollectionItem[]> {
  return request<CollectionItem[]>('/english/collections', { query: { item_type } })
}

export function addCollection(item_type: string, item_id: number): Promise<CollectionItem> {
  return request<CollectionItem>('/english/collections', {
    method: 'POST',
    body: { item_type, item_id },
  })
}

export function removeCollection(id: number): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>(`/english/collections/${id}`, { method: 'DELETE' })
}

// ── 打卡 / 统计 ──────────────────────────────────────────────────

export function checkin(): Promise<CheckinStats> {
  return request<CheckinStats>('/english/checkin', { method: 'POST' })
}

export function getCheckinStats(): Promise<CheckinStats> {
  return request<CheckinStats>('/english/checkin/stats')
}

export function getStudyStats(): Promise<StudyStats> {
  return request<StudyStats>('/english/study/stats')
}

// ── 奖励系统 ─────────────────────────────────────────────────────

export function getRewardsOverview(): Promise<RewardOverview> {
  return request<RewardOverview>('/rewards/overview')
}

export function getRewardsShop(): Promise<ShopItem[]> {
  return request<ShopItem[]>('/rewards/shop')
}

export function collectRewards(): Promise<CollectResult> {
  return request<CollectResult>('/rewards/collect', { method: 'POST' })
}

export function redeemReward(itemKey: string): Promise<ShopItem> {
  return request<ShopItem>('/rewards/redeem', { method: 'POST', body: { item_key: itemKey } })
}

export function equipReward(
  itemKey: string | null,
): Promise<{ equipped_title: string | null; equipped_decor: string | null }> {
  return request<{ equipped_title: string | null; equipped_decor: string | null }>('/rewards/equip', {
    method: 'POST',
    body: { item_key: itemKey },
  })
}
