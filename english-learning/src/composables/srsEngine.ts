/**
 * 背单词 SRS 状态机 —— 唯一实现，登录用户与游客共用。
 *
 * 规则：
 * - 固定艾宾浩斯间隔 1→2→4→7→15，走完 → 已掌握(2)，不再复习
 * - 每日顺序：先复习到期旧词，复习队列清空后解锁新词
 * - 仅 认识/不认识 两个操作
 * - 复习·不认识：间隔重置 1、next=明天、wrong_count==1 时本轮末尾再插一次
 * - 新词·不认识：当天最多 3 次尝试（初始+2 次重复推送），第 3 次仍不认识则落定次日复习
 *
 * 纯函数，无 Vue/fetch/localStorage 依赖，便于单元测试。
 */

export const SUCCESSOR: Record<number, number> = { 1: 2, 2: 4, 4: 7, 7: 15 }

export interface MemoryRow {
  word_id: number
  status: number // 0/1/2
  next_review_date: string | null // YYYY-MM-DD
  interval: number
  wrong_count: number
}

export type Phase = 'review' | 'new' | 'done'

export interface SessionState {
  date: string | null
  phase: Phase
  review_queue: number[]
  new_queue: number[]
  review_done: number
  new_done: number
  wrong_total: number
  /** 当日第几轮（继续学习轮次；首轮为 0） */
  round: number
}

export interface SrsContext {
  memory: Map<number, MemoryRow>
  session: SessionState
}

