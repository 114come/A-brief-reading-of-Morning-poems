// 独立 SRS 引擎验证脚本（vitest worker 在本机不可用时使用）
// 运行：node scripts/verify-srs.mjs  （Node 24 原生剥离 TS 类型）
import assert from 'node:assert'
import {
  addDaysStr,
  advancePhase,
  answerNew,
  answerReview,
  continueLearning,
  ensureSession,
  hasUnlearned,
  isDayComplete,
  toRows,
} from '../src/composables/srsEngine.ts'

const TODAY = '2026-08-01'
const ALL = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

const mem = (wordId, status = 0, next = null, interval = 0, wrong = 0) =>
  ({ word_id: wordId, status, next_review_date: next, interval, wrong_count: wrong })
const freshSession = (date = TODAY) =>
  ({ date, phase: 'review', review_queue: [], new_queue: [], review_done: 0, new_done: 0, wrong_total: 0 })

let passed = 0
function ok(name, fn) {
  try {
    fn()
    passed++
    console.log('  ✓', name)
  } catch (e) {
    console.error('  ✗', name, '\n   ', e.message)
    process.exitCode = 1
  }
}

console.log('addDaysStr')
ok('跨月/跨年正确', () => {
  assert.equal(addDaysStr('2026-08-01', 1), '2026-08-02')
  assert.equal(addDaysStr('2026-08-31', 1), '2026-09-01')
  assert.equal(addDaysStr('2026-12-31', 1), '2027-01-01')
  assert.equal(addDaysStr('2026-08-01', 15), '2026-08-16')
})

console.log('ensureSession 复习队列构建')
ok('到期词按到期日升序', () => {
  const ctx = ensureSession([mem(1, 1, '2026-08-01', 1), mem(2, 1, '2026-07-30', 2), mem(3, 1, '2026-08-03', 1)], null, 10, ALL)
  assert.equal(ctx.session.phase, 'review')
  assert.deepEqual(ctx.session.review_queue, [2, 1])
})
ok('无到期词直接进新词阶段取前 N 个', () => {
  const ctx = ensureSession([mem(1, 1, '2026-08-05', 1), mem(5, 2), mem(6, 2)], null, 3, ALL)
  assert.equal(ctx.session.phase, 'new')
  assert.deepEqual(ctx.session.new_queue, [2, 3, 4])
})
ok('跨天 wrong_count 重置', () => {
  const ctx = ensureSession([mem(1, 1, '2026-08-01', 1, 2)], freshSession('2026-07-31'), 10, ALL)
  assert.equal(ctx.memory.get(1).wrong_count, 0)
})

console.log('复习阶段作答')
ok('认识 1→2 天', () => {
  let ctx = ensureSession([mem(1, 1, '2026-08-01', 1)], null, 10, ALL)
  ctx = answerReview(ctx, 1, true, TODAY)
  assert.equal(ctx.memory.get(1).interval, 2)
  assert.equal(ctx.memory.get(1).next_review_date, '2026-08-03')
})
ok('认识 7→15 天', () => {
  let ctx = ensureSession([mem(1, 1, '2026-08-01', 7)], null, 10, ALL)
  ctx = answerReview(ctx, 1, true, TODAY)
  assert.equal(ctx.memory.get(1).interval, 15)
})
ok('认识 15 天 → 已掌握不再复习', () => {
  let ctx = ensureSession([mem(1, 1, '2026-08-01', 15)], null, 10, ALL)
  ctx = answerReview(ctx, 1, true, TODAY)
  assert.equal(ctx.memory.get(1).status, 2)
  assert.equal(ctx.memory.get(1).next_review_date, null)
  const next = ensureSession(toRows(ctx), ctx.session, 10, ALL)
  assert.ok(!next.session.review_queue.includes(1))
})
ok('不认识：重置1天+单次重插', () => {
  let ctx = ensureSession([mem(1, 1, '2026-08-01', 4)], null, 10, ALL)
  ctx = answerReview(ctx, 1, false, TODAY)
  assert.equal(ctx.memory.get(1).interval, 1)
  assert.equal(ctx.memory.get(1).next_review_date, '2026-08-02')
  assert.deepEqual(ctx.session.review_queue, [1])
  ctx = answerReview(ctx, 1, false, TODAY)
  assert.equal(ctx.memory.get(1).wrong_count, 2)
  assert.deepEqual(ctx.session.review_queue, [])
})

