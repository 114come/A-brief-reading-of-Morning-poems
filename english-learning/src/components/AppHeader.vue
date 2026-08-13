<script setup lang="ts">
import { computed, ref } from 'vue'
import { BookOpen, Menu, X } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import ThemeToggle from './ThemeToggle.vue'
import UserArea from './UserArea.vue'

const route = useRoute()
const mobileOpen = ref(false)

const navItems = [
  { label: '首页', to: '/home' },
  { label: '词笺', to: '/word' },
  { label: '浅读', to: '/reading' },
  { label: '归处', to: '/study-center' },
]

function isActive(to: string): boolean {
  if (to === '/home') return route.path === '/home'
  return route.path === to || route.path.startsWith(`${to}/`)
}

const activeLabel = computed(() => navItems.find((i) => isActive(i.to))?.label || '')

function closePanel(): void {
  mobileOpen.value = false
}
</script>

<template>
  <header class="app-header">
    <div class="container header-inner">
      <!-- Logo -->
      <RouterLink to="/home" class="logo" @click="closePanel">
        <span class="logo-badge"><BookOpen :size="16" :stroke-width="2" /></span>
        <span class="logo-text">朝词浅阅</span>
      </RouterLink>

      <!-- 主导航（桌面） -->
      <nav class="main-nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <!-- 空白留白 -->
      <div class="spacer"></div>

      <!-- 桌面右侧：主题 + 账号 -->
      <div class="desktop-right">
        <ThemeToggle />
        <UserArea />
      </div>

      <!-- 移动端汉堡 -->
      <button
        class="hamburger"
        type="button"
        :aria-label="mobileOpen ? '关闭菜单' : '打开菜单'"
        :aria-expanded="mobileOpen"
        @click="mobileOpen = !mobileOpen"
      >
        <X v-if="mobileOpen" :size="20" :stroke-width="1.8" />
        <Menu v-else :size="20" :stroke-width="1.8" />
      </button>
    </div>

    <!-- 移动端面板 -->
    <transition name="panel">
      <div v-if="mobileOpen" class="mobile-panel">
        <nav class="mobile-nav">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="mobile-nav-item"
            :class="{ active: isActive(item.to) }"
            @click="closePanel"
          >
            {{ item.label }}
          </RouterLink>
        </nav>
        <div class="mobile-foot">
          <span class="mobile-current">{{ activeLabel || '首页' }}</span>
          <ThemeToggle />
        </div>
        <div class="mobile-user">
          <UserArea />
        </div>
      </div>
    </transition>
  </header>
</template>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--header-height);
  background: color-mix(in srgb, var(--surface) 86%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  z-index: 999;
}

.header-inner {
  height: 100%;
  display: flex;
  align-items: center;
  gap: 24px;
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.logo-badge {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: var(--brand-gradient);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 10px var(--sun-soft);
}

.logo-text {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

/* 主导航 */
.main-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.nav-item {
  position: relative;
  padding: 8px 16px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-2);
  transition: color 0.18s ease;
}

.nav-item:hover {
  color: var(--text);
}

.nav-item.active {
  color: var(--primary);
  font-weight: 600;
}

.nav-item.active::after {
  content: '';
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 2px;
  height: 2px;
  border-radius: 999px;
  background: var(--brand-gradient);
}

/* 留白 */
.spacer {
  flex: 1;
}

.desktop-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 汉堡按钮（默认隐藏） */
.hamburger {
  display: none;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-2);
}

.hamburger:hover {
  color: var(--primary);
  border-color: var(--primary);
}

/* 移动端面板 */
.mobile-panel {
  position: fixed;
  top: var(--header-height);
  left: 0;
  right: 0;
  z-index: 998;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow);
  padding: 12px 20px 20px;
}

.mobile-nav {
  display: flex;
  flex-direction: column;
}

.mobile-nav-item {
  padding: 13px 8px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-2);
  border-radius: 8px;
  transition: all 0.15s ease;
}

.mobile-nav-item.active {
  color: var(--primary);
  font-weight: 600;
  background: var(--primary-soft);
}

.mobile-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  padding: 12px 8px 4px;
  border-top: 1px solid var(--border);
}

.mobile-current {
  font-size: 13px;
  color: var(--text-3);
}

.mobile-user {
  padding: 8px;
}

/* 面板动画 */
.panel-enter-active,
.panel-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .main-nav,
  .desktop-right {
    display: none;
  }

  .hamburger {
    display: inline-flex;
  }
}
</style>
