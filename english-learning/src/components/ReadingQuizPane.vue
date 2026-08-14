<script setup lang="ts">
import { computed, ref } from 'vue'
import { getReadingQuiz, submitReadingQuiz } from '@/api/english'
import { useRewardCollect } from '@/composables/rewardCollect'
import { useUiStore } from '@/stores/ui'
import type { ReadingQuizQuestion } from '@/types'
import McQuestion from './test/McQuestion.vue'
import FillQuestion from './test/FillQuestion.vue'

const props = defineProps<{
  articleId: number
}>()

const emit = defineEmits<{
  (e: 'done'): void
}>()

const ui = useUiStore()
const { collectAndNotify } = useRewardCollect()

type Phase = 'idle' | 'loading' | 'quiz' | 'done'
const phase = ref<Phase>('idle')
const questions = ref<ReadingQuizQuestion[]>([])
const idx = ref(0)
const answers = ref<{ word: string; type: string; correct: boolean; definition: string }[]>([])
const result = ref<{ correct: number; total: number } | null>(null)

const current = computed(() => questions.value[idx.value])
const choiceQ = computed(() => current.value && ['a', 'b', 'c'].includes(current.value.type))
const accuracy = computed(() =>
  result.value && result.value.total
    ? Math.round((result.value.correct * 100) / result.value.total)
    : 0,
)
const wrongWords = computed(() => {
  const wrong = answers.value.filter((a) => !a.correct).map((a) => a.word)
  return wrong
})

async function start(): Promise<void> {
  phase.value = 'loading'
  answers.value = []
  result.value = null
  try {
    const res = await getReadingQuiz(props.articleId)
    questions.value = res.questions
    if (!res.questions.length) {
      ui.showToast('今日暂无足够词汇出题')
      phase.value = 'idle'
      return
    }
    idx.value = 0
    phase.value = 'quiz'
  } catch (e) {
    ui.showToast((e as Error).message || '出题失败')
    phase.value = 'idle'
  }
}

function onMcAnswer(correct: boolean): void {
  record(correct)
}

function onFillAnswer(correct: boolean): void {
  record(correct)
}

function record(correct: boolean): void {
  const q = current.value
  if (!q) return
  answers.value.push({ word: q.word, type: q.type, correct, definition: q.definition })
  if (idx.value + 1 < questions.value.length) {
    idx.value += 1
  } else {
    void submit()
  }
}

async function submit(): Promise<void> {
  phase.value = 'loading'
  try {
    const res = await submitReadingQuiz(props.articleId, answers.value)
    result.value = { correct: res.correct, total: res.total }
    phase.value = 'done'
    emit('done')
    // 结算当日奖励积分（小测及格任务，幂等；后端按正确率判定达标）
    await collectAndNotify()
  } catch (e) {
    ui.showToast((e as Error).message || '提交失败')
    // 恢复作答态，允许重试
    phase.value = answers.value.length < questions.value.length ? 'quiz' : 'done'
  }
}

function retry(): void {
  void start()
}
</script>

<template>
  <div class="quiz-pane card card-pad">
    <div class="quiz-head">
      <div class="quiz-title">今日小测 · 文章词汇</div>
      <span class="quiz-sub">{{ questions.length ? `${questions.length} 题 · 轻量热身` : '4-6 题随机' }}</span>
    </div>

    <!-- 未开始 -->
    <div v-if="phase === 'idle'" class="quiz-empty">
      <p>读完全文，用 4-6 道小题检验理解，答错词汇自动进入生词库。</p>
      <button class="btn btn-primary" type="button" @click="start">开始小测</button>
    </div>

    <!-- 加载 / 出题 -->
    <div v-else-if="phase === 'loading'" class="quiz-empty">加载中…</div>

    <!-- 答题 -->
    <div v-else-if="phase === 'quiz' && current" class="quiz-body">
      <div class="quiz-progress">第 {{ idx + 1 }} / {{ questions.length }} 题</div>
      <McQuestion v-if="choiceQ" :key="current.word + current.type" :question="current" autoplay @answer="onMcAnswer" />
      <FillQuestion v-else :key="current.word + current.type" :question="current" @answer="onFillAnswer" />
    </div>

    <!-- 结果 -->
    <div v-else-if="phase === 'done' && result" class="quiz-result">
      <div class="result-big">{{ accuracy }}%</div>
      <div class="result-sub">答对 {{ result.correct }} / {{ result.total }} 题</div>
      <div v-if="wrongWords.length" class="result-wrong">
        <div class="result-label">本次错词（已自动加入生词库）</div>
        <div class="wrong-chips">
          <span v-for="w in wrongWords" :key="w" class="wrong-chip">{{ w }}</span>
        </div>
      </div>
      <button class="btn btn-ghost btn-sm" type="button" @click="retry">再测一次</button>
    </div>
  </div>
</template>

<style scoped>
.quiz-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.quiz-title {
  font-size: 16px;
  font-weight: 700;
}

.quiz-sub {
  font-size: 12px;
  color: var(--text-3);
}

.quiz-empty {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  color: var(--text-2);
  padding: 12px 0 8px;
}

.quiz-progress {
  text-align: center;
  font-size: 13px;
  color: var(--text-3);
  margin-bottom: 14px;
}

.quiz-result {
  margin-top: 16px;
  text-align: center;
}

.result-big {
  font-size: 44px;
  font-weight: 800;
  color: var(--primary);
}

.result-sub {
  margin-top: 4px;
  color: var(--text-2);
}

.result-wrong {
  margin: 16px auto 4px;
  max-width: 420px;
}

.result-label {
  font-size: 13px;
  color: var(--text-3);
  margin-bottom: 8px;
}

.wrong-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.wrong-chip {
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 13px;
  font-weight: 600;
}
</style>
