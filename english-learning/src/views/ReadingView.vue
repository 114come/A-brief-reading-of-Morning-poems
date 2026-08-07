<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Eye,
  EyeOff,
  NotebookPen,
  Star,
  Target,
  Volume2,
} from 'lucide-vue-next'
import {
  addCollection,
  completeDailyReading,
  createNote,
  getArticle,
  getDailyReadingToday,
  getReadingArchive,
  removeCollection,
  setReadingLevel,
  updateNote,
} from '@/api/english'
import { useAuthStore } from '@/stores/auth'
import { useDailySummaryStore } from '@/stores/dailySummary'
import { useUiStore } from '@/stores/ui'
import { TTS_RATES, useTts } from '@/composables/useTts'
import type { Article, DailyReadingToday, ReadingArchiveItem } from '@/types'
import { READING_LEVEL_LABEL, READING_TOPIC_LABEL } from '@/types'
import PageTabs from '@/components/PageTabs.vue'
import WordLookupPopover from '@/components/WordLookupPopover.vue'
import ReadingQuizPane from '@/components/ReadingQuizPane.vue'

const auth = useAuthStore()
const ui = useUiStore()
const summary = useDailySummaryStore()
const tts = useTts()

const tabs = [
  { key: 'today', label: '今日一读' },
  { key: 'archive', label: '历史存档', requiresLogin: true },
]
const activeTab = ref('today')

// ── 今日数据 ────────────────────────────────────────────────────
const loading = ref(false)
const today = ref<DailyReadingToday | null>(null)
const article = computed<Article | null>(() => today.value?.article ?? archiveArticle.value)
const archiveArticle = ref<Article | null>(null)

// 阅读计时
let readSec = 0
let readTimer: ReturnType<typeof setInterval> | null = null
function startReadTimer(): void {
  if (readTimer) return
  readTimer = setInterval(() => {
    if (document.visibilityState === 'visible') readSec += 1
  }, 1000)
}
function stopReadTimer(): void {
  if (readTimer) {
    clearInterval(readTimer)
    readTimer = null
  }
}

// ── 工具栏 ──────────────────────────────────────────────────────
const rate = ref(1.0)
const maskMode = ref(false) // 遮罩：只看中文
const showCn = ref(false) // 全文翻译对照

// ── 划词弹层 ────────────────────────────────────────────────────
const popover = ref<{ word: string; x: number; y: number } | null>(null)

// ── 今日任务 ────────────────────────────────────────────────────
const record = computed(() => today.value?.record)
const readingDone = computed(() => record.value?.status === 'done')
const wordTaskDone = computed(() => today.value?.word_task_done ?? false)

async function loadToday(): Promise<void> {
  loading.value = true
  archiveArticle.value = null
  popover.value = null
  try {
    today.value = await getDailyReadingToday()
    startReadTimer()
  } catch (e) {
    ui.showToast((e as Error).message || '今日文章加载失败')
  } finally {
    loading.value = false
  }
}

async function changeLevel(mode: 'auto' | 'manual', level?: 'basic' | 'cet4' | 'advanced'): Promise<void> {
  try {
    await setReadingLevel(mode, level)
    ui.showToast(level ? `难度已切换为 ${READING_LEVEL_LABEL[level]}` : '已恢复自动适配')
    await loadToday()
  } catch (e) {
    ui.showToast((e as Error).message || '切换失败')
  }
}

// ── 朗读 ────────────────────────────────────────────────────────
function speakArticle(): void {
  if (!article.value) return
  tts.speakUS(article.value.content, rate.value)
}

// ── 划词 ────────────────────────────────────────────────────────
function onTokenClick(word: string, e: MouseEvent): void {
  const pad = 14
  let x = e.clientX + pad
  let y = e.clientY + pad
  if (x + 300 > window.innerWidth) x = e.clientX - 300 - pad
  if (y + 180 > window.innerHeight) y = e.clientY - 180 - pad
  popover.value = { word, x: Math.max(8, x), y: Math.max(8, y) }
}
function closePopover(): void {
  popover.value = null
}
function onCollected(): void {
  // 刷新今日数据（更新 new_word_count）
  void loadToday()
}