console.log('新词阶段作答')
ok('认识落定1天', () => {
  let ctx = ensureSession([], null, 3, ALL)
  ctx = answerNew(ctx, 2, true, TODAY)
  assert.equal(ctx.memory.get(2).status, 1)
  assert.equal(ctx.memory.get(2).interval, 1)
  assert.equal(ctx.memory.get(2).next_review_date, '2026-08-02')
})
ok('不认识3次尝试后落定次日复习', () => {
  // 词池只含 2 且每日 1 个 → 队列始终只面对词 2
  let ctx = ensureSession([], null, 1, [2, 99])
  assert.deepEqual(ctx.session.new_queue, [2])
  ctx = answerNew(ctx, 2, false, TODAY)
  assert.equal(ctx.memory.get(2).wrong_count, 1)
  assert.ok(ctx.session.new_queue.includes(2))
  ctx = answerNew(ctx, 2, false, TODAY)
  assert.equal(ctx.memory.get(2).wrong_count, 2)
  assert.ok(ctx.session.new_queue.includes(2))
  ctx = answerNew(ctx, 2, false, TODAY)
  assert.equal(ctx.memory.get(2).wrong_count, 3)
  assert.equal(ctx.memory.get(2).status, 1)
  assert.equal(ctx.memory.get(2).next_review_date, '2026-08-02')
  assert.deepEqual(ctx.session.new_queue, [])
})

console.log('跨刷新续期')
ok('新词答错后重建会话剩余尝试保留', () => {
  let ctx = ensureSession([], null, 1, [2, 99])
  ctx = answerNew(ctx, 2, false, TODAY)
  const rebuilt = ensureSession(toRows(ctx), ctx.session, 1, [2, 99])
  assert.equal(rebuilt.session.phase, 'new')
  assert.ok(rebuilt.session.new_queue.includes(2))
  assert.equal(rebuilt.memory.get(2).wrong_count, 1)
  let c = answerNew(rebuilt, 2, false, TODAY)
  assert.equal(c.memory.get(2).wrong_count, 2)
  c = answerNew(c, 2, false, TODAY)
  assert.equal(c.memory.get(2).status, 1)
  assert.deepEqual(c.session.new_queue, [])
})
ok('复习答错后刷新重插保留', () => {
  let ctx = ensureSession([mem(1, 1, '2026-08-01', 4)], null, 10, ALL)
  ctx = answerReview(ctx, 1, false, TODAY)
  const rebuilt = ensureSession(toRows(ctx), ctx.session, 10, ALL)
  assert.ok(rebuilt.session.review_queue.includes(1))
  assert.equal(rebuilt.memory.get(1).wrong_count, 1)
})

console.log('阶段推进')
ok('复习清空→解锁新词→新词清空→done', () => {
  let ctx = ensureSession([mem(1, 1, '2026-08-01', 1)], null, 3, ALL)
  assert.equal(ctx.session.phase, 'review')
  ctx = answerReview(ctx, 1, true, TODAY)
  ctx = advancePhase(ctx, 3, ALL)
  assert.equal(ctx.session.phase, 'new')
  assert.ok(ctx.session.new_queue.length > 0)
  while (ctx.session.new_queue.length > 0) {
    const id = ctx.session.new_queue[0]
    ctx = answerNew(ctx, id, true, TODAY)
    ctx = advancePhase(ctx, 3, ALL)
  }
  assert.ok(isDayComplete(ctx))
})
ok('全部已掌握→立即 done', () => {
  const allLearned = [1, 2, 3].map((id) => mem(id, 2))
  const ctx = ensureSession(allLearned, null, 3, [1, 2, 3])
  assert.ok(isDayComplete(ctx))
})

console.log('继续学习（多轮）')
ok('完成一轮后可继续拉取下一批未学词，轮次+1', () => {
  // 词池 5 个，每日 3 个 → 第一轮学 1,2,3
  let ctx = ensureSession([], null, 3, [1, 2, 3, 4, 5])
  assert.deepEqual(ctx.session.new_queue, [1, 2, 3])
  while (ctx.session.new_queue.length > 0) {
    const id = ctx.session.new_queue[0]
    ctx = answerNew(ctx, id, true, TODAY)
    ctx = advancePhase(ctx, 3, [1, 2, 3, 4, 5])
  }
  assert.ok(isDayComplete(ctx))
  assert.equal(ctx.session.round, 0)
  assert.ok(hasUnlearned(toRows(ctx), [1, 2, 3, 4, 5]))
  // 继续 → 第 2 轮取 4,5
  ctx = continueLearning(ctx, 3, [1, 2, 3, 4, 5])
  assert.equal(ctx.session.round, 1)
  assert.equal(ctx.session.phase, 'new')
  assert.deepEqual(ctx.session.new_queue, [4, 5])
})
ok('词库全部学完后 hasUnlearned=false 且 continueLearning 直接 done', () => {
  const allLearned = [1, 2, 3].map((id) => mem(id, 1, '2026-08-02', 1))
  let ctx = ensureSession(allLearned, null, 3, [1, 2, 3])
  assert.ok(!hasUnlearned(toRows(ctx), [1, 2, 3]))
  ctx = continueLearning(ctx, 3, [1, 2, 3])
  assert.equal(ctx.session.phase, 'done')
})

console.log(`\n${passed} 组断言全部通过`)
