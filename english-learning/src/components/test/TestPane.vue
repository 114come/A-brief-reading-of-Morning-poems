<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Lock } from 'lucide-vue-next'
import { getTestQuestions } from '@/api/english'
import { useAuthStore } from '@/stores/auth'
import { useSrsStore } from '@/stores/srs'
import { useUiStore } from '@/stores/ui'
import { useDailySummaryStore } from '@/stores/dailySummary'
import type { TestQuestion } from '@/types'
import McQuestion from './McQuestion.vue'
import FillQuestion from './FillQuestion.vue'
import TestReport, { type TestRecord } from './TestReport.vue'

const srs = useSrsStore()
const auth = useAuthStore()
const ui = useUiStore()
const dailySummary = useDailySummaryStore()

const CHOICE_TYPES = [
  { value: 'a', label: '英译中' },
  { value: 'b', label: '中译英' },
  { value: 'c', label: '听音选义' },
]
const FILL_TYPES = [
  { value: 'd', label: '单词填空' },
  { value: 'e', label: '例句填空' },
]

// 模块 + 题型
const module = ref<'choice' | 'fill'>('choice')
const qTypes = computed(() => (module.value === 'choice' ? CHOICE_TYPES : FILL_TYPES))
const questionType = ref<'a' | 'b' | 'c' | 'd' | 'e'>('a')

// 出题模式
const mode = ref<'today' | 'book' | 'wordbook' | 'reading_new'>('book')
const MODES = [
  { value: 'today', label: '当日学习测试', desc: '今日新词+复习词' },
  { value: 'book', label: '词库专项测试', desc: '当前词库学习中单词' },
  { value: 'wordbook', label: '生词本薄弱测试', desc: '生词本内单词' },
  { value: 'reading_new', label: '今日阅读生词专项训练', desc: '当日阅读中的生词' },
]
const todayDone = computed(() => srs.session?.phase === 'done')

// 题量（词库专项才有）
const count = ref(20)
const counts = [20, 50, 100]

// 测试状态
const phase = ref<'config' | 'testing' | 'report'>('config')
const loading = ref(false)
const questions = ref<TestQuestion[]>([])
const currentIdx = ref(0)
const records = ref<TestRecord[]>([])
const reported = ref(false)

const current = computed(() => questions.value[currentIdx.value])

function switchModule(m: 'choice' | 'fill'): void {
  if (module.value === m) return
  module.value = m
  questionType.value = m === 'choice' ? 'a' : 'd'
  resetToConfig()
}

function resetToConfig(): void {
  phase.value = 'config'
  questions.value = []
  records.value = []
  currentIdx.value = 0
  reported.value = false
}

function selectQType(v: string): void {
  questionType.value = v as TestQuestion['type']
}

async function start(): Promise<void> {
  if (mode.value === 'today' && !todayDone.value) {
    ui.showToast('请先完成今日背诵')
    return
  }
  loading.value = true
  try {
    // reading_new 模式后端忽略 book_id（取当日阅读生词），未 onboarding 时兜底 0
    const bookId = mode.value === 'reading_new' ? (srs.bookId ?? 0) : srs.bookId!
    const res = await getTestQuestions({
      book_id: bookId,
      module: module.value,
      question_type: questionType.value,
      mode: mode.value,
      count: mode.value === 'book' ? count.value : 20,
    })
    questions.value = res.questions
    if (res.questions.length === 0) {
      ui.showToast('该模式下暂无可用单词')
      return
    }
    records.value = []
    currentIdx.value = 0
    phase.value = 'testing'
  } catch (e) {
    ui.showToast((e as Error).message || '出题失败')
  } finally {
    loading.value = false
  }
}

async function handleMcAnswer(correct: boolean): Promise<void> {
  await recordAndAdvance(correct, '')
}

async function handleFillAnswer(correct: boolean, userAnswer: string, usedHint: boolean): Promise<void> {
  await recordAndAdvance(correct, userAnswer, usedHint)
}

async function recordAndAdvance(correct: boolean, userAnswer: string, usedHint = false): Promise<void> {
  const q = current.value
  if (!q) return
  records.value.push({ question: q, userAnswer, correct, usedHint })
  // 记忆影响：答对推进 / 答错惩罚（填空错题置顶）
  try {
    await srs.applyTestAnswer(q.word_id, correct, module.value === 'fill')
  } catch (e) {
    ui.showToast('记忆更新失败: ' + (e as Error).message)
  }
  if (currentIdx.value + 1 < questions.value.length) {
    currentIdx.value += 1
  } else {
    phase.value = 'report'
    // 埋点：测试完成上报（单选/填空各自题数 + 答对数）
    const correctCount = records.value.filter((r) => r.correct).length
    const qCount = records.value.length
    if (auth.isLoggedIn && qCount > 0 && !reported.value) {
      reported.value = true
      const payload =
        module.value === 'choice'
          ? { test_choice_questions: qCount, test_choice_correct: correctCount }
          : { test_fill_questions: qCount, test_fill_correct: correctCount }
      await dailySummary.report(payload)
    }
  }
}

