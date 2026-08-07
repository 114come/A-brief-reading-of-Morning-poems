<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  BookMarked,
  BookOpen,
  BookOpenCheck,
  Compass,
  GraduationCap,
  MessageCircle,
  School,
} from 'lucide-vue-next'
import { useOnboardingStore } from '@/stores/onboarding'
import { useSrsStore } from '@/stores/srs'
import { useUiStore } from '@/stores/ui'

const onboarding = useOnboardingStore()
const srs = useSrsStore()
const ui = useUiStore()

// 目标 → 词书 code 映射（code 即目标字符串）
const targets = [
  { code: 'primary_school', label: '中小学', icon: School },
  { code: 'high_school', label: '高中', icon: BookOpen },
  { code: 'cet4', label: '四级', icon: BookMarked },
  { code: 'cet6', label: '六级', icon: BookOpenCheck },
  { code: 'kaoyan', label: '考研', icon: GraduationCap },
  { code: 'daily', label: '日常口语', icon: MessageCircle },
]

const selectedTarget = ref('cet4')
const selectedBookId = ref<number | null>(null)
const dailyNewWords = ref(20)
const pronunciation = ref<'us' | 'uk'>('us')
const autoplay = ref(true)
const submitting = ref(false)

const books = computed(() => srs.books)

// 目标词书自动高亮匹配
const matchedBook = computed(() => books.value.find((b) => b.code === selectedTarget.value) || null)

function pickTarget(code: string): void {
  selectedTarget.value = code
  const match = books.value.find((b) => b.code === code)
  if (match) selectedBookId.value = match.id
}

async function submit(): Promise<void> {
  const bookId = selectedBookId.value
  if (!bookId) {
    ui.showToast('请选择一本词书')
    return
  }
  submitting.value = true
  try {
    await srs.submitOnboarding({
      target: selectedTarget.value,
      book_id: bookId,
      daily_new_words: dailyNewWords.value,
      pronunciation: pronunciation.value,
      autoplay: autoplay.value,
    })
    onboarding.close()
    await srs.startDay()
    ui.showToast('设置完成，开始背单词吧！')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await srs.init()
  const current = srs.bookId || matchedBook.value?.id || books.value[0]?.id
  selectedBookId.value = current ?? null
  if (matchedBook.value) selectedBookId.value = matchedBook.value.id
})
</script>

<template>
  <Teleport to="body">
    <div class="modal-mask" @click.self="ui.showToast('请先完成设置')">
      <div class="modal-box onboarding-box">
        <div class="onboarding-head">
          <div class="empty-icon"><Compass :size="28" :stroke-width="1.6" /></div>
          <div class="modal-title">开始你的背单词计划</div>
          <p class="modal-desc" style="margin-bottom: 4px">选择学习目标与词库，我们为你安排每日复习计划</p>
        </div>

        <!-- 1. 学习目标 -->
        <div class="step-label">1. 选择学习目标</div>
        <div class="target-grid">
          <button
            v-for="t in targets"
            :key="t.code"
            type="button"
            class="target-btn"
            :class="{ active: selectedTarget === t.code }"
            @click="pickTarget(t.code)"
          >
            <span class="target-icon"><component :is="t.icon" :size="20" :stroke-width="1.8" /></span>
            <span>{{ t.label }}</span>
          </button>
        </div>

        <!-- 2. 词书 -->
        <div class="step-label">2. 选择主背诵词书</div>
        <div class="book-list">
          <button
            v-for="b in books"
            :key="b.id"
            type="button"
            class="book-btn"
            :class="{ active: selectedBookId === b.id, hint: matchedBook?.id === b.id }"
            @click="selectedBookId = b.id"
          >
            <span>{{ b.name }}</span>
            <span class="book-count">{{ b.word_count }} 词</span>
          </button>
        </div>

        <!-- 3. 参数 -->
        <div class="step-label">3. 背诵参数</div>
        <div class="param-row">
          <span class="param-name">每日新词</span>
          <div class="param-options">
            <button
              v-for="n in [10, 20, 30, 50]"
              :key="n"
              type="button"
              class="num-btn"
              :class="{ active: dailyNewWords === n }"
              @click="dailyNewWords = n"
            >
              {{ n }}
            </button>
          </div>
        </div>
        <div class="param-row">
          <span class="param-name">发音</span>
          <div class="param-options">
            <button type="button" class="num-btn" :class="{ active: pronunciation === 'us' }" @click="pronunciation = 'us'">美式</button>
            <button type="button" class="num-btn" :class="{ active: pronunciation === 'uk' }" @click="pronunciation = 'uk'">英式</button>
          </div>
        </div>
        <div class="param-row">
          <span class="param-name">自动播放</span>
          <button type="button" class="switch" :class="{ on: autoplay }" @click="autoplay = !autoplay">
            <span class="switch-knob"></span>
          </button>
        </div>

        <button class="btn btn-primary submit-btn" type="button" :disabled="submitting" @click="submit">
          {{ submitting ? '设置中…' : '开始背诵' }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.onboarding-box {
  width: 520px;
  max-height: 88vh;
  overflow-y: auto;
}

.onboarding-head {
  text-align: center;
  margin-bottom: 18px;
}

.step-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-2);
  margin: 16px 0 10px;
}

.target-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.target-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 6px;
  border: 1px solid var(--border-2);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  transition: all 0.18s ease;
}

.target-btn.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 600;
}

.target-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--surface-2);
  color: var(--primary);
  margin-bottom: 2px;
}

.target-btn.active .target-icon {
  background: var(--primary);
  color: #fff;
}

.book-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.book-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid var(--border-2);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  transition: all 0.18s ease;
}

.book-btn.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 600;
}

.book-btn.hint:not(.active) {
  border-color: var(--accent);
  color: var(--accent);
}

.book-count {
  font-size: 12px;
  opacity: 0.7;
}

.param-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.param-name {
  font-size: 14px;
  color: var(--text);
  flex-shrink: 0;
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
  transition: all 0.18s ease;
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

.submit-btn {
  width: 100%;
  height: 44px;
  margin-top: 20px;
  font-size: 16px;
}
</style>
