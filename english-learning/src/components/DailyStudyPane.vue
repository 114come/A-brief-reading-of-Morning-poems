<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Library, RefreshCw, Sparkles, Target } from 'lucide-vue-next'
import { useSrsStore } from '@/stores/srs'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { useDailySummaryStore } from '@/stores/dailySummary'
import { categoryName, WORD_CATEGORIES } from '@/types'
import WordCard from './WordCard.vue'
import SummaryModal from './SummaryModal.vue'

const srs = useSrsStore()
const ui = useUiStore()
const auth = useAuthStore()
const summary = useDailySummaryStore()

const answering = ref(false)
const started = ref(false)
const showSummary = ref(false)

// 背单词计时（埋点）
let studySec = 0
let studyTimer: ReturnType<typeof setInterval> | null = null
function startStudyTimer(): void {
  if (studyTimer || !auth.isLoggedIn) return
  studyTimer = setInterval(() => {
    if (document.visibilityState === 'visible') studySec += 1
  }, 1000)
}
function flushStudySec(): void {
  if (studySec > 0 && auth.isLoggedIn) {
    void summary.report({ word_study_sec: studySec })
    studySec = 0
  }
}
function stopStudyTimer(): void {
  if (studyTimer) {
    clearInterval(studyTimer)
    studyTimer = null
  }
  flushStudySec()
}

const phase = computed(() => srs.session?.phase ?? 'new')
const current = computed(() => srs.currentWord())

const reviewTotal = computed(() => {
  if (!srs.session) return 0
  return srs.session.review_done + srs.session.review_queue.length
})

const newTotal = computed(() => {
  if (!srs.session) return 0
  return srs.session.new_done + srs.session.new_queue.length
})

const reviewDone = computed(() => srs.session?.review_done ?? 0)
const newDone = computed(() => srs.session?.new_done ?? 0)
const reviewPct = computed(() => (reviewTotal.value ? Math.round((reviewDone.value / reviewTotal.value) * 100) : 100))
const newPct = computed(() => (newTotal.value ? Math.round((newDone.value / newTotal.value) * 100) : 0))

function start(): void {
  void srs.startDay().finally(() => {
    started.value = true
    startStudyTimer()
  })
}

function setCategory(tag: string | null): void {
  srs.setStudyTag(tag)
  ui.showToast(tag ? `已切换到「${categoryName(tag)}」` : '已切换到「全部」')
}

/** 学习中切换分类：立即按新分类重建本轮新词队列（已答单词状态保留） */
function changeCategory(tag: string | null): void {
  srs.setStudyTag(tag)
  void srs.rebuildNewBatch()
  ui.showToast(tag ? `已切换到「${categoryName(tag)}」，重新选词` : '已切换到「全部」，重新选词')
}

async function handleAnswer(known: boolean): Promise<void> {
  if (answering.value) return
  answering.value = true
  try {
    await srs.answer(known)
    if (srs.session?.phase === 'done') {
      await new Promise((r) => setTimeout(r, 400))
      showSummary.value = true
    }
  } finally {
    answering.value = false
  }
}

function closeSummary(): void {
  showSummary.value = false
}

async function handleContinue(): Promise<void> {
  showSummary.value = false
  await srs.continueRound()
  started.value = true
}

onMounted(async () => {
  await srs.init()
})

onBeforeUnmount(() => {
  stopStudyTimer()
})

// 初始化完成后若已引导，立即开始当日
watch(
  () => [srs.initialized, srs.onboarded] as const,
  ([init, onb]) => {
    if (init && onb) start()
  },
  { immediate: true },
)
</script>