// ── 收藏 / 笔记 ─────────────────────────────────────────────────
async function toggleFavorite(): Promise<void> {
  if (!article.value) return
  try {
    if (article.value.is_favorite) {
      const all = await summaryFavorites()
      const col = all.find((c) => c.item_id === article.value!.id && c.item_type === 'reading')
      if (col) await removeCollection(col.id)
      article.value.is_favorite = false
      ui.showToast('已取消收藏')
    } else {
      await addCollection('reading', article.value.id)
      article.value.is_favorite = true
      ui.showToast('已收藏')
    }
  } catch {
    ui.showToast('操作失败')
  }
}
async function summaryFavorites() {
  const { listCollections } = await import('@/api/english')
  return listCollections('reading')
}

const noteText = ref('')
const savingNote = ref(false)
const canEditNote = computed(() => auth.isLoggedIn)
const noteOpen = ref(false)

async function saveNote(): Promise<void> {
  if (!article.value || !noteText.value.trim()) {
    ui.showToast('笔记内容不能为空')
    return
  }
  savingNote.value = true
  try {
    if (article.value.note_id) {
      await updateNote(article.value.note_id, noteText.value.trim())
    } else {
      await createNote(article.value.id, noteText.value.trim())
    }
    ui.showToast('笔记已保存')
    const updated = await getArticle(article.value.id)
    article.value.note_id = updated.note_id
    article.value.note_updated_at = updated.note_updated_at
    noteOpen.value = false
  } catch {
    ui.showToast('保存失败')
  } finally {
    savingNote.value = false
  }
}

// ── 完成打卡 ────────────────────────────────────────────────────
const completing = ref(false)
async function completeReading(): Promise<void> {
  if (!article.value) return
  completing.value = true
  try {
    await completeDailyReading(article.value.id, readSec)
    stopReadTimer()
    ui.showToast('今日一读打卡成功')
    await loadToday()
  } catch (e) {
    ui.showToast((e as Error).message || '打卡失败')
  } finally {
    completing.value = false
  }
}

// ── 历史存档 ────────────────────────────────────────────────────
const archiveLoading = ref(false)
const archiveItems = ref<ReadingArchiveItem[]>([])

async function loadArchive(): Promise<void> {
  archiveLoading.value = true
  try {
    archiveItems.value = await getReadingArchive()
  } catch (e) {
    ui.showToast((e as Error).message || '加载失败')
  } finally {
    archiveLoading.value = false
  }
}

async function viewArchiveItem(item: ReadingArchiveItem): Promise<void> {
  try {
    archiveArticle.value = await getArticle(item.article_id)
    maskMode.value = false
    showCn.value = false
    popover.value = null
  } catch {
    ui.showToast('加载文章失败')
  }
}
function backFromArchive(): void {
  archiveArticle.value = null
}

