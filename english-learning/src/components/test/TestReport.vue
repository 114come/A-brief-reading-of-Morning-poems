<script setup lang="ts">
import { computed } from 'vue'
import { BarChart3, Check, Sparkles } from 'lucide-vue-next'
import type { TestQuestion } from '@/types'

export interface TestRecord {
  question: TestQuestion
  userAnswer: string
  correct: boolean
  usedHint: boolean
}

const props = defineProps<{
  records: TestRecord[]
}>()

const emit = defineEmits<{
  (e: 'addWrong'): void
  (e: 'retry'): void
}>()

const total = computed(() => props.records.length)
const correctCount = computed(() => props.records.filter((r) => r.correct).length)
const accuracy = computed(() => (total.value ? Math.round((correctCount.value / total.value) * 100) : 0))
const wrong = computed(() => props.records.filter((r) => !r.correct))

// 分题型正确率
const byType = computed(() => {
  const map = new Map<string, { total: number; correct: number; label: string }>()
  for (const r of props.records) {
    const t = r.question.type
    if (!map.has(t)) map.set(t, { total: 0, correct: 0, label: typeLabel(t) })
    const e = map.get(t)!
    e.total += 1
    if (r.correct) e.correct += 1
  }
  return [...map.values()]
})

function typeLabel(t: string): string {
  return { a: '英译中', b: '中译英', c: '听音选义', d: '单词填空', e: '例句填空' }[t] ?? t
}

function showPrompt(q: TestQuestion): string {
  if (q.type === 'a' || q.type === 'c') return q.word + (q.phonetic ? ' ' + q.phonetic : '')
  if (q.type === 'b') return q.definition
  if (q.type === 'd') return q.definition + ' → ' + q.mask
  if (q.type === 'e') return (q.example_cn || q.definition) + '（' + q.word + '）'
  return q.word
}

function userAnswerText(r: TestRecord): string {
  return r.userAnswer || '（未作答）'
}
</script>

<template>
  <div class="report">
    <div class="report-head card card-pad">
      <div class="report-title">
        <BarChart3 :size="19" :stroke-width="1.8" style="vertical-align: -4px; margin-right: 6px" />
        测试报告
      </div>
      <div class="report-stats">
        <div class="stat-item"><span class="num">{{ total }}</span><span class="lbl">总题量</span></div>
        <div class="stat-item"><span class="num ok">{{ correctCount }}</span><span class="lbl">答对</span></div>
        <div class="stat-item"><span class="num wrong">{{ total - correctCount }}</span><span class="lbl">答错</span></div>
        <div class="stat-item"><span class="num" :style="{ color: accuracy >= 60 ? 'var(--success)' : 'var(--danger)' }">{{ accuracy }}%</span><span class="lbl">正确率</span></div>
      </div>
    </div>

    <!-- 分题型正确率 -->
    <div v-if="byType.length > 1" class="card card-pad" style="margin-top: 14px">
      <div class="sub-title">分题型正确率</div>
      <div class="type-rows">
        <div v-for="t in byType" :key="t.label" class="type-row">
          <span class="type-label">{{ t.label }}</span>
          <div class="type-track">
            <div class="type-fill" :style="{ width: (t.total ? Math.round((t.correct / t.total) * 100) : 0) + '%' }"></div>
          </div>
          <span class="type-num">{{ t.correct }}/{{ t.total }}</span>
        </div>
      </div>
    </div>

    <!-- 错题列表 -->
    <div class="card card-pad" style="margin-top: 14px">
      <div class="sub-title">错题（{{ wrong.length }}）</div>
      <div v-if="wrong.length === 0" class="no-wrong">
        <Sparkles :size="16" :stroke-width="2" style="vertical-align: -3px; margin-right: 6px" />
        全部答对，太棒了！
      </div>
      <div v-for="(r, i) in wrong" :key="i" class="wrong-item">
        <div class="wrong-q">{{ showPrompt(r.question) }}</div>
        <div class="wrong-ans">
          <span class="ans-label">你的答案</span>
          <span class="ans-user">
            <Check v-if="r.correct" :size="14" :stroke-width="2.5" class="ans-check" />
            <template v-else>{{ userAnswerText(r) }}</template>
          </span>
        </div>
        <div class="wrong-ans">
          <span class="ans-label">正确答案</span><span class="ans-correct">{{ r.question.answer }}</span>
        </div>
        <div v-if="r.usedHint" class="wrong-hint">使用了提示</div>
      </div>
    </div>

    <div class="report-actions">
      <button v-if="wrong.length" class="btn btn-primary" type="button" @click="emit('addWrong')">
        将 {{ wrong.length }} 个错题加入生词本
      </button>
      <button class="btn btn-ghost" type="button" @click="emit('retry')">再测一组</button>
    </div>
  </div>
</template>

<style scoped>
.report {
  max-width: 680px;
  margin: 0 auto;
}

.report-title {
  font-size: 20px;
  font-weight: 800;
  margin-bottom: 16px;
}

.report-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px;
  background: var(--surface-2);
  border-radius: 10px;
}

.stat-item .num {
  font-size: 26px;
  font-weight: 800;
  color: var(--primary);
}

.stat-item .num.ok {
  color: var(--success);
}

.stat-item .num.wrong {
  color: var(--danger);
}

.stat-item .lbl {
  font-size: 12px;
  color: var(--text-2);
  margin-top: 2px;
}

.sub-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 12px;
}

.type-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.type-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.type-label {
  width: 60px;
  font-size: 13px;
  color: var(--text-2);
}

.type-track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  overflow: hidden;
}

.type-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--brand-gradient);
}

.type-num {
  font-size: 12px;
  color: var(--text-2);
  min-width: 44px;
  text-align: right;
}

.no-wrong {
  padding: 30px;
  text-align: center;
  font-size: 15px;
  color: var(--success);
}

.ans-check {
  color: var(--success);
  vertical-align: -2px;
}

.wrong-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}

.wrong-item:last-child {
  border-bottom: none;
}

.wrong-q {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

.wrong-ans {
  margin-top: 4px;
  font-size: 13px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.ans-label {
  color: var(--text-3);
  width: 56px;
  flex-shrink: 0;
}

.ans-user {
  color: var(--danger);
}

.ans-correct {
  color: var(--success);
  font-weight: 600;
}

.wrong-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--accent);
}

.report-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}
</style>
