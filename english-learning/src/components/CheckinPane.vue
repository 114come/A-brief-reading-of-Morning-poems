<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CheckCircle2 } from 'lucide-vue-next'
import { checkin, getCheckinStats } from '@/api/english'
import { useUiStore } from '@/stores/ui'
import type { CheckinStats } from '@/types'

const ui = useUiStore()
const stats = ref<CheckinStats | null>(null)

const weekdayNames = ['日', '一', '二', '三', '四', '五', '六']

/** 最近 30 天的打卡格子（补足到周一起始） */
const calendarDays = computed(() => {
  if (!stats.value) return []
  const dates = new Set(stats.value.recent_dates)
  const days: { date: string; done: boolean; day: number }[] = []
  const today = new Date()
  // 计算需要向前补足的偏移，使最后一周从周一开始
  const end = new Date(today)
  const offset = (end.getDay() + 6) % 7 // 到上周一的距离
  for (let i = 0; i < 30; i++) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const iso = d.toISOString().slice(0, 10)
    days.unshift({ date: iso, done: dates.has(iso), day: d.getDate() })
  }
  // 前置补齐到周一开始
  const first = new Date(days[0]?.date || today)
  const lead = (first.getDay() + 6) % 7
  for (let i = lead; i > 0; i--) {
    const d = new Date(first)
    d.setDate(d.getDate() - i)
    days.unshift({ date: d.toISOString().slice(0, 10), done: false, day: d.getDate() })
  }
  return days
})

const todayIso = computed(() => new Date().toISOString().slice(0, 10))

async function doCheckin(): Promise<void> {
  try {
    stats.value = await checkin()
    ui.showToast('打卡成功，继续加油！')
  } catch {
    ui.showToast('打卡失败')
  }
}

onMounted(async () => {
  try {
    stats.value = await getCheckinStats()
  } catch {
    ui.showToast('加载打卡数据失败')
  }
})
</script>

<template>
  <div>
    <div v-if="!stats" class="empty">加载中…</div>

    <template v-else>
      <div class="stat-grid checkin-stats">
        <div class="stat-card">
          <div class="stat-num">{{ stats.total_days }}</div>
          <div class="stat-label">累计打卡（天）</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: var(--success)">{{ stats.streak_days }}</div>
          <div class="stat-label">连续打卡（天）</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" :style="{ color: stats.today_done ? 'var(--success)' : 'var(--text-3)' }">
            {{ stats.today_done ? '已打卡' : '未打卡' }}
          </div>
          <div class="stat-label">今日状态</div>
        </div>
      </div>

      <div class="card card-pad" style="margin-top: 16px">
        <div class="checkin-action">
          <div>
            <div class="field-label" style="margin-bottom: 2px">每日一签</div>
            <p class="checkin-tip">坚持每天打卡，积累是学好英语的捷径。</p>
          </div>
          <button
            class="btn btn-primary"
            type="button"
            :disabled="stats.today_done"
            @click="doCheckin"
          >
            <template v-if="stats.today_done">
              <CheckCircle2 :size="16" />
              今日已打卡
            </template>
            <template v-else>立即打卡</template>
          </button>
        </div>
      </div>

      <div class="card card-pad" style="margin-top: 16px">
        <div class="field-label" style="margin-bottom: 12px">最近 30 天</div>
        <div class="calendar">
          <div v-for="d in calendarDays" :key="d.date" class="cal-cell" :class="{ done: d.done, today: d.date === todayIso }">
            <span class="cal-day">{{ d.day }}</span>
          </div>
        </div>
        <div class="cal-legend">
          <span class="cal-cell" style="width: 18px; height: 18px; background: var(--surface-2); border: 1px solid var(--border)"></span>
          <span style="font-size: 12px; color: var(--text-2)">未打卡</span>
          <span class="cal-cell" style="width: 18px; height: 18px; background: var(--primary); margin-left: 12px"></span>
          <span style="font-size: 12px; color: var(--text-2)">已打卡</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.checkin-stats {
  grid-template-columns: repeat(3, 1fr);
}

.checkin-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.checkin-tip {
  font-size: 13px;
  color: var(--text-2);
}

.calendar {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 6px;
}

.cal-cell {
  aspect-ratio: 1;
  max-width: 44px;
  border-radius: 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--text-3);
}

.cal-cell.done {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
  font-weight: 600;
}

.cal-cell.today {
  outline: 2px solid var(--primary-2);
  outline-offset: 1px;
}

.cal-legend {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  color: var(--text-2);
}
</style>
