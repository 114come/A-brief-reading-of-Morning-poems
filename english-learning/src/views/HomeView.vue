<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ArrowRight, BookMarked, BookOpenText, Compass } from 'lucide-vue-next'
import { getStudyStats } from '@/api/english'
import { useAuthStore } from '@/stores/auth'
import type { StudyStats } from '@/types'

const auth = useAuthStore()
const stats = ref<StudyStats | null>(null)

const features = [
  { to: '/word', icon: BookMarked, title: '词笺', desc: '词库背诵 + 生词本复习', tone: 'primary' },
  { to: '/reading', icon: BookOpenText, title: '浅读', desc: '每日短文 + 阅读笔记', tone: 'accent' },
  { to: '/study-center', icon: Compass, title: '归处', desc: '每日打卡 + 数据总览', tone: 'sage' },
]

onMounted(async () => {
  if (auth.isLoggedIn) {
    try {
      stats.value = await getStudyStats()
    } catch {
      /* 忽略 */
    }
  }
})
</script>

<template>
  <div class="container">
    <!-- Hero：纯排版，留白撑高级感 -->
    <section class="hero">
      <div class="hero-rule"></div>
      <p class="hero-eyebrow">朝词浅阅 · English Learning</p>
      <h1 class="hero-title">每天进步一点点</h1>
      <p class="hero-desc">把英语学习变成习惯。</p>
      <div class="hero-actions">
        <RouterLink to="/word" class="btn btn-primary">
          开始背单词
          <ArrowRight :size="16" />
        </RouterLink>
        <RouterLink to="/reading" class="btn btn-ghost">去读一篇</RouterLink>
      </div>
    </section>

    <!-- 功能入口 -->
    <section class="feature-grid">
      <RouterLink
        v-for="f in features"
        :key="f.to"
        :to="f.to"
        class="card feature-card"
      >
        <div class="feature-icon" :class="`tone-${f.tone}`">
          <component :is="f.icon" :size="22" :stroke-width="1.8" />
        </div>
        <div class="feature-title">{{ f.title }}</div>
        <div class="feature-desc">{{ f.desc }}</div>
      </RouterLink>
    </section>

    <!-- 已登录：学习数据速览 -->
    <section v-if="auth.isLoggedIn && stats" class="card card-pad home-stats">
      <h2 class="section-title">我的学习概况</h2>
      <div class="stat-grid">
        <div class="stat-mini"><span class="num">{{ stats.wordbook_count }}</span><span class="lbl">生词本</span></div>
        <div class="stat-mini"><span class="num">{{ stats.mastered_count }}</span><span class="lbl">已掌握</span></div>
        <div class="stat-mini"><span class="num">{{ stats.checkin_total }}</span><span class="lbl">打卡天数</span></div>
        <div class="stat-mini"><span class="num">{{ stats.favorite_count }}</span><span class="lbl">收藏</span></div>
        <div class="stat-mini"><span class="num">{{ stats.note_count }}</span><span class="lbl">阅读笔记</span></div>
      </div>
      <div style="margin-top: 24px">
        <RouterLink to="/study-center" class="btn btn-soft btn-sm">查看详细数据</RouterLink>
      </div>
    </section>

    <!-- 游客：登录提示 -->
    <section v-else-if="!auth.isLoggedIn" class="card card-pad guest-call">
      <div>
        <div class="guest-title">登录后同步所有学习记录</div>
        <p class="guest-desc">生词本、收藏、阅读笔记和打卡数据，都会为你保存。</p>
      </div>
      <div class="guest-actions">
        <RouterLink to="/register" class="btn btn-primary">免费注册</RouterLink>
        <RouterLink to="/login" class="btn btn-ghost">登录</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ── Hero ── */
.hero {
  position: relative;
  overflow: hidden;
  padding: 76px 40px 66px;
  text-align: center;
  background: var(--sunrise-glow),
    linear-gradient(180deg, var(--primary-soft), transparent 72%);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border);
}

/* 晨光弧线：hero 顶部一道柔和的金色地平线 */
.hero::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 120px;
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, var(--sun), transparent);
  opacity: 0.7;
}

.hero-rule {
  width: 40px;
  height: 3px;
  border-radius: 999px;
  background: var(--brand-gradient);
  margin: 0 auto 24px;
}

.hero-eyebrow {
  font-size: var(--fs-sm);
  font-weight: 500;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 16px;
}

.hero-title {
  font-family: var(--font-display);
  font-size: var(--fs-hero);
  font-weight: 600;
  letter-spacing: 0.04em;
  line-height: 1.25;
}

.hero-desc {
  margin-top: 12px;
  font-size: var(--fs-md);
  color: var(--text-2);
}

.hero-actions {
  margin-top: 32px;
  display: flex;
  justify-content: center;
  gap: 12px;
}

/* ── 功能入口 ── */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-top: 24px;
}

.feature-card {
  padding: 28px 24px;
  transition: transform var(--t-fast), box-shadow var(--t-fast);
}

.feature-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow);
}

.feature-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.tone-primary {
  background: var(--primary-soft);
  color: var(--primary);
}

.tone-accent {
  background: var(--accent-soft);
  color: var(--accent);
}

.tone-sage {
  background: var(--success-soft);
  color: var(--success);
}

.feature-title {
  font-size: 17px;
  font-weight: 600;
}

.feature-desc {
  margin-top: 4px;
  font-size: var(--fs-sm);
  color: var(--text-2);
}

/* ── 学习概况 ── */
.home-stats {
  margin-top: 24px;
}

.section-title {
  font-size: var(--fs-lg);
  font-weight: 600;
  margin-bottom: 20px;
}

.stat-mini {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-mini .num {
  font-size: 26px;
  font-weight: 700;
  color: var(--primary);
}

.stat-mini .lbl {
  font-size: var(--fs-sm);
  color: var(--text-2);
}

/* ── 游客提示 ── */
.guest-call {
  margin-top: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.guest-title {
  font-size: 17px;
  font-weight: 600;
}

.guest-desc {
  margin-top: 4px;
  font-size: var(--fs-sm);
  color: var(--text-2);
}

.guest-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .hero {
    padding: 48px 24px 44px;
  }

  .hero-title {
    font-size: var(--fs-3xl);
  }

  .feature-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .guest-call {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
