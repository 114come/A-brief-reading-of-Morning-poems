<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getStudyStats } from '@/api/english'
import { useUiStore } from '@/stores/ui'
import type { StudyStats } from '@/types'
import PageTabs from '@/components/PageTabs.vue'
import CheckinPane from '@/components/CheckinPane.vue'
import DailySummaryPane from '@/components/DailySummaryPane.vue'

const ui = useUiStore()
const route = useRoute()

// 支持 ?tab=summary 直达
const initialTab = route.query.tab as string | undefined
const activeTab = ref(initialTab && ['checkin', 'overview', 'summary'].includes(initialTab) ? initialTab : 'checkin')
const tabs = [
  { key: 'checkin', label: '每日打卡', requiresLogin: true },
  { key: 'overview', label: '学习数据总览', requiresLogin: true },
  { key: 'summary', label: 'AI 学习日报', requiresLogin: true },
]

const loading = ref(false)
const stats = ref<StudyStats | null>(null)

const statItems = [
  { key: 'wordbook_count', label: '生词本词汇', suffix: '个' },
  { key: 'mastered_count', label: '已掌握词汇', suffix: '个' },
  { key: 'favorite_count', label: '收藏内容', suffix: '条' },
  { key: 'note_count', label: '阅读笔记', suffix: '篇' },
  { key: 'checkin_total', label: '累计打卡', suffix: '天' },
  { key: 'checkin_streak', label: '连续打卡', suffix: '天' },
] as const

async function loadStats(): Promise<void> {
  loading.value = true
  try {
    stats.value = await getStudyStats()
  } catch {
    ui.showToast('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

function onTabChange(): void {
  if (activeTab.value === 'overview' && !stats.value) loadStats()
}

onMounted(() => {
  if (activeTab.value === 'overview') loadStats()
})
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <h1 class="page-title">归处</h1>
        <p class="page-desc">打卡坚持 + 数据洞察，让努力看得见</p>
      </div>
    </div>

    <PageTabs v-model="activeTab" :tabs="tabs" @update:model-value="onTabChange" />

    <CheckinPane v-if="activeTab === 'checkin'" />
    <DailySummaryPane v-else-if="activeTab === 'summary'" />

    <div v-else>
      <div v-if="loading" class="empty">加载中…</div>

      <div v-else-if="stats" class="overview-wrap">
        <div class="stat-grid overview-grid">
          <div v-for="item in statItems" :key="item.key" class="stat-card">
            <div class="stat-num">{{ stats[item.key] }}<span class="suffix">{{ item.suffix }}</span></div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
        </div>

        <div class="card card-pad" style="margin-top: 16px">
          <div class="field-label">词库覆盖</div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: Math.min(100, Math.round((stats.mastered_count / Math.max(stats.total_words, 1)) * 100)) + '%' }"></div>
          </div>
          <p class="progress-tip">当前词库共 {{ stats.total_words }} 个单词，已掌握 {{ stats.mastered_count }} 个</p>
        </div>
      </div>

      <div v-else class="empty">暂无数据</div>
    </div>
  </div>
</template>

<style scoped>
.overview-grid {
  grid-template-columns: repeat(3, 1fr);
}

.suffix {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-2);
  margin-left: 4px;
}

.progress-track {
  height: 10px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--brand-gradient);
  transition: width 0.4s ease;
}

.progress-tip {
  margin-top: 10px;
  font-size: 13px;
  color: var(--text-2);
}

@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
