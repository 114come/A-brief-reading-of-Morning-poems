<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useRewardsStore } from '@/stores/rewards'
import { TITLE_META } from '@/constants/titles'

const auth = useAuthStore()
const rewards = useRewardsStore()
const route = useRoute()
const router = useRouter()

const open = ref(false)
let hideTimer: ReturnType<typeof setTimeout> | null = null

/** 头像展示：http 链接显示图片，其余作为文本（首字母/emoji） */
const avatarText = computed(() => {
  if (auth.user?.avatar && !auth.user.avatar.startsWith('http')) return auth.user.avatar.slice(0, 2)
  const name = auth.user?.nickname || auth.user?.username || 'U'
  return name.slice(0, 1).toUpperCase()
})

const displayName = computed(() => auth.user?.nickname || auth.user?.username || '')

const titleName = computed(() => {
  const key = rewards.overview?.equipped_title
  return key ? TITLE_META[key] || key : ''
})

onMounted(() => {
  if (auth.isLoggedIn) {
    rewards.loadOverview().catch(() => {})
  }
})

const menuItems = [
  { label: '我的生词本', to: '/word/notebook', dividerBefore: false },
  { label: '我的收藏', to: '/collect', dividerBefore: false },
  { label: '阅读笔记', to: '/reading/note', dividerBefore: false },
  { label: '打卡数据', to: '/study-center/checkin', dividerBefore: false },
  { label: '账号设置', to: '/user/setting', dividerBefore: true },
]

function openMenu(): void {
  if (hideTimer) clearTimeout(hideTimer)
  open.value = true
}

function scheduleClose(): void {
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => {
    open.value = false
  }, 1500)
}

function go(to: string): void {
  open.value = false
  router.push(to)
}

function handleLogout(): void {
  open.value = false
  auth.logout()
}

// 路由变化即收起菜单
watch(
  () => route.path,
  () => {
    open.value = false
  },
)

onBeforeUnmount(() => {
  if (hideTimer) clearTimeout(hideTimer)
})
</script>

<template>
  <div class="user-area">
    <!-- 游客态 -->
    <template v-if="!auth.isLoggedIn">
      <RouterLink to="/login" class="btn btn-ghost btn-sm">登录</RouterLink>
      <RouterLink to="/register" class="btn btn-primary btn-sm">注册</RouterLink>
    </template>

    <!-- 登录态：头像 + 昵称 + 下拉 -->
    <div
      v-else
      class="user-dropdown"
      @mouseenter="openMenu"
      @mouseleave="scheduleClose"
    >
      <button class="user-trigger" type="button">
        <span class="avatar">
          <img
            v-if="auth.user?.avatar && auth.user.avatar.startsWith('http')"
            :src="auth.user.avatar"
            alt="avatar"
          />
          <span v-else>{{ avatarText }}</span>
        </span>
        <span class="nickname">{{ displayName }}</span>
        <span v-if="titleName" class="user-title">{{ titleName }}</span>
        <ChevronDown
          class="caret"
          :class="{ flip: open }"
          :size="14"
          :stroke-width="2"
        />
      </button>

      <transition name="dropdown">
        <ul v-if="open" class="user-menu">
          <li v-for="item in menuItems" :key="item.to">
            <span v-if="item.dividerBefore" class="menu-divider"></span>
            <button class="menu-item" type="button" @click="go(item.to)">{{ item.label }}</button>
          </li>
          <li>
            <span class="menu-divider"></span>
            <button class="menu-item danger" type="button" @click="handleLogout">退出登录</button>
          </li>
        </ul>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.user-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-dropdown {
  position: relative;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 4px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.user-trigger:hover {
  border-color: var(--primary);
  box-shadow: 0 2px 10px var(--primary-soft);
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.nickname {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.caret {
  width: 14px;
  height: 14px;
  color: var(--text-3);
  transition: transform 0.2s ease;
}

.user-title {
  font-size: 11px;
  color: var(--sun);
  border: 1px solid var(--sun-soft);
  border-radius: 999px;
  padding: 1px 8px;
  background: var(--sun-soft);
  white-space: nowrap;
}

@media (max-width: 768px) {
  .user-title {
    display: none;
  }
}

.caret.flip {
  transform: rotate(180deg);
}

/* 下拉菜单 */
.user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 168px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  padding: 6px;
  z-index: 100;
}

.menu-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 9px 14px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 14px;
  color: var(--text);
  transition: background 0.15s ease, color 0.15s ease;
}

.menu-item:hover {
  background: var(--primary-soft);
  color: var(--primary);
}

.menu-item.danger {
  color: var(--danger);
}

.menu-item.danger:hover {
  background: var(--danger-soft);
  color: var(--danger);
}

.menu-divider {
  display: block;
  height: 1px;
  margin: 5px 4px;
  background: var(--border);
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