/** 本地时区 YYYY-MM-DD */
export function todayStr(): string {
  const d = new Date()
  const m = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

export function addDaysStr(dateStr: string, days: number): string {
  const parts = dateStr.split('-').map(Number)
  const [y = 0, m = 1, d = 1] = parts
  const dt = new Date(y, m - 1, d)
  dt.setDate(dt.getDate() + days)
  const mm = `${dt.getMonth() + 1}`.padStart(2, '0')
  const dd = `${dt.getDate()}`.padStart(2, '0')
  return `${dt.getFullYear()}-${mm}-${dd}`
}

function emptySession(): SessionState {
  return { date: null, phase: 'review', review_queue: [], new_queue: [], review_done: 0, new_done: 0, wrong_total: 0, round: 0 }
}

function enterNewPhase(mem: Map<number, MemoryRow>, s: SessionState, dailyNewWords: number, allWordIds: number[]): void {
  if (s.new_queue.length > 0) return // 已构建过，不重复
  const unlearned = allWordIds.filter((id) => (mem.get(id)?.status ?? 0) === 0)
  s.phase = 'new'
  s.new_queue = unlearned.slice(0, dailyNewWords)
}

/**
 * 初始化/重建当日会话：跨天重置 wrong_count，重建复习队列；
 * 无到期词则直接进入新词阶段。
 */
export function ensureSession(
  memory: MemoryRow[],
  session: SessionState | null,
  dailyNewWords: number,
  allWordIds: number[],
): SrsContext {
  const mem = new Map(memory.map((m) => [m.word_id, { ...m }]))
  const today = todayStr()

  if (!session || session.date !== today) {
    for (const row of mem.values()) row.wrong_count = 0
    const due = memory
      .filter((m) => m.status === 1 && m.next_review_date && m.next_review_date <= today)
      .sort((a, b) => (a.next_review_date! < b.next_review_date! ? -1 : 1))
      .map((m) => m.word_id)
    const s = emptySession()
    s.date = today
    s.review_queue = due
    s.phase = due.length > 0 ? 'review' : 'new'
    if (s.phase === 'new') enterNewPhase(mem, s, dailyNewWords, allWordIds)
    if (s.new_queue.length === 0 && s.phase === 'new') s.phase = 'done'
    return { memory: mem, session: s }
  }

  return { memory: mem, session: { ...session } }
}

/** 复习作答：认识升间隔/完结；不认识重置+末尾重插一次 */
export function answerReview(ctx: SrsContext, wordId: number, known: boolean, today = todayStr()): SrsContext {
  const mem = new Map(ctx.memory)
  const s: SessionState = { ...ctx.session, review_queue: [...ctx.session.review_queue], new_queue: [...ctx.session.new_queue] }
  const row = mem.get(wordId)
  if (!row) return ctx
  s.review_queue.shift()

  if (known) {
    row.wrong_count = 0
    if (row.interval === 15) {
      row.status = 2
      row.next_review_date = null
    } else {
      row.interval = SUCCESSOR[row.interval] ?? 1
      row.next_review_date = addDaysStr(today, row.interval)
    }
  } else {
    row.wrong_count += 1
    row.interval = 1
    row.next_review_date = addDaysStr(today, 1)
    s.wrong_total += 1
    if (row.wrong_count === 1) s.review_queue.push(wordId) // 仅首次末尾重插，保证清空
  }
  s.review_done += 1
  mem.set(wordId, row)
  return { memory: mem, session: s }
}

/** 新词作答：认识落定1天；不认识<3次重推，第3次落定次日复习 */
export function answerNew(ctx: SrsContext, wordId: number, known: boolean, today = todayStr()): SrsContext {
  const mem = new Map(ctx.memory)
  const s: SessionState = { ...ctx.session, review_queue: [...ctx.session.review_queue], new_queue: [...ctx.session.new_queue] }
  let row = mem.get(wordId)
  if (!row) {
    // 新词可能尚无记忆行（如全新游客/新加入单词）：先建默认行
    row = { word_id: wordId, status: 0, next_review_date: null, interval: 0, wrong_count: 0 }
    mem.set(wordId, row)
  }
  s.new_queue.shift()

  if (known) {
    row.status = 1
    row.interval = 1
    row.next_review_date = addDaysStr(today, 1)
    row.wrong_count = 0
  } else {
    row.wrong_count += 1
    s.wrong_total += 1
    if (row.wrong_count < 3) {
      s.new_queue.push(wordId) // 当天重复推送（共 3 次尝试）
    } else {
      row.status = 1
      row.interval = 1
      row.next_review_date = addDaysStr(today, 1)
    }
  }
  s.new_done += 1
  mem.set(wordId, row)
  return { memory: mem, session: s }
}

/** 每次作答后调用：处理阶段推进 */
export function advancePhase(ctx: SrsContext, dailyNewWords: number, allWordIds: number[]): SrsContext {
  const s = { ...ctx.session, review_queue: [...ctx.session.review_queue], new_queue: [...ctx.session.new_queue] }
  if (s.phase === 'review' && s.review_queue.length === 0) {
    enterNewPhase(ctx.memory, s, dailyNewWords, allWordIds)
  }
  if (s.phase === 'new' && s.new_queue.length === 0) {
    s.phase = 'done'
  }
  return { memory: ctx.memory, session: s }
}

/** 当前应展示的词（复习或新词队列队首） */
export function currentWordId(ctx: SrsContext): number | null {
  const s = ctx.session
  if (s.phase === 'review' && s.review_queue.length > 0) return s.review_queue[0] ?? null
  if (s.phase === 'new' && s.new_queue.length > 0) return s.new_queue[0] ?? null
  return null
}

/**
 * 继续学习：完成一轮后从剩余未学池再取一批新词（无每日上限）。
 * 新一轮只有新词（本轮已把到期词复习完），轮次 +1，本轮计数清零。
 */
export function continueLearning(ctx: SrsContext, dailyNewWords: number, allWordIds: number[]): SrsContext {
  const mem = new Map(ctx.memory)
  const s: SessionState = {
    date: ctx.session.date ?? todayStr(),
    phase: 'new',
    review_queue: [],
    new_queue: [],
    review_done: 0,
    new_done: 0,
    wrong_total: 0,
    round: (ctx.session.round ?? 0) + 1,
  }
  enterNewPhase(mem, s, dailyNewWords, allWordIds)
  if (s.new_queue.length === 0) s.phase = 'done'
  return { memory: mem, session: s }
}

/** 词书中是否还有未学单词（可继续学习） */
export function hasUnlearned(memory: MemoryRow[], allWordIds: number[]): boolean {
  const mem = new Map(memory.map((m) => [m.word_id, m]))
  return allWordIds.some((id) => (mem.get(id)?.status ?? 0) === 0)
}

export function isDayComplete(ctx: SrsContext): boolean {
  return ctx.session.phase === 'done'
}

export function toRows(ctx: SrsContext): MemoryRow[] {
  return [...ctx.memory.values()]
}
