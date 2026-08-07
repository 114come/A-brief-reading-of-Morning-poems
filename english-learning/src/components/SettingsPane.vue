<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getSrsStats } from '@/api/english'
import { useAuthStore } from '@/stores/auth'
import { useOnboardingStore } from '@/stores/onboarding'
import { useSrsStore } from '@/stores/srs'
import { useUiStore } from '@/stores/ui'
import type { BookStats, SrsStats } from '@/types'

const srs = useSrsStore()
const auth = useAuthStore()
const ui = useUiStore()
const onboarding = useOnboardingStore()

const stats = ref<SrsStats | null>(null)

async function loadStats(): Promise<void> {
  if (auth.isLoggedIn) {
    try {
      stats.value = await getSrsStats()
    } catch {
      /* ignore */
    }
  }
}

function switchBook(bookId: number): void {
  srs.switchBook(bookId)
  ui.showToast('已切换到该词库')
  loadStats()
}

function updateDaily(n: number): void {
  srs.setSettings({ daily_new_words: n })
  ui.showToast(`每日新词已设为 ${n}`)
}

function updatePron(p: 'us' | 'uk'): void {
  srs.setSettings({ pronunciation: p })
  ui.showToast(p === 'us' ? '已切换美式发音' : '已切换英式发音')
}

function updateAutoplay(v: boolean): void {
  srs.setSettings({ autoplay: v })
  ui.showToast(v ? '已开启自动播放' : '已关闭自动播放')
}

async function resetData(): Promise<void> {
  if (!window.confirm('确定清除当前词库的学习数据吗？所有背诵记录、生词本和打卡都会被清空，回到全新状态。')) return
  await srs.resetCurrentBook()
  ui.showToast('学习数据已清除')
  loadStats()
}

function bookStatsOf(bookId: number): BookStats | undefined {
  return stats.value?.per_book.find((b) => b.book_id === bookId)
}

onMounted(async () => {
  await srs.init()
  loadStats()
})
</script>

<template>
  <div class="settings-grid">
    <!-- 词库切换 -->
    <div class="card card-pad">
      <div class="field-label">当前词库</div>
      <div class="book-list">
        <button
          v-for="b in srs.books"
          :key="b.id"
          type="button"
          class="book-item"
          :class="{ active: srs.bookId === b.id }"
          @click="switchBook(b.id)"
        >
          <span class="book-name">{{ b.name }}</span>
          <span v-if="srs.bookId === b.id" class="tag tag-primary">学习中</span>
          <span v-else class="book-count">{{ b.word_count }} 词</span>
        </button>
      </div>
      <p class="tip">切换词库：旧词库进度封存保留，新词库从头开始。</p>
    </div>

    <!-- 背诵参数 -->
    <div class="card card-pad">
      <div class="field-label">背诵参数</div>
      <div class="param-row">
        <span class="param-name">每日新词</span>
        <div class="param-options">
          <button
            v-for="n in [10, 20, 30, 50]"
            :key="n"
            type="button"
            class="num-btn"
            :class="{ active: srs.settings?.daily_new_words === n }"
            @click="updateDaily(n)"
          >
            {{ n }}
          </button>
        </div>
      </div>
      <div class="param-row">
        <span class="param-name">发音</span>
        <div class="param-options">
          <button type="button" class="num-btn" :class="{ active: srs.settings?.pronunciation === 'us' }" @click="updatePron('us')">美式</button>
          <button type="button" class="num-btn" :class="{ active: srs.settings?.pronunciation === 'uk' }" @click="updatePron('uk')">英式</button>
        </div>
      </div>
      <div class="param-row">
        <span class="param-name">自动播放</span>
        <button type="button" class="switch" :class="{ on: srs.settings?.autoplay }" @click="updateAutoplay(!srs.settings?.autoplay)">
          <span class="switch-knob"></span>
        </button>
      </div>
      <p class="tip">智能复习固定 1→2→4→7→15 天，走完标记已掌握。</p>
    </div>

    <!-- 词库统计 -->
    <div v-if="stats" class="card card-pad">
      <div class="field-label">学习统计</div>
      <div class="stat-mini-grid">
        <div class="stat-mini"><span class="num">{{ stats.total_studied }}</span><span class="lbl">累计背诵</span></div>
        <div class="stat-mini"><span class="num">{{ stats.mastered_count }}</span><span class="lbl">已掌握</span></div>
        <div class="stat-mini"><span class="num" style="color: var(--success)">{{ stats.streak_days }}</span><span class="lbl">连续打卡</span></div>
      </div>
      <div class="book-stats">
        <div v-for="b in srs.books" :key="b.id" class="book-stat-row">
          <span class="bs-name">{{ b.name }}</span>
          <div class="bs-track">
            <div
              class="bs-fill"
              :style="{ width: Math.round(((bookStatsOf(b.id)?.learning || 0) + (bookStatsOf(b.id)?.mastered || 0)) / Math.max(bookStatsOf(b.id)?.total_words || 1, 1) * 100) + '%' }"
            ></div>
          </div>
          <span class="bs-num">
            {{ (bookStatsOf(b.id)?.mastered || 0) }}/{{ bookStatsOf(b.id)?.total_words || 0 }}
          </span>
        </div>
      </div>
    </div>

    <!-- 危险操作 -->
    <div class="card card-pad danger-card">
      <div class="field-label" style="color: var(--danger)">危险操作</div>
      <p class="tip">清除后等同于变回全新用户状态，无法恢复。</p>
      <button class="btn btn-danger-soft" type="button" @click="resetData">清除当前词库学习数据</button>
    </div>
  </div>
</template>

<style scoped>
.settings-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 760px;
}

.book-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.book-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border: 1px solid var(--border-2);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  transition: all 0.18s ease;
}

.book-item.active {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.book-count {
  font-size: 12px;
  color: var(--text-3);
}

.tip {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-3);
}

.param-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.param-name {
  font-size: 14px;
}

.param-options {
  display: flex;
  gap: 6px;
}

.num-btn {
  padding: 7px 16px;
  border: 1px solid var(--border-2);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-2);
  font-size: 13px;
}

.num-btn.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 600;
}

.switch {
  width: 46px;
  height: 26px;
  border-radius: 999px;
  border: none;
  background: var(--border-2);
  position: relative;
  transition: background 0.2s ease;
}

.switch.on {
  background: var(--primary);
}

.switch-knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  transition: left 0.2s ease;
}

.switch.on .switch-knob {
  left: 23px;
}

.stat-mini-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.stat-mini {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px;
  background: var(--surface-2);
  border-radius: 10px;
}

.stat-mini .num {
  font-size: 22px;
  font-weight: 800;
  color: var(--primary);
}

.stat-mini .lbl {
  font-size: 12px;
  color: var(--text-2);
}

.book-stats {
  margin-top: 16px;
}

.book-stat-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.bs-name {
  width: 64px;
  font-size: 13px;
  color: var(--text-2);
  flex-shrink: 0;
}

.bs-track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  overflow: hidden;
}

.bs-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--brand-gradient);
}

.bs-num {
  font-size: 12px;
  color: var(--text-2);
  min-width: 60px;
  text-align: right;
}

.danger-card {
  border-color: var(--danger-soft);
}
</style>
