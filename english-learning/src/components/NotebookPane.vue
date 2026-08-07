<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { BookOpen } from 'lucide-vue-next'
import { clearWordbook, listWordbook, removeWordbook } from '@/api/english'
import { useAuthStore } from '@/stores/auth'
import { useSrsStore } from '@/stores/srs'
import { useUiStore } from '@/stores/ui'
import type { WordbookItem } from '@/types'

const auth = useAuthStore()
const srs = useSrsStore()
const ui = useUiStore()

const loading = ref(false)
const items = ref<WordbookItem[]>([])
const selectedBookId = ref<number | null>(null)

const books = computed(() => srs.books)

async function load(): Promise<void> {
  loading.value = true
  try {
    const bookId = selectedBookId.value ?? srs.bookId ?? undefined
    if (auth.isLoggedIn) {
      items.value = await listWordbook(bookId)
    } else {
      const { loadGuestWordbook } = await import('@/composables/srsStorage')
      const ids = loadGuestWordbook(selectedBookId.value ?? srs.bookId ?? 0)
      const all = srs.bookWords
      items.value = ids
        .map((word_id) => all.find((w) => w.id === word_id))
        .filter(Boolean)
        .map((w, idx) => ({ id: idx, book_id: selectedBookId.value ?? 0, created_at: '', word: w! }))
    }
  } catch {
    ui.showToast('加载生词本失败')
  } finally {
    loading.value = false
  }
}

/** 认识 → 移出生词本 */
async function known(item: WordbookItem): Promise<void> {
  try {
    if (auth.isLoggedIn) {
      await removeWordbook(item.id)
    } else {
      const { loadGuestWordbook, saveGuestWordbook } = await import('@/composables/srsStorage')
      const bid = selectedBookId.value ?? srs.bookId ?? 0
      saveGuestWordbook(bid, loadGuestWordbook(bid).filter((id) => id !== item.word.id))
    }
    items.value = items.value.filter((i) => i.id !== item.id)
    ui.showToast('已掌握，从生词本移除')
  } catch {
    ui.showToast('操作失败')
  }
}

/** 不认识 → 保留并提升优先级（置顶） */
async function unknown(item: WordbookItem): Promise<void> {
  try {
    if (auth.isLoggedIn) {
      const { addWordbook } = await import('@/api/english')
      const bid = selectedBookId.value ?? srs.bookId ?? 0
      await addWordbook(item.word.id, bid) // 重新 add 会 touch updated_at 置顶
    } else {
      const { loadGuestWordbook, saveGuestWordbook } = await import('@/composables/srsStorage')
      const bid = selectedBookId.value ?? srs.bookId ?? 0
      const list = loadGuestWordbook(bid).filter((id) => id !== item.word.id)
      saveGuestWordbook(bid, [item.word.id, ...list])
    }
    ui.showToast('留在生词本，下次优先复习')
    await load()
  } catch {
    ui.showToast('操作失败')
  }
}

async function remove(item: WordbookItem): Promise<void> {
  try {
    if (auth.isLoggedIn) {
      await removeWordbook(item.id)
    } else {
      const { loadGuestWordbook, saveGuestWordbook } = await import('@/composables/srsStorage')
      const bid = selectedBookId.value ?? srs.bookId ?? 0
      saveGuestWordbook(bid, loadGuestWordbook(bid).filter((id) => id !== item.word.id))
    }
    items.value = items.value.filter((i) => i.id !== item.id)
    ui.showToast('已删除')
  } catch {
    ui.showToast('操作失败')
  }
}

async function clearAll(): Promise<void> {
  const bid = selectedBookId.value ?? srs.bookId
  if (!bid) return
  if (!window.confirm('确定清空生词本吗？此操作不可撤销。')) return
  try {
    if (auth.isLoggedIn) {
      await clearWordbook(bid)
    } else {
      const { saveGuestWordbook } = await import('@/composables/srsStorage')
      saveGuestWordbook(bid, [])
    }
    items.value = []
    ui.showToast('生词本已清空')
  } catch {
    ui.showToast('操作失败')
  }
}

function selectBook(id: number): void {
  selectedBookId.value = id
  load()
}

watch(
  () => srs.bookId,
  () => load(),
)

onMounted(async () => {
  await srs.init()
  load()
})
</script>

<template>
  <div>
    <div v-if="books.length" class="book-filter">
      <button
        type="button"
        class="book-filter-btn"
        :class="{ active: selectedBookId === null }"
        @click="selectedBookId = null; load()"
      >
        全部
      </button>
      <button
        v-for="b in books"
        :key="b.id"
        type="button"
        class="book-filter-btn"
        :class="{ active: selectedBookId === b.id }"
        @click="selectBook(b.id)"
      >
        {{ b.name }}
      </button>
    </div>

    <div v-if="loading" class="empty">加载中…</div>

    <div v-else-if="items.length === 0" class="empty">
      <div class="empty-icon"><BookOpen :size="28" :stroke-width="1.6" /></div>
      <div class="empty-text">生词本是空的，背单词时点「不认识」会自动收录</div>
    </div>

    <div v-else class="card">
      <div class="note-head">
        <span class="note-count">共 {{ items.length }} 个生词</span>
        <button class="btn btn-danger-soft btn-sm" type="button" @click="clearAll">一键清空</button>
      </div>
      <div v-for="item in items" :key="item.id" class="list-row">
        <div class="word-main">
          <div class="row-title">{{ item.word.word }}
            <span v-if="item.word.phonetic" class="phonetic">{{ item.word.phonetic }}</span>
          </div>
          <div class="row-sub">{{ item.word.definition }}</div>
        </div>
        <div class="word-actions">
          <button class="btn btn-ghost btn-sm" type="button" title="还不认识，下次优先复习" @click="unknown(item)">不认识</button>
          <button class="btn btn-success btn-sm" type="button" title="认识了，移出生词本" @click="known(item)">认识</button>
          <button class="btn btn-danger-soft btn-sm" type="button" @click="remove(item)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.book-filter {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.book-filter-btn {
  padding: 6px 16px;
  border: 1px solid var(--border-2);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text-2);
  font-size: 13px;
  transition: all 0.18s ease;
}

.book-filter-btn.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 600;
}

.note-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
}

.note-count {
  font-size: 13px;
  color: var(--text-2);
}

.word-main {
  flex: 1;
  min-width: 0;
}

.phonetic {
  font-size: 13px;
  color: var(--text-3);
  font-weight: 400;
  margin-left: 8px;
}

.word-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}
</style>
