import { describe, expect, it } from 'vitest'
import {
  addDaysStr,
  advancePhase,
  answerNew,
  answerReview,
  continueLearning,
  ensureSession,
  hasUnlearned,
  isDayComplete,
  todayStr,
  toRows,
  type MemoryRow,
  type SessionState,
} from '../srsEngine'

// 测试日期：动态取今天（避免硬编码日期漂移）
const TODAY = todayStr()

function mem(wordId: number, status = 0, next?: string | null, interval = 0, wrong = 0): MemoryRow {
  return { word_id: wordId, status, next_review_date: next ?? null, interval, wrong_count: wrong }
}

function freshSession(date = TODAY): SessionState {
  return { date, phase: 'review', review_queue: [], new_queue: [], review_done: 0, new_done: 0, wrong_total: 0, round: 0 }
}

// 全部单词池
const ALL = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

describe('addDaysStr', () => {
  it('跨月/跨年正确', () => {
    expect(addDaysStr('2026-08-01', 1)).toBe('2026-08-02')
    expect(addDaysStr('2026-08-31', 1)).toBe('2026-09-01')
    expect(addDaysStr('2026-12-31', 1)).toBe('2027-01-01')
    expect(addDaysStr('2026-08-01', 15)).toBe('2026-08-16')
  })
})

describe('ensureSession 复习队列构建', () => {
  it('到期词按到期日升序进入复习队列', () => {
    // 用动态日期：today 之前（到期）、today+2（未到期）
    const later = addDaysStr(TODAY, -1)  // 词1 今天-1
    const earlier = addDaysStr(TODAY, -2) // 词2 今天-2（更早到期 → 排前）
    const future = addDaysStr(TODAY, 2)
    const memory = [mem(1, 1, later, 1), mem(2, 1, earlier, 2), mem(3, 1, future, 1)]
    const ctx = ensureSession(memory, null, 10, ALL)
    expect(ctx.session.phase).toBe('review')
    expect(ctx.session.review_queue).toEqual([2, 1]) // future 未到期不入队
  })

  it('无到期词时直接进入新词阶段，取未学池前 N 个', () => {
    const future = addDaysStr(TODAY, 1)
    const memory = [mem(1, 1, future, 1), mem(5, 2), mem(6, 2)] // 1 未到期，5/6 已掌握
    const ctx = ensureSession(memory, null, 3, ALL)
    expect(ctx.session.phase).toBe('new')
    expect(ctx.session.new_queue).toEqual([2, 3, 4]) // 未学池按 word_id 升序前 3 个
  })

  it('跨天 wrong_count 重置', () => {
    const memory = [mem(1, 1, TODAY, 1, 2)]
    const ctx = ensureSession(memory, freshSession(addDaysStr(TODAY, -1)), 10, ALL)
    expect(ctx.memory.get(1)!.wrong_count).toBe(0)
  })
})

describe('复习阶段作答', () => {
  it('认识：1→2 天，next 顺延', () => {
    let ctx = ensureSession([mem(1, 1, TODAY, 1)], null, 10, ALL)
    ctx = answerReview(ctx, 1, true, TODAY)
    expect(ctx.memory.get(1)!.interval).toBe(2)
    expect(ctx.memory.get(1)!.next_review_date).toBe(addDaysStr(TODAY, 2))
    expect(ctx.memory.get(1)!.wrong_count).toBe(0)
    expect(ctx.session.review_queue).toEqual([])
  })

  it('认识：7→15 天', () => {
    let ctx = ensureSession([mem(1, 1, TODAY, 7)], null, 10, ALL)
    ctx = answerReview(ctx, 1, true, TODAY)
    expect(ctx.memory.get(1)!.interval).toBe(15)
  })

  it('认识：15 天 → 已掌握(status=2)，next=null，不再复习', () => {
    let ctx = ensureSession([mem(1, 1, TODAY, 15)], null, 10, ALL)
    ctx = answerReview(ctx, 1, true, TODAY)
    expect(ctx.memory.get(1)!.status).toBe(2)
    expect(ctx.memory.get(1)!.next_review_date).toBeNull()
    // 后续 ensureSession 不再把它放入复习队列
    const next = ensureSession(toRows(ctx), ctx.session, 10, ALL)
    expect(next.session.review_queue).not.toContain(1)
  })

  it('不认识：间隔重置 1，next=明天，仅首次末尾重插一次', () => {
    let ctx = ensureSession([mem(1, 1, TODAY, 4)], null, 10, ALL)
    ctx = answerReview(ctx, 1, false, TODAY)
    expect(ctx.memory.get(1)!.interval).toBe(1)
    expect(ctx.memory.get(1)!.next_review_date).toBe(addDaysStr(TODAY, 1))
    expect(ctx.memory.get(1)!.wrong_count).toBe(1)
    expect(ctx.session.review_queue).toEqual([1]) // 末尾重插

    // 第二次仍不认识：不再重插，队列清空
    ctx = answerReview(ctx, 1, false, TODAY)
    expect(ctx.memory.get(1)!.wrong_count).toBe(2)
    expect(ctx.session.review_queue).toEqual([])
  })
})