// ── 文本分词渲染 ────────────────────────────────────────────────
function splitTokens(text: string): { text: string; word: string | null }[] {
  return text.split(/(\s+)/).map((seg) => {
    if (/^[A-Za-z][A-Za-z'-]*$/.test(seg)) {
      return { text: seg, word: seg.replace(/[^A-Za-z]/g, '').toLowerCase() }
    }
    return { text: seg, word: null }
  })
}

const paragraphs = computed(() => (article.value?.content ?? '').split(/\n+/).filter((p) => p.trim()))
const cnParagraphs = computed(() => (article.value?.content_cn ?? '').split(/\n+/).filter((p) => p.trim()))

onMounted(() => {
  void loadToday()
})

// 切换到历史存档时加载
watch(activeTab, (t) => {
  if (t === 'archive' && !archiveItems.value.length) void loadArchive()
})

onBeforeUnmount(() => {
  stopReadTimer()
  if (auth.isLoggedIn && readSec > 0) {
    void summary.report({ reading_duration_sec: readSec })
  }
})
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <h1 class="page-title">浅读</h1>
        <p class="page-desc">每天一篇适配你词汇水平的短文，读完后答题打卡，生词自动进入背诵流程</p>
      </div>
    </div>

    <PageTabs v-model="activeTab" :tabs="tabs" />

    <!-- ═══ 今日一读 ═══ -->
    <div v-if="activeTab === 'today'">
      <div v-if="loading && !today" class="empty">今日文章生成中…（约需数秒）</div>

      <template v-else-if="today && article">
        <!-- 任务状态卡 -->
        <div class="card task-card">
          <div class="task-item" :class="{ done: readingDone }">
            <span class="task-icon">
              <CheckCircle2 v-if="readingDone" :size="18" :stroke-width="2" />
              <BookOpen v-else :size="18" :stroke-width="1.8" />
            </span>
            <div>
              <div class="task-name">今日一读</div>
              <div class="task-state">{{ readingDone ? '已打卡' : '未完成' }}</div>
            </div>
          </div>
          <div class="task-divider"></div>
          <div class="task-item" :class="{ done: wordTaskDone }">
            <span class="task-icon">
              <CheckCircle2 v-if="wordTaskDone" :size="18" :stroke-width="2" />
              <BookOpen v-else :size="18" :stroke-width="1.8" />
            </span>
            <div>
              <div class="task-name">今日背单词</div>
              <div class="task-state">{{ wordTaskDone ? '已完成' : '待完成' }}</div>
            </div>
          </div>
          <div class="task-divider"></div>
          <div class="task-item">
            <span class="task-icon"><Target :size="18" :stroke-width="1.8" /></span>
            <div>
              <div class="task-name">文章难度</div>
              <div class="task-state">
                <select
                  class="select sm level-select"
                  :value="today.level_mode === 'manual' ? today.manual_level ?? 'auto' : 'auto'"
                  @change="
                    (e) => {
                      const v = (e.target as HTMLSelectElement).value
                      if (v === 'auto') changeLevel('auto')
                      else changeLevel('manual', v as 'basic' | 'cet4' | 'advanced')
                    }
                  "
                >
                  <option value="auto">自动适配</option>
                  <option value="basic">基础</option>
                  <option value="cet4">四级</option>
                  <option value="advanced">高阶</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- 文章头 -->
        <div class="card article-head-card">
          <div class="article-title">{{ article.title }}</div>
          <div class="article-meta">
            <span v-if="article.level" class="tag tag-primary">{{ READING_LEVEL_LABEL[article.level] || article.level }}</span>
            <span v-if="article.topic" class="tag">{{ READING_TOPIC_LABEL[article.topic] || article.topic }}</span>
            <span class="meta-text">{{ article.word_count }} 词</span>
            <span class="meta-text">约 {{ today.estimated_min }} 分钟</span>
            <span class="spacer"></span>
            <button
              class="btn btn-ghost btn-sm"
              :class="{ faved: article.is_favorite }"
              type="button"
              @click="toggleFavorite"
            >
              <template v-if="article.is_favorite">
                <Star :size="14" :stroke-width="2" :fill="'currentColor'" />
                已收藏
              </template>
              <template v-else>
                <Star :size="14" :stroke-width="2" />
                收藏
              </template>
            </button>
          </div>

          <!-- 工具栏 -->
          <div class="article-tools">
            <div class="tool-group">
              <button class="btn btn-ghost btn-sm" type="button" @click="speakArticle">
                <Volume2 :size="14" :stroke-width="2" />朗读全文
              </button>
              <div class="rate-group">
                <button
                  v-for="r in TTS_RATES"
                  :key="r.rate"
                  type="button"
                  class="rate-btn"
                  :class="{ active: rate === r.rate }"
                  @click="rate = r.rate"
                >
                  {{ r.label }}
                </button>
              </div>
            </div>
            <div class="tool-group">
              <button
                class="btn btn-ghost btn-sm"
                :class="{ toggled: maskMode }"
                type="button"
                @click="maskMode = !maskMode"
              >
                <EyeOff v-if="maskMode" :size="14" :stroke-width="2" />
                <Eye v-else :size="14" :stroke-width="2" />
                {{ maskMode ? '遮罩已开启' : '遮罩模式' }}
              </button>
              <button
                class="btn btn-ghost btn-sm"
                :class="{ toggled: showCn }"
                type="button"
                :disabled="maskMode"
                @click="showCn = !showCn"
              >
                {{ showCn ? '隐藏翻译' : '全文翻译' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 正文 -->
        <div class="card article-body">
          <!-- 遮罩模式：只显示中文 -->
          <div v-if="maskMode" class="cn-text">
            <p v-for="(p, i) in cnParagraphs" :key="i" class="cn-para">{{ p }}</p>
            <p v-if="!cnParagraphs.length" class="cn-para">{{ article.content_cn }}</p>
            <div class="mask-hint">遮罩模式：隐藏英文，对照中文回忆</div>
          </div>

          <!-- 正常阅读 -->
          <template v-else>
            <p v-for="(p, i) in paragraphs" :key="i" class="en-para">
              <template v-for="(tok, j) in splitTokens(p)" :key="j">
                <button
                  v-if="tok.word"
                  type="button"
                  class="word-token"
                  @click="onTokenClick(tok.word, $event)"
                >
                  {{ tok.text }}
                </button>
                <span v-else>{{ tok.text }}</span>
              </template>
            </p>
            <div v-if="showCn" class="cn-block">
              <p v-for="(p, i) in cnParagraphs" :key="i" class="cn-para">{{ p }}</p>
            </div>
          </template>
        </div>

        <!-- 今日小测 -->
        <ReadingQuizPane :article-id="article.id" />

        <!-- 动作区 -->
        <div class="card action-card">
          <div class="action-note" v-if="noteOpen || article.note_id">
            <div class="field-label">{{ article.note_id ? '我的笔记' : '添加笔记' }}</div>
            <textarea v-model="noteText" class="input" rows="3" placeholder="记录生词、好句和感想…" />
            <div class="note-actions">
              <button class="btn btn-ghost btn-sm" type="button" @click="noteOpen = false">收起</button>
              <button class="btn btn-primary btn-sm" type="button" :disabled="savingNote" @click="saveNote">
                {{ savingNote ? '保存中…' : '保存笔记' }}
              </button>
            </div>
          </div>
          <div class="action-row">
            <button class="btn btn-ghost btn-sm" type="button" @click="noteOpen = true">
              <NotebookPen :size="14" :stroke-width="2" />添加笔记
            </button>
            <span class="spacer"></span>
            <button
              class="btn btn-primary"
              type="button"
              :disabled="completing || readingDone"
              @click="completeReading"
            >
              <template v-if="readingDone">
                <CheckCircle2 :size="16" />今日已打卡
              </template>
              <template v-else>{{ completing ? '打卡中…' : '完成今日一读打卡' }}</template>
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- ═══ 历史存档 ═══ -->
    <div v-else>
      <div v-if="archiveArticle" class="card archive-detail">
        <div class="archive-detail-head">
          <button class="btn btn-ghost btn-sm" type="button" @click="backFromArchive">
            <ArrowLeft :size="14" :stroke-width="2" />返回存档
          </button>
          <span class="spacer"></span>
          <button class="btn btn-ghost btn-sm" type="button" @click="speakArticle">
            <Volume2 :size="14" :stroke-width="2" />朗读
          </button>
          <button
            class="btn btn-ghost btn-sm"
            :class="{ toggled: maskMode }"
            type="button"
            @click="maskMode = !maskMode"
          >
            <EyeOff v-if="maskMode" :size="14" :stroke-width="2" />
            <Eye v-else :size="14" :stroke-width="2" />
            遮罩
          </button>
        </div>
        <div class="article-title">{{ archiveArticle.title }}</div>
        <div class="article-meta">
          <span v-if="archiveArticle.level" class="tag tag-primary">{{ READING_LEVEL_LABEL[archiveArticle.level] || archiveArticle.level }}</span>
          <span v-if="archiveArticle.topic" class="tag">{{ READING_TOPIC_LABEL[archiveArticle.topic] || archiveArticle.topic }}</span>
          <span class="meta-text">{{ archiveArticle.word_count }} 词</span>
        </div>
        <div v-if="maskMode" class="cn-text">
          <p v-for="(p, i) in cnParagraphs" :key="i" class="cn-para">{{ p }}</p>
        </div>
        <template v-else>
          <p v-for="(p, i) in paragraphs" :key="i" class="en-para">{{ p }}</p>
          <div v-if="showCn" class="cn-block">
            <p v-for="(p, i) in cnParagraphs" :key="i" class="cn-para">{{ p }}</p>
          </div>
        </template>
      </div>

      <template v-else>
        <div v-if="archiveLoading" class="empty">加载中…</div>
        <div v-else-if="!archiveItems.length" class="empty">还没有历史阅读记录，快去完成今日一读吧</div>
        <div v-else class="archive-list">
          <div v-for="item in archiveItems" :key="item.id" class="card archive-card" @click="viewArchiveItem(item)">
            <div class="archive-head">
              <span class="archive-date">{{ item.reading_date }}</span>
              <span class="tag tag-primary">{{ item.level_label }}</span>
              <span v-if="item.topic_label" class="tag">{{ item.topic_label }}</span>
              <span class="spacer"></span>
              <span v-if="item.status === 'done'" class="done-badge">
                <CheckCircle2 :size="12" :stroke-width="2.2" style="vertical-align: -2px; margin-right: 3px" />
                已打卡
              </span>
              <span v-else class="pending-badge">待打卡</span>
            </div>
            <div class="archive-title">{{ item.title }}</div>
            <div class="archive-stats">
              <span>正确率 <b>{{ item.accuracy }}%</b></span>
              <span>新增生词 <b>{{ item.new_word_count }}</b> 个</span>
              <span v-if="item.note_id">
                <NotebookPen :size="13" :stroke-width="2" style="vertical-align: -2px; margin-right: 3px" />
                有笔记
              </span>
              <span v-if="item.is_favorite">
                <Star :size="13" :stroke-width="2" :fill="'currentColor'" style="vertical-align: -2px; margin-right: 3px" />
                已收藏
              </span>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 划词弹层 -->
    <WordLookupPopover
      v-if="popover && article"
      :word="popover.word"
      :keywords="article.keywords ?? []"
      :article-id="article.id"
      :style="{ left: popover.x + 'px', top: popover.y + 'px' }"
      @collected="onCollected"
      @close="closePopover"
    />
  </div>
</template>

<style scoped>
/* 任务卡 */
.task-card {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px 20px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 120px;
}

.task-item.done .task-name,
.task-item.done .task-state {
  color: var(--success);
}

.task-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--primary-soft);
  color: var(--primary);
  flex-shrink: 0;
}

.task-item.done .task-icon {
  background: var(--success-soft);
  color: var(--success);
}

.task-name {
  font-size: 13px;
  color: var(--text-3);
}

.task-state {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.task-divider {
  width: 1px;
  height: 30px;
  background: var(--border);
}

.level-select {
  min-width: 108px;
}

/* 文章头 */
.article-head-card {
  margin-top: 14px;
  padding: 22px 26px;
}

.article-title {
  font-size: var(--fs-xl);
  font-weight: 600;
  line-height: 1.5;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.meta-text {
  font-size: 13px;
  color: var(--text-3);
}

.article-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
  flex-wrap: wrap;
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.rate-group {
  display: inline-flex;
  border: 1px solid var(--border-2);
  border-radius: 999px;
  overflow: hidden;
}

.rate-btn {
  padding: 5px 12px;
  font-size: 12px;
  border: none;
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
}

.rate-btn.active {
  background: var(--primary);
  color: #fff;
}

.btn.toggled {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-soft);
}

/* 正文 */
.article-body {
  margin-top: 14px;
  padding: 28px 34px;
}

.en-para {
  font-size: 16px;
  line-height: 2.1;
  color: var(--text);
  margin-bottom: 16px;
}

.word-token {
  border: none;
  background: transparent;
  padding: 0;
  font-size: inherit;
  line-height: inherit;
  color: inherit;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s ease;
}

.word-token:hover {
  background: var(--primary-soft);
  color: var(--primary);
  box-shadow: inset 0 -2px 0 var(--primary);
}

.cn-text {
  color: var(--text-2);
}

.cn-para {
  font-size: 15px;
  line-height: 2;
  margin-bottom: 12px;
}

.cn-block {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px dashed var(--border-2);
}

.mask-hint {
  margin-top: 22px;
  font-size: 12px;
  color: var(--text-3);
  text-align: center;
}

/* 动作区 */
.action-card {
  margin-top: 14px;
  padding: 18px 24px;
}

.action-note {
  margin-bottom: 14px;
}

.note-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 历史存档 */
.archive-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-top: 4px;
}

.archive-card {
  padding: 18px 20px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.archive-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.archive-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.archive-date {
  font-size: 13px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}

.archive-title {
  margin-top: 10px;
  font-size: var(--fs-md);
  font-weight: 600;
}

.archive-stats {
  margin-top: 10px;
  display: flex;
  gap: 14px;
  font-size: 13px;
  color: var(--text-3);
}

.archive-stats b {
  color: var(--primary);
}

.done-badge {
  font-size: 12px;
  color: var(--success);
}

.pending-badge {
  font-size: 12px;
  color: var(--text-3);
}

.archive-detail {
  padding: 24px 30px;
}

.archive-detail-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.faved {
  color: var(--primary);
  border-color: var(--primary);
  background: var(--primary-soft);
}

.spacer {
  flex: 1;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .task-card {
    gap: 12px;
    padding: 14px 16px;
  }

  .article-head-card {
    padding: 18px 16px;
  }

  .article-body {
    padding: 20px 18px;
  }

  .en-para {
    font-size: 15px;
    line-height: 2;
  }

  .archive-list {
    grid-template-columns: 1fr;
  }

  .archive-detail {
    padding: 18px 16px;
  }
}
</style>