<template>
  <div>
    <!-- 加载中 -->
    <div v-if="!srs.initialized" class="empty">加载中…</div>

    <!-- 未引导：提示去设置词库 -->
    <div v-else-if="!srs.onboarded" class="empty">
      <div class="empty-icon"><Target :size="28" :stroke-width="1.6" /></div>
      <div class="empty-text">先完成学习目标设置，开始你的背单词计划</div>
    </div>

    <!-- 今日已完成 -->
    <div v-else-if="phase === 'done' && !showSummary" class="card card-pad daily-done">
      <div class="empty-icon"><Sparkles :size="28" :stroke-width="1.6" /></div>
      <div class="done-title">今日学习已完成</div>
      <div class="done-sub">
        本轮复习 {{ srs.session?.review_done || 0 }} 个 · 新词 {{ srs.session?.new_done || 0 }} 个
      </div>
      <div class="done-cats">
        <span class="cat-label">学习类型</span>
        <button type="button" class="cat-chip" :class="{ active: srs.selectedTag === null }" @click="setCategory(null)">全部</button>
        <button
          v-for="c in WORD_CATEGORIES"
          :key="c.tag"
          type="button"
          class="cat-chip"
          :class="{ active: srs.selectedTag === c.tag }"
          @click="setCategory(c.tag)"
        >
          {{ c.name }}
        </button>
      </div>
      <div class="done-actions">
        <button v-if="srs.canContinue" class="btn btn-primary" type="button" @click="handleContinue">
          继续学一轮 →
        </button>
        <button class="btn btn-ghost" type="button" @click="showSummary = true">查看今日总结</button>
      </div>
    </div>

    <!-- 未开始：今日概览 + 分类选择 + 开始按钮 -->
    <div v-else-if="!started" class="card card-pad daily-start">
      <div class="empty-icon"><Library :size="28" :stroke-width="1.6" /></div>
      <div class="start-title">{{ srs.currentBook?.name }} · 每日学习</div>
      <div class="start-stats">
        <span v-if="reviewTotal > 0" class="tag tag-primary">待复习 {{ reviewTotal }}</span>
        <span class="tag tag-success">今日新词 {{ srs.dailyNewWords }}</span>
      </div>

      <div class="start-cats">
        <span class="cat-label">学习类型</span>
        <button type="button" class="cat-chip" :class="{ active: srs.selectedTag === null }" @click="setCategory(null)">
          全部
        </button>
        <button
          v-for="c in WORD_CATEGORIES"
          :key="c.tag"
          type="button"
          class="cat-chip"
          :class="{ active: srs.selectedTag === c.tag }"
          @click="setCategory(c.tag)"
        >
          {{ c.name }}
        </button>
      </div>

      <div class="start-desc">
        {{ srs.selectedTag ? `正在背「${categoryName(srs.selectedTag)}」词汇` : '背诵全部词汇' }} · 先复习到期旧词，再学习新词。
      </div>
      <button class="btn btn-primary start-btn" type="button" @click="start">
        {{ reviewTotal > 0 ? '开始复习' : '开始背诵' }}
      </button>
    </div>

    <!-- 学习中：进度 + 单词卡 -->
    <template v-else>
      <div class="study-progress card card-pad">
        <div class="progress-line">
          <span class="prog-label">复习</span>
          <div class="prog-track"><div class="prog-fill review" :style="{ width: reviewPct + '%' }"></div></div>
          <span class="prog-num">{{ reviewDone }}/{{ reviewTotal }}</span>
        </div>
        <div v-if="phase === 'new' || (phase === 'review' && reviewTotal === 0)" class="progress-line">
          <span class="prog-label">新词</span>
          <div class="prog-track"><div class="prog-fill new" :style="{ width: newPct + '%' }"></div></div>
          <span class="prog-num">{{ newDone }}/{{ newTotal }}</span>
        </div>
        <div v-if="phase === 'review'" class="phase-tip">
          <RefreshCw :size="13" :stroke-width="2" style="vertical-align: -2px; margin-right: 4px" />
          复习阶段 — 全部复习完解锁新词
        </div>
        <div v-else-if="phase === 'new'" class="phase-tip">
          <Sparkles :size="13" :stroke-width="2" style="vertical-align: -2px; margin-right: 4px" />
          新词阶段 · 第 {{ (srs.session?.round ?? 0) + 1 }} 轮
          <span v-if="srs.selectedTag" class="phase-cat">（{{ categoryName(srs.selectedTag) }}）</span>
        </div>
        <div class="study-cats">
          <span class="cat-label">类型</span>
          <button type="button" class="cat-chip" :class="{ active: srs.selectedTag === null }" @click="changeCategory(null)">全部</button>
          <button
            v-for="c in WORD_CATEGORIES"
            :key="c.tag"
            type="button"
            class="cat-chip"
            :class="{ active: srs.selectedTag === c.tag }"
            @click="changeCategory(c.tag)"
          >
            {{ c.name }}
          </button>
        </div>
      </div>

      <div v-if="current" style="margin-top: 16px">
        <WordCard
          :word="current"
          :pronunciation="srs.settings?.pronunciation"
          :autoplay="srs.settings?.autoplay"
          @answer="handleAnswer"
        />
      </div>
      <div v-else-if="phase !== 'done'" class="empty">准备中…</div>
    </template>

    <!-- 今日总结弹窗 -->
    <SummaryModal
      v-if="showSummary && srs.completeResult"
      :result="srs.completeResult"
      :is-guest="!auth.isLoggedIn"
      :can-continue="srs.canContinue"
      @close="closeSummary"
      @continue="handleContinue"
    />
  </div>
</template>

<style scoped>
.daily-start,
.daily-done {
  max-width: 560px;
  margin: 0 auto;
  text-align: center;
  padding: 44px 40px;
}

.start-title,
.done-title {
  font-size: var(--fs-xl);
  font-weight: 600;
  margin-top: 12px;
}

.start-stats {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 14px;
}

.start-cats,
.done-cats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.cat-label {
  font-size: 13px;
  color: var(--text-2);
}

.cat-chip {
  padding: 5px 14px;
  border: 1px solid var(--border-2);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text-2);
  font-size: 13px;
  transition: all 0.18s ease;
}

.cat-chip.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 600;
}

.phase-cat {
  color: var(--text-3);
  font-size: 13px;
}

.start-desc,
.done-sub {
  margin-top: 10px;
  font-size: 14px;
  color: var(--text-2);
}

.done-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

.start-btn {
  margin-top: 22px;
  height: 46px;
  padding: 0 44px;
  font-size: 16px;
}

/* 进度 */
.study-progress {
  max-width: 620px;
  margin: 0 auto;
}

.progress-line {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.prog-label {
  width: 34px;
  font-size: 13px;
  color: var(--text-2);
  flex-shrink: 0;
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
  transition: width 0.3s ease;
}

.prog-fill.review {
  background: linear-gradient(90deg, var(--sage), var(--accent));
}

.prog-fill.new {
  background: var(--brand-gradient);
}

.prog-num {
  font-size: 12px;
  color: var(--text-2);
  min-width: 44px;
  text-align: right;
}

.phase-tip {
  font-size: 13px;
  color: var(--text-2);
  margin-top: 4px;
}
</style>