describe('新词阶段作答', () => {
  it('认识：落定 status=1, interval=1, next=明天', () => {
    let ctx = ensureSession([], null, 3, ALL)
    ctx = answerNew(ctx, 2, true, TODAY)
    expect(ctx.memory.get(2)!.status).toBe(1)
    expect(ctx.memory.get(2)!.interval).toBe(1)
    expect(ctx.memory.get(2)!.next_review_date).toBe(addDaysStr(TODAY, 1))
  })

  it('不认识：<3 次重推，共 3 次尝试，第 3 次仍不认识则落定次日复习', () => {
    // 词池只含 2 且每日 1 个 → 队列始终只面对词 2
    let ctx = ensureSession([], null, 1, [2, 99])
    expect(ctx.session.new_queue).toEqual([2])
    ctx = answerNew(ctx, 2, false, TODAY)
    expect(ctx.memory.get(2)!.wrong_count).toBe(1)
    expect(ctx.session.new_queue).toContain(2)
    ctx = answerNew(ctx, 2, false, TODAY)
    expect(ctx.memory.get(2)!.wrong_count).toBe(2)
    expect(ctx.session.new_queue).toContain(2)
    ctx = answerNew(ctx, 2, false, TODAY)
    expect(ctx.memory.get(2)!.wrong_count).toBe(3)
    expect(ctx.memory.get(2)!.status).toBe(1)
    expect(ctx.memory.get(2)!.interval).toBe(1)
    expect(ctx.memory.get(2)!.next_review_date).toBe(addDaysStr(TODAY, 1))
    expect(ctx.session.new_queue).toEqual([])
  })
})

describe('跨刷新续期', () => {
  it('答错后重建会话，重复推送剩余尝试保留', () => {
    // 第 1 天：新词 2 答错一次（wrong_count=1，还有 2 次尝试）
    let ctx = ensureSession([], null, 1, [2, 99])
    ctx = answerNew(ctx, 2, false, TODAY)
    const rowsAfterReload = toRows(ctx)
    const sessionAfterReload = ctx.session

    // 模拟刷新：用持久化的 rows + session 重建
    const rebuilt = ensureSession(rowsAfterReload, sessionAfterReload, 1, [2, 99])
    expect(rebuilt.session.phase).toBe('new')
    expect(rebuilt.session.new_queue).toContain(2)
    expect(rebuilt.memory.get(2)!.wrong_count).toBe(1)

    let c = answerNew(rebuilt, 2, false, TODAY)
    expect(c.memory.get(2)!.wrong_count).toBe(2)
    expect(c.session.new_queue).toContain(2)
    c = answerNew(c, 2, false, TODAY)
    expect(c.memory.get(2)!.status).toBe(1)
    expect(c.session.new_queue).toEqual([])
  })

  it('复习阶段答错后刷新，重插保留', () => {
    let ctx = ensureSession([mem(1, 1, TODAY, 4)], null, 10, ALL)
    ctx = answerReview(ctx, 1, false, TODAY)
    const rebuilt = ensureSession(toRows(ctx), ctx.session, 10, ALL)
    expect(rebuilt.session.review_queue).toContain(1)
    expect(rebuilt.memory.get(1)!.wrong_count).toBe(1)
  })
})

describe('阶段推进', () => {
  it('复习队列清空 → 解锁新词 → 新词清空 → done', () => {
    // 仅 1 个到期词，daily=3
    let ctx = ensureSession([mem(1, 1, TODAY, 1)], null, 3, ALL)
    expect(ctx.session.phase).toBe('review')
    ctx = answerReview(ctx, 1, true, TODAY)
    ctx = advancePhase(ctx, 3, ALL)
    expect(ctx.session.phase).toBe('new')
    expect(ctx.session.new_queue.length).toBeGreaterThan(0)
    // 答完 3 个新词
    while (ctx.session.new_queue.length > 0) {
      const id = ctx.session.new_queue[0]!
      ctx = answerNew(ctx, id, true, TODAY)
      ctx = advancePhase(ctx, 3, ALL)
    }
    expect(isDayComplete(ctx)).toBe(true)
  })

  it('新词全部掌握后 ensureSession 不再产生新词（done）', () => {
    const allLearned = [1, 2, 3].map((id) => mem(id, 2))
    const ctx = ensureSession(allLearned, null, 3, [1, 2, 3])
    // 全部已掌握 → 无未学 → new 阶段立即 done
    expect(isDayComplete(ctx)).toBe(true)
  })
})

describe('继续学习（多轮）', () => {
  it('完成一轮后可继续拉取下一批未学词，轮次+1', () => {
    // 词池 5 个，每日 3 个 → 第一轮学 1,2,3
    let ctx = ensureSession([], null, 3, [1, 2, 3, 4, 5])
    expect(ctx.session.new_queue).toEqual([1, 2, 3])
    while (ctx.session.new_queue.length > 0) {
      const id = ctx.session.new_queue[0]!
      ctx = answerNew(ctx, id, true, TODAY)
      ctx = advancePhase(ctx, 3, [1, 2, 3, 4, 5])
    }
    expect(isDayComplete(ctx)).toBe(true)
    expect(ctx.session.round).toBe(0)
    expect(hasUnlearned(toRows(ctx), [1, 2, 3, 4, 5])).toBe(true)
    // 继续 → 第 2 轮取 4,5
    ctx = continueLearning(ctx, 3, [1, 2, 3, 4, 5])
    expect(ctx.session.round).toBe(1)
    expect(ctx.session.phase).toBe('new')
    expect(ctx.session.new_queue).toEqual([4, 5])
  })

  it('词库全部学完后 hasUnlearned=false 且 continueLearning 直接 done', () => {
    const allLearned = [1, 2, 3].map((id) => mem(id, 1, addDaysStr(TODAY, 1), 1))
    let ctx = ensureSession(allLearned, null, 3, [1, 2, 3])
    expect(hasUnlearned(toRows(ctx), [1, 2, 3])).toBe(false)
    ctx = continueLearning(ctx, 3, [1, 2, 3])
    expect(ctx.session.phase).toBe('done')
  })
})