async function addWrongToWordbook(): Promise<void> {
  if (!auth.requireAuth()) return
  const wrong = records.value.filter((r) => !r.correct)
  for (const r of wrong) {
    await srs.applyTestAnswer(r.question.word_id, false, true)
  }
  ui.showToast(`已将 ${wrong.length} 个错题加入生词本`)
}

function retry(): void {
  resetToConfig()
}

onMounted(async () => {
  await srs.init()
})

watch(mode, () => resetToConfig())
</script>

<template>
  <div>
    <!-- 配置阶段 -->
    <div v-if="phase === 'config'" class="test-config">
      <!-- 模块 Tab -->
      <div class="module-tabs">
        <button type="button" class="module-tab" :class="{ active: module === 'choice' }" @click="switchModule('choice')">
          单选测试模块
        </button>
        <button type="button" class="module-tab" :class="{ active: module === 'fill' }" @click="switchModule('fill')">
          填空测试模块
        </button>
      </div>

      <div class="card card-pad">
        <div class="field-label">出题模式</div>
        <div class="mode-list">
          <button
            v-for="m in MODES"
            :key="m.value"
            type="button"
            class="mode-btn"
            :class="{ active: mode === m.value, disabled: m.value === 'today' && !todayDone }"
            @click="mode = m.value as typeof mode"
          >
            <div class="mode-name">{{ m.label }}</div>
            <div class="mode-desc">{{ m.desc }}</div>
            <div v-if="m.value === 'today' && !todayDone" class="mode-lock">
              <Lock :size="12" :stroke-width="2" style="vertical-align: -2px; margin-right: 3px" />
              需先完成今日背诵
            </div>
          </button>
        </div>

        <div class="field-label" style="margin-top: 18px">题型</div>
        <div class="qtype-row">
          <button
            v-for="t in qTypes"
            :key="t.value"
            type="button"
            class="qtype-btn"
            :class="{ active: questionType === t.value }"
            @click="selectQType(t.value)"
          >
            {{ t.label }}
          </button>
        </div>

        <div v-if="mode === 'book'" class="field-label" style="margin-top: 18px">题量</div>
        <div v-if="mode === 'book'" class="count-row">
          <button
            v-for="c in counts"
            :key="c"
            type="button"
            class="qtype-btn"
            :class="{ active: count === c }"
            @click="count = c"
          >
            {{ c }}
          </button>
        </div>

        <button class="btn btn-primary start-test-btn" type="button" :disabled="loading" @click="start">
          {{ loading ? '出题中…' : '开始测试' }}
        </button>
      </div>
    </div>

    <!-- 测试中 -->
    <div v-else-if="phase === 'testing' && current">
      <div class="test-progress">
        <span class="prog-text">第 {{ currentIdx + 1 }} / {{ questions.length }} 题</span>
        <div class="prog-track">
          <div class="prog-fill" :style="{ width: ((currentIdx) / questions.length) * 100 + '%' }"></div>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" @click="resetToConfig">退出测试</button>
      </div>

      <div style="margin-top: 16px">
        <McQuestion
          v-if="module === 'choice'"
          :key="current.word_id"
          :question="current"
          @answer="handleMcAnswer"
        />
        <FillQuestion
          v-else
          :key="current.word_id"
          :question="current"
          @answer="handleFillAnswer"
        />
      </div>
    </div>

    <!-- 报告 -->
    <div v-else-if="phase === 'report'" style="margin-top: 8px">
      <TestReport
        :records="records"
        @add-wrong="addWrongToWordbook"
        @retry="retry"
      />
    </div>
  </div>
</template>

<style scoped>
.test-config {
  max-width: 720px;
}

.module-tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  width: fit-content;
  margin-bottom: 16px;
}

.module-tab {
  padding: 8px 22px;
  border-radius: 9px;
  border: none;
  background: transparent;
  color: var(--text-2);
  font-size: 14px;
  transition: all 0.18s ease;
}

.module-tab.active {
  background: var(--surface);
  color: var(--primary);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.mode-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mode-btn {
  display: block;
  text-align: left;
  padding: 12px 16px;
  border: 1px solid var(--border-2);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  transition: all 0.15s ease;
}

.mode-btn.active {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.mode-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-name {
  font-size: 15px;
  font-weight: 600;
}

.mode-desc {
  font-size: 12px;
  color: var(--text-2);
  margin-top: 2px;
}

.mode-lock {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  color: var(--accent);
  margin-top: 2px;
}

.qtype-row,
.count-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.qtype-btn {
  padding: 8px 18px;
  border: 1px solid var(--border-2);
  border-radius: 9px;
  background: var(--surface);
  color: var(--text-2);
  font-size: 14px;
  transition: all 0.15s ease;
}

.qtype-btn.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 600;
}

.start-test-btn {
  width: 100%;
  height: 44px;
  margin-top: 22px;
  font-size: 15px;
}

.test-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 620px;
  margin: 0 auto;
}

.prog-text {
  font-size: 13px;
  color: var(--text-2);
  min-width: 80px;
}

.prog-track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  overflow: hidden;
}

.prog-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--brand-gradient);
  transition: width 0.3s ease;
}
</style>
