<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { BarChart3, BrainCircuit, Lightbulb, Sparkles } from 'lucide-vue-next'
import { useDailySummaryStore } from '@/stores/dailySummary'
import { useUiStore } from '@/stores/ui'
import type { SummaryCategory } from '@/types'

const store = useDailySummaryStore()
const ui = useUiStore()

const summary = computed(() => store.summary)
const generated = computed(() => Boolean(summary.value?.ai_overview))

function copyText(text: string, label: string): void {
  const doCopy = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(
        () => ui.showToast(`${label}已复制`),
        () => fallbackCopy(text, label),
      )
    } else {
      fallbackCopy(text, label)
    }
  }
  doCopy()
}

function fallbackCopy(text: string, label: string): void {
  const ta = document.createElement('textarea')
  ta.value = text
  document.body.appendChild(ta)
  ta.select()
  try {
    document.execCommand('copy')
    ui.showToast(`${label}已复制`)
  } catch {
    ui.showToast('复制失败')
  }
  document.body.removeChild(ta)
}

function copyTable(): void {
  if (!summary.value?.table) return
  const lines = ['学习分类\t统计项目\t当日数据']
  for (const cat of summary.value.table) {
    for (const item of cat.items) {
      lines.push(`${cat.category}\t${item.label}\t${item.value}`)
    }
  }
  copyText(lines.join('\n'), '表格')
}

function copySummary(): void {
  if (!summary.value) return
  copyText(`${summary.value.ai_overview}\n\n${summary.value.ai_advice}`, '总结')
}

onMounted(() => {
  store.loadSummary()
})
</script>

<template>
  <div class="summary-pane">
    <!-- 加载中 -->
    <div v-if="store.loading" class="empty">加载中…</div>

    <!-- 空态：未生成 -->
    <div v-else-if="!generated" class="card card-pad summary-empty">
      <div class="empty-icon"><Sparkles :size="28" :stroke-width="1.6" /></div>
      <div class="empty-title">AI 学习日报</div>
      <p class="empty-text">完成今日学习后，AI 将基于你的单词、阅读和测试数据，生成专属学习日报与建议。</p>
      <button
        class="btn btn-primary gen-btn"
        type="button"
        :disabled="store.generating"
        @click="store.generate()"
      >
        {{ store.generating ? 'AI 分析中…' : '生成今日 AI 总结' }}
      </button>
      <p class="empty-hint">每日仅可生成 1 次 · 仅登录用户可用</p>
    </div>

    <!-- 已生成 -->
    <div v-else class="summary-content">
      <!-- 数据汇总表 -->
      <div class="card card-pad">
        <div class="sub-head">
          <div class="sub-title">
            <BarChart3 :size="17" :stroke-width="1.8" style="vertical-align: -3px; margin-right: 6px" />
            当日学习数据汇总
          </div>
          <button class="btn btn-ghost btn-sm" type="button" @click="copyTable">复制表格</button>
        </div>
        <table class="summary-table">
          <thead>
            <tr><th>学习分类</th><th>统计项目</th><th>当日数据</th></tr>
          </thead>
          <tbody>
            <template v-for="cat in (summary?.table || [])" :key="cat.category">
              <tr v-for="(item, i) in cat.items" :key="item.label">
                <td v-if="i === 0" :rowspan="cat.items.length" class="cat-cell">{{ cat.category }}</td>
                <td>{{ item.label }}</td>
                <td class="val-cell">{{ item.value }}</td>
              </tr>
            </template>
          </tbody>
        </table>
        <p v-if="summary?.source === 'fallback'" class="source-hint">AI 服务暂不可用，已展示数据概览</p>
        <p v-else class="gen-time">生成于 {{ summary?.generated_at ? new Date(summary.generated_at).toLocaleTimeString() : '' }}</p>
      </div>

      <!-- AI 板块 1：客观概括 -->
      <div class="card card-pad ai-block">
        <div class="ai-icon"><BrainCircuit :size="18" :stroke-width="1.8" /></div>
        <div class="ai-body">
          <div class="ai-label">客观数据概括</div>
          <p class="ai-text">{{ summary?.ai_overview }}</p>
        </div>
      </div>

      <!-- AI 板块 2：个性化建议 -->
      <div class="card card-pad ai-block">
        <div class="ai-icon"><Lightbulb :size="18" :stroke-width="1.8" /></div>
        <div class="ai-body">
          <div class="ai-label">个性化点评与次日建议</div>
          <p class="ai-text">{{ summary?.ai_advice }}</p>
        </div>
      </div>

      <div class="copy-actions">
        <button class="btn btn-soft" type="button" @click="copySummary">复制 AI 总结</button>
        <button class="btn btn-ghost" type="button" @click="store.generate()">查看（重复进入）</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.summary-empty {
  max-width: 560px;
  margin: 0 auto;
  text-align: center;
  padding: 48px 40px;
}

.empty-title {
  font-size: var(--fs-xl);
  font-weight: 600;
  margin-top: 12px;
}

.gen-btn {
  margin-top: 20px;
  height: 44px;
  padding: 0 32px;
}

.empty-hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-3);
}

.sub-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.sub-title {
  font-size: 17px;
  font-weight: 700;
}

.summary-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.summary-table th {
  text-align: left;
  padding: 10px 12px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  color: var(--text-2);
  font-weight: 600;
}

.summary-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
}

.cat-cell {
  font-weight: 700;
  color: var(--primary);
  vertical-align: top;
}

.val-cell {
  font-weight: 600;
  color: var(--text);
}

.source-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--accent);
}

.gen-time {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-3);
}

.ai-block {
  margin-top: 14px;
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.ai-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--primary-soft);
  color: var(--primary);
  flex-shrink: 0;
}

.ai-label {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 6px;
}

.ai-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text);
}

.copy-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 18px;
}
</style>
