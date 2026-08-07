import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  generateDailySummary,
  getDailySummary,
  getTodayActivity,
  reportActivity,
} from '@/api/english'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import type { ActivityReport, DailySummary } from '@/types'

export const useDailySummaryStore = defineStore('dailySummary', () => {
  const auth = useAuthStore()
  const ui = useUiStore()

  const summary = ref<DailySummary | null>(null)
  const loading = ref(false)
  const generating = ref(false)
  const hasActivityToday = ref(false)
  const todayChecked = ref(false)

  async function refreshHasActivity(): Promise<void> {
    if (!auth.isLoggedIn || todayChecked.value) return
    try {
      const r = await getTodayActivity()
      hasActivityToday.value = r.has_activity
      todayChecked.value = true
    } catch {
      /* ignore */
    }
  }

  async function loadSummary(): Promise<void> {
    if (!auth.isLoggedIn) return
    loading.value = true
    try {
      summary.value = await getDailySummary()
    } catch {
      ui.showToast('加载日报失败')
    } finally {
      loading.value = false
    }
  }

  async function generate(): Promise<DailySummary | null> {
    if (!auth.isLoggedIn) return null
    if (generating.value) return null
    generating.value = true
    try {
      // 若已生成则读缓存
      if (!summary.value?.ai_overview) {
        summary.value = await getDailySummary()
      }
      if (summary.value?.ai_overview) {
        ui.showToast('今日日报已生成')
        return summary.value
      }
      summary.value = await generateDailySummary()
      ui.showToast('今日 AI 日报已生成')
      return summary.value
    } catch (e) {
      ui.showToast((e as Error).message || '生成失败')
      return null
    } finally {
      generating.value = false
    }
  }

  /** 埋点上报（登录用户）；成功后标记今日有活动 */
  async function report(data: ActivityReport): Promise<void> {
    if (!auth.isLoggedIn) return
    try {
      await reportActivity(data)
      hasActivityToday.value = true
      todayChecked.value = true
    } catch {
      /* 埋点失败不阻塞学习 */
    }
  }

  return { summary, loading, generating, hasActivityToday, todayChecked, refreshHasActivity, loadSummary, generate, report }
})
