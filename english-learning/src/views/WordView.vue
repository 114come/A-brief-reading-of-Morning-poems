<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useOnboardingStore } from '@/stores/onboarding'
import { useSrsStore } from '@/stores/srs'
import DailyStudyPane from '@/components/DailyStudyPane.vue'
import NotebookPane from '@/components/NotebookPane.vue'
import SettingsPane from '@/components/SettingsPane.vue'
import WordBookBrowse from '@/components/WordBookBrowse.vue'
import TestPane from '@/components/test/TestPane.vue'
import OnboardingModal from '@/components/OnboardingModal.vue'

const srs = useSrsStore()
const onboarding = useOnboardingStore()

const activeTab = ref('study')
const tabs = [
  { key: 'study', label: '每日学习' },
  { key: 'browse', label: '查看词库', requiresLogin: false },
  { key: 'test', label: '单词测试', requiresLogin: false },
  { key: 'notebook', label: '生词本', requiresLogin: false },
  { key: 'settings', label: '词库设置' },
]

onMounted(async () => {
  await srs.init()
  // 首次进入/未引导 → 打开引导弹窗（不可跳过）
  if (!srs.onboarded) onboarding.open(srs.bookId ?? undefined)
})

watch(
  () => srs.onboarded,
  (onb) => {
    if (!onb) onboarding.open(srs.bookId ?? undefined)
  },
)
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <h1 class="page-title">词笺</h1>
        <p class="page-desc">先复习到期旧词，再学习今日新词，智能间隔复习</p>
      </div>
    </div>

    <div class="tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        type="button"
        class="tab-item"
        :class="{ active: activeTab === t.key }"
        @click="activeTab = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <DailyStudyPane v-if="activeTab === 'study'" />
    <WordBookBrowse v-else-if="activeTab === 'browse'" />
    <TestPane v-else-if="activeTab === 'test'" />
    <NotebookPane v-else-if="activeTab === 'notebook'" />
    <SettingsPane v-else />

    <OnboardingModal v-if="onboarding.isOpen" />
  </div>
</template>
