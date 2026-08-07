/** 与后端 /api/v1/english 响应对应的类型定义 */

export interface UserProfile {
  id: number
  username: string
  email: string
  nickname: string | null
  avatar: string | null
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface RegisterResponse extends TokenPair {
  user: UserProfile
}

export interface WordBook {
  id: number
  code: string
  name: string
  sort_order: number
  word_count: number
}

export interface Word {
  id: number
  book_id: number
  word: string
  phonetic: string | null
  definition: string
  pos: string | null
  example: string | null
  example2: string | null
  phrase: string | null
  level: string | null
  tags: string | null
  in_wordbook: boolean
  is_favorite: boolean
  /** 用户分类（core/common/advanced），未分类为 null */
  tag: string | null
}

/** 单词分类选项（code → 中文名） */
export const WORD_CATEGORIES: { tag: string; name: string }[] = [
  { tag: 'core', name: '核心' },
  { tag: 'common', name: '常用' },
  { tag: 'advanced', name: '拓展' },
]

export function categoryName(tag: string | null): string {
  return WORD_CATEGORIES.find((c) => c.tag === tag)?.name ?? '未分类'
}

export interface Category {
  tag: string
  name: string
  count: number
}

export interface WordbookItem {
  id: number
  book_id: number
  created_at: string
  word: Word
}

// ── SRS ────────────────────────────────────────────────────────────

export interface MemoryRow {
  word_id: number
  status: number // 0 未学习 / 1 学习中 / 2 已掌握
  next_review_date: string | null
  interval: number // 1|2|4|7|15
  wrong_count: number
}

export interface SrsSessionState {
  date: string | null
  phase: 'review' | 'new' | 'done'
  review_queue: number[]
  new_queue: number[]
  review_done: number
  new_done: number
  wrong_total: number
  /** 当日第几轮（继续学习轮次；首轮为 0） */
  round: number
}

export interface SrsSettings {
  book_id: number
  target: string
  daily_new_words: number
  pronunciation: 'us' | 'uk'
  autoplay: boolean
  onboarding_done: boolean
}

export interface SrsState {
  settings: SrsSettings | null
  memory: MemoryRow[]
  session: SrsSessionState | null
}

export interface BookStats {
  book_id: number
  total_words: number
  unlearned: number
  learning: number
  mastered: number
  wordbook_count: number
}

export interface SrsStats {
  total_studied: number
  wordbook_count: number
  mastered_count: number
  streak_days: number
  total_days: number
  today_done: boolean
  per_book: BookStats[]
}

export interface CompleteResult {
  checkin: { streak_days: number; total_days: number; today_done: boolean }
  summary: {
    total_studied: number
    wordbook_count: number
    mastered_count: number
    streak_days: number
  }
}

export interface TestQuestion {
  word_id: number
  word: string
  phonetic: string | null
  definition: string
  pos: string | null
  type: 'a' | 'b' | 'c' | 'd' | 'e'
  show: 'word' | 'definition' | 'audio'
  options: string[]
  answer: string
  mask: string
  example_en: string | null
  example_cn: string | null
}

export interface TestQuestions {
  questions: TestQuestion[]
  mode: string
  module: string
  question_type: string
  total: number
}

export interface ActivityReport {
  activity_date?: string
  word_study_sec?: number
  reading_article_id?: number
  reading_duration_sec?: number
  word_lookups?: number
  test_choice_questions?: number
  test_choice_correct?: number
  test_fill_questions?: number
  test_fill_correct?: number
}

export interface SummaryItem {
  label: string
  value: string
}

export interface SummaryCategory {
  category: string
  items: SummaryItem[]
}

export interface DailySummary {
  date: string
  table: SummaryCategory[] | null
  ai_overview: string | null
  ai_advice: string | null
  source: string | null
  generated_at: string | null
}

export interface ArticleItem {
  id: number
  title: string
  level: string | null
  word_count: number
  is_favorite: boolean
  note_id: number | null
  note_updated_at: string | null
}

export interface Article extends ArticleItem {
  content: string
  content_cn: string | null
  topic: string | null
  publish_date: string | null
  keywords: ReadingKeyword[] | null
}

export interface ReadingKeyword {
  word: string
  definition: string
  example: string
}

// ── 每日一读 ────────────────────────────────────────────────────────

export interface DailyReadingRecord {
  status: 'pending' | 'done'
  level: 'basic' | 'cet4' | 'advanced'
  level_label: string
  correct_count: number
  total_questions: number
  accuracy: number
  new_word_count: number
}

export interface DailyReadingToday {
  record: DailyReadingRecord
  article: Article
  level_mode: 'auto' | 'manual'
  manual_level: 'basic' | 'cet4' | 'advanced' | null
  topics: string[]
  estimated_min: number
  word_task_done: boolean
}

export interface ReadingArchiveItem {
  id: number
  reading_date: string
  article_id: number
  title: string
  level: string
  level_label: string
  topic: string | null
  topic_label: string
  status: string
  correct_count: number
  total_questions: number
  accuracy: number
  new_word_count: number
  is_favorite: boolean
  note_id: number | null
}

export interface ReadingQuizQuestion {
  word_id: number
  word: string
  phonetic: string | null
  definition: string
  pos: string | null
  type: 'a' | 'b' | 'c' | 'd' | 'e'
  show: 'word' | 'definition' | 'audio'
  options: string[]
  answer: string
  mask: string
  example_en: string | null
  example_cn: string | null
}

export interface ReadingQuiz {
  questions: ReadingQuizQuestion[]
  total: number
}

export const READING_LEVEL_LABEL: Record<string, string> = {
  basic: '基础',
  cet4: '四级',
  advanced: '高阶',
}

export const READING_TOPIC_LABEL: Record<string, string> = {
  fun_science: '趣味科普',
  life_story: '生活故事',
  film: '影视文摘',
  motto: '短句美文',
  exam: '应试短文',
}

export interface Note {
  id: number
  article_id: number
  article_title: string | null
  content: string
  created_at: string
  updated_at: string
}

export interface CollectionItem {
  id: number
  item_type: 'word' | 'listening' | 'reading'
  item_id: number
  created_at: string
  title: string | null
  subtitle: string | null
}

export interface CheckinStats {
  streak_days: number
  total_days: number
  today_done: boolean
  recent_dates: string[]
}

export interface StudyStats {
  total_words: number
  wordbook_count: number
  mastered_count: number
  favorite_count: number
  note_count: number
  checkin_total: number
  checkin_streak: number
  today_checkin: boolean
}
