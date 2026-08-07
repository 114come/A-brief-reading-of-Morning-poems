<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NotebookPen } from 'lucide-vue-next'
import { createNote, deleteNote, listArticles, listNotes, updateNote } from '@/api/english'
import { useUiStore } from '@/stores/ui'
import type { ArticleItem, Note } from '@/types'

const ui = useUiStore()
const loading = ref(false)
const notes = ref<Note[]>([])
const articles = ref<ArticleItem[]>([])

// 新建
const showForm = ref(false)
const articleId = ref<number | null>(null)
const newContent = ref('')

// 编辑
const editingId = ref<number | null>(null)
const editContent = ref('')

async function load(): Promise<void> {
  loading.value = true
  try {
    notes.value = await listNotes()
    articles.value = await listArticles()
  } catch {
    ui.showToast('加载笔记失败')
  } finally {
    loading.value = false
  }
}

async function submitNew(): Promise<void> {
  if (!articleId.value || !newContent.value.trim()) {
    ui.showToast('请选择文章并填写笔记内容')
    return
  }
  try {
    await createNote(articleId.value, newContent.value.trim())
    newContent.value = ''
    articleId.value = null
    showForm.value = false
    ui.showToast('笔记已保存')
    await load()
  } catch {
    ui.showToast('保存失败，可能该文章已有笔记')
  }
}

function startEdit(note: Note): void {
  editingId.value = note.id
  editContent.value = note.content
}

async function saveEdit(note: Note): Promise<void> {
  if (!editContent.value.trim()) {
    ui.showToast('内容不能为空')
    return
  }
  try {
    await updateNote(note.id, editContent.value.trim())
    ui.showToast('笔记已更新')
    await load()
  } finally {
    editingId.value = null
  }
}

async function remove(note: Note): Promise<void> {
  try {
    await deleteNote(note.id)
    notes.value = notes.value.filter((n) => n.id !== note.id)
    ui.showToast('笔记已删除')
  } catch {
    ui.showToast('删除失败')
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div v-if="loading" class="empty">加载中…</div>

    <template v-else>
      <div class="card card-pad note-form" v-if="showForm">
        <div class="field-label">选择文章</div>
        <select v-model.number="articleId" class="input">
          <option :value="null" disabled>请选择一篇已读文章</option>
          <option v-for="a in articles" :key="a.id" :value="a.id">{{ a.title }}</option>
        </select>
        <div class="field-label" style="margin-top: 14px">笔记内容</div>
        <textarea v-model="newContent" class="input" rows="4" placeholder="记录生词、好句和你的感想…"></textarea>
        <div class="form-actions">
          <button class="btn btn-ghost btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-primary btn-sm" type="button" @click="submitNew">保存笔记</button>
        </div>
      </div>

      <div v-if="notes.length === 0" class="empty">
        <div class="empty-icon"><NotebookPen :size="28" :stroke-width="1.6" /></div>
        <div class="empty-text">还没有阅读笔记</div>
        <button v-if="!showForm" class="btn btn-primary btn-sm" type="button" @click="showForm = true">新建笔记</button>
      </div>

      <div v-else class="card">
        <div class="note-head">
          <span class="note-count">共 {{ notes.length }} 条笔记</span>
          <button class="btn btn-soft btn-sm" type="button" @click="showForm = !showForm">
            {{ showForm ? '收起' : '新建笔记' }}
          </button>
        </div>
        <div v-for="note in notes" :key="note.id" class="list-row note-item">
          <div class="note-main">
            <div class="row-title">{{ note.article_title || `文章 #${note.article_id}` }}</div>
            <textarea
              v-if="editingId === note.id"
              v-model="editContent"
              class="input note-content"
              rows="3"
            ></textarea>
            <p v-else class="note-content">{{ note.content }}</p>
            <div class="row-sub note-time">{{ new Date(note.updated_at).toLocaleString() }}</div>
          </div>
          <div class="note-actions">
            <template v-if="editingId === note.id">
              <button class="btn btn-ghost btn-sm" type="button" @click="editingId = null">取消</button>
              <button class="btn btn-primary btn-sm" type="button" @click="saveEdit(note)">保存</button>
            </template>
            <template v-else>
              <button class="btn btn-ghost btn-sm" type="button" @click="startEdit(note)">编辑</button>
              <button class="btn btn-danger-soft btn-sm" type="button" @click="remove(note)">删除</button>
            </template>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.note-form {
  margin-bottom: 16px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
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

.note-main {
  flex: 1;
  min-width: 0;
}

.note-content {
  margin-top: 6px;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text);
}

.note-time {
  font-size: 12px;
}

.note-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}
</style>
