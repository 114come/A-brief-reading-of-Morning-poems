<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { Star } from 'lucide-vue-next'
import { listCollections, removeCollection } from '@/api/english'
import { useUiStore } from '@/stores/ui'
import type { CollectionItem } from '@/types'

const props = defineProps<{
  /** 不传则展示全部类型（/collect）；传 listening/reading 则过滤 */
  itemType?: 'word' | 'listening' | 'reading'
}>()

const ui = useUiStore()
const loading = ref(false)
const items = ref<CollectionItem[]>([])

const TYPE_LABEL: Record<string, { label: string; cls: string }> = {
  word: { label: '单词', cls: 'tag-primary' },
  listening: { label: '听力', cls: 'tag-success' },
  reading: { label: '文章', cls: 'tag' },
}

async function load(): Promise<void> {
  loading.value = true
  try {
    items.value = await listCollections(props.itemType)
  } catch {
    ui.showToast('加载收藏失败')
  } finally {
    loading.value = false
  }
}

async function remove(item: CollectionItem): Promise<void> {
  try {
    await removeCollection(item.id)
    items.value = items.value.filter((i) => i.id !== item.id)
    ui.showToast('已取消收藏')
  } catch {
    ui.showToast('操作失败')
  }
}

onMounted(load)
watch(() => props.itemType, load)
</script>

<template>
  <div>
    <div v-if="loading" class="empty">加载中…</div>

    <div v-else-if="items.length === 0" class="empty">
      <div class="empty-icon"><Star :size="28" :stroke-width="1.6" /></div>
      <div class="empty-text">暂无收藏内容</div>
    </div>

    <div v-else class="card">
      <div v-for="item in items" :key="item.id" class="list-row">
        <div class="fav-main">
          <div class="row-title">{{ item.title || `#${item.item_id}` }}</div>
          <div v-if="item.subtitle" class="row-sub">{{ item.subtitle }}</div>
        </div>
        <span v-if="!props.itemType" class="tag" :class="TYPE_LABEL[item.item_type]?.cls || 'tag'">
          {{ TYPE_LABEL[item.item_type]?.label || item.item_type }}
        </span>
        <span class="fav-time">{{ new Date(item.created_at).toLocaleDateString() }}</span>
        <button class="btn btn-danger-soft btn-sm" type="button" @click="remove(item)">取消收藏</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fav-main {
  flex: 1;
  min-width: 0;
}

.fav-time {
  font-size: 12px;
  color: var(--text-3);
  white-space: nowrap;
}
</style>
