<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Search } from 'lucide-vue-next'
import { getCategories } from '@/api/english'
import { useAuthStore } from '@/stores/auth'
import { useSrsStore } from '@/stores/srs'
import { useUiStore } from '@/stores/ui'
import { categoryName, WORD_CATEGORIES, type Category, type Word } from '@/types'

const srs = useSrsStore()
const auth = useAuthStore()
const ui = useUiStore()

const activeTag = ref<string | null>(null)
const categories = ref<Category[]>([])
const loading = ref(false)

// 当前词库所有单词
const allWords = computed<Word[]>(() => srs.bookWords)

// 按首字母分组
const groups = computed(() => {
  const filtered = activeTag.value ? allWords.value.filter((w) => w.tag === activeTag.value) : allWords.value
  const map = new Map<string, Word[]>()
  for (const w of filtered) {
    const letter = (w.word[0] || '#').toUpperCase()
    if (!map.has(letter)) map.set(letter, [])
    map.get(letter)!.push(w)
  }
  const letters = [...map.keys()].sort()
  return letters.map((l) => ({ letter: l, words: map.get(l)! }))
})

const totalCount = computed(() => allWords.value.length)

async function loadCategories(): Promise<void> {
  if (!auth.isLoggedIn || !srs.bookId) return
  try {
    categories.value = await getCategories(srs.bookId)
  } catch {
    /* ignore */
  }
}

function tagOptions(): { value: string | null; label: string }[] {
  return [{ value: null, label: '未分类' }, ...WORD_CATEGORIES.map((c) => ({ value: c.tag, label: c.name }))]
}

async function setTag(word: Word, tag: string | null): Promise<void> {
  try {
    await srs.setWordTag(word.id, tag)
    ui.showToast(tag ? `已标记「${categoryName(tag)}」` : '已取消分类')
    await loadCategories()
  } catch {
    ui.showToast('操作失败')
  }
}

function selectTag(tag: string | null): void {
  activeTag.value = tag
}

onMounted(async () => {
  await srs.init()
  loading.value = true
  try {
    await loadCategories()
  } finally {
    loading.value = false
  }
})

watch(() => srs.bookId, loadCategories)
</script>

<template>
  <div>
    <!-- 分类筛选条 -->
    <div class="cat-filter">
      <button type="button" class="cat-chip" :class="{ active: activeTag === null }" @click="selectTag(null)">
        全部 <span class="chip-count">{{ totalCount }}</span>
      </button>
      <button
        v-for="c in categories"
        :key="c.tag"
        type="button"
        class="cat-chip"
        :class="{ active: activeTag === c.tag }"
        @click="selectTag(c.tag)"
      >
        {{ c.name }} <span class="chip-count">{{ c.count }}</span>
      </button>
    </div>

    <div v-if="!allWords.length" class="empty">加载中…</div>

    <div v-else-if="groups.length === 0" class="empty">
      <div class="empty-icon"><Search :size="28" :stroke-width="1.6" /></div>
      <div class="empty-text">该分类下暂无单词</div>
    </div>

    <div v-else class="book-browse">
      <div v-for="g in groups" :key="g.letter" class="letter-group card">
        <div class="letter-head">{{ g.letter }} <span class="letter-count">{{ g.words.length }}</span></div>
        <div v-for="w in g.words" :key="w.id" class="word-row">
          <div class="brow-main">
            <span class="brow-word">{{ w.word }}</span>
            <span v-if="w.pos" class="brow-pos">{{ w.pos }}</span>
            <span v-if="w.phonetic" class="brow-phonetic">{{ w.phonetic }}</span>
            <span class="brow-def">{{ w.definition }}</span>
          </div>
          <select
            class="tag-select"
            :class="{ tagged: w.tag }"
            :value="w.tag ?? ''"
            @change="(e) => setTag(w, (e.target as HTMLSelectElement).value || null)"
          >
            <option value="">未分类</option>
            <option v-for="c in WORD_CATEGORIES" :key="c.tag" :value="c.tag">{{ c.name }}</option>
          </select>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cat-filter {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
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

.chip-count {
  font-size: 12px;
  opacity: 0.7;
}

.book-browse {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.letter-group {
  overflow: hidden;
}

.letter-head {
  padding: 10px 18px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--primary);
}

.letter-count {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-3);
  margin-left: 6px;
}

.word-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 18px;
  border-bottom: 1px solid var(--border);
}

.word-row:last-child {
  border-bottom: none;
}

.word-row:hover {
  background: var(--surface-2);
}

.brow-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.brow-word {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  min-width: 120px;
}

.brow-pos {
  font-size: 12px;
  color: var(--primary);
  background: var(--primary-soft);
  padding: 1px 6px;
  border-radius: 5px;
  min-width: 46px;
  text-align: center;
  flex-shrink: 0;
}

.brow-phonetic {
  font-size: 12px;
  color: var(--text-3);
  min-width: 110px;
}

.brow-def {
  font-size: 13px;
  color: var(--text-2);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag-select {
  height: 28px;
  border: 1px solid var(--border-2);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-2);
  font-size: 13px;
  padding: 0 6px;
  flex-shrink: 0;
}

.tag-select.tagged {
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 600;
}
</style>
