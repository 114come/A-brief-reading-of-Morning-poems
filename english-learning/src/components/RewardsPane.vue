<script setup lang="ts">
import { computed, inject, onMounted, ref } from 'vue'
import type { Ref } from 'vue'
import { Coins, Gift, Medal, Sparkles } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useRewardsStore } from '@/stores/rewards'
import { useRewardCollect } from '@/composables/rewardCollect'
import DailyQuote from './DailyQuote.vue'
import type RewardCelebrationModal from './RewardCelebrationModal.vue'
import type { ShopItem } from '@/types'

const auth = useAuthStore()
const store = useRewardsStore()
const { collectAndNotify } = useRewardCollect()
const activeTab = ref<'tasks' | 'shop'>('tasks')
const shopType = ref<'title' | 'decor' | 'egg'>('title')

const celebrationModal = inject<Ref<InstanceType<typeof RewardCelebrationModal> | null> | undefined>('celebrationModal')

const shopItems = computed(() => store.shop.filter((i) => i.type === shopType.value))

const hasUnclaimed = computed(() => store.overview?.tasks.some((t) => t.done && !t.earned) ?? false)

const claiming = ref(false)

async function onClaim(): Promise<void> {
  if (claiming.value) return
  claiming.value = true
  try {
    await collectAndNotify()
    await store.loadOverview()
  } finally {
    claiming.value = false
  }
}

async function onEquip(item: ShopItem): Promise<void> {
  const current = store.overview?.equipped_title
  await store.equip(current === item.item_key ? null : item.item_key)
}

async function onRedeem(item: ShopItem): Promise<void> {
  await store.redeem(item.item_key)
  celebrationModal?.value?.show(`解锁 · ${item.name}`, `${item.desc} · 花费 ${item.price} 分`)
}

onMounted(() => {
  if (auth.isLoggedIn) {
    store.loadOverview()
    store.loadShop()
  }
})
</script>

<template>
  <div v-if="store.overview" class="rewards">
    <!-- 积分卡 -->
    <div class="points-card">
      <div class="pc-left">
        <div class="pc-icon"><Coins :size="20" :stroke-width="1.8" /></div>
        <div>
          <div class="pc-label">当前积分</div>
          <div class="pc-balance">{{ store.overview.balance }}</div>
        </div>
      </div>
      <div class="pc-right">
        <div class="pc-stat">
          <span class="pc-num">{{ store.overview.streak_days }}</span>
          <span class="pc-cap">连续天数</span>
        </div>
        <div class="pc-stat">
          <span class="pc-num">{{ store.overview.today_earned }}</span>
          <span class="pc-cap">今日已得</span>
        </div>
        <div class="pc-stat">
          <span class="pc-num">{{ store.overview.total_earned }}</span>
          <span class="pc-cap">累计获得</span>
        </div>
      </div>
    </div>

    <DailyQuote :quote="store.overview.quote" :source="store.overview.quote_source" />

    <!-- Tab 切换 -->
    <div class="tabs reward-tabs">
      <button class="tab-item" :class="{ active: activeTab === 'tasks' }" type="button" @click="activeTab = 'tasks'">每日任务</button>
      <button class="tab-item" :class="{ active: activeTab === 'shop' }" type="button" @click="activeTab = 'shop'">兑换站</button>
    </div>

    <!-- 每日任务 -->
    <section v-if="activeTab === 'tasks'" class="task-list">
      <div v-for="t in store.overview.tasks" :key="t.key" class="card task-item" :class="{ done: t.done }">
        <span class="task-icon"><Medal :size="18" :stroke-width="1.8" /></span>
        <div class="task-main">
          <div class="task-name">{{ t.name }}</div>
          <div class="task-desc">{{ t.desc }}</div>
        </div>
        <div class="task-side">
          <span class="task-points">+{{ t.points }}</span>
          <span v-if="t.earned" class="tag tag-success">已领</span>
          <span v-else-if="t.done" class="tag">待领取</span>
        </div>
      </div>
      <button
        v-if="hasUnclaimed"
        class="btn btn-primary claim-btn"
        type="button"
        :disabled="claiming"
        @click="onClaim"
      >
        <Sparkles :size="15" :stroke-width="1.8" />
        {{ claiming ? '领取中…' : '一键领取全部奖励' }}
      </button>
      <p class="task-hint">完成任务后点此领取 · 完成学习行为也会自动到账 · 每天 0 点重置</p>
    </section>

    <!-- 兑换站 -->
    <section v-else class="shop">
      <div class="tabs shop-tabs">
        <button class="tab-item" :class="{ active: shopType === 'title' }" type="button" @click="shopType = 'title'">称号</button>
        <button class="tab-item" :class="{ active: shopType === 'decor' }" type="button" @click="shopType = 'decor'">装饰</button>
        <button class="tab-item" :class="{ active: shopType === 'egg' }" type="button" @click="shopType = 'egg'">彩蛋</button>
      </div>
      <div class="shop-grid">
        <div v-for="item in shopItems" :key="item.item_key" class="card shop-item">
          <div class="si-name">{{ item.name }}</div>
          <div class="si-desc">{{ item.desc }}</div>
          <div class="si-foot">
            <span class="si-price"><Gift :size="13" /> {{ item.price }} 分</span>
            <template v-if="item.type === 'title'">
              <button
                v-if="item.is_unlocked"
                class="btn btn-soft btn-sm"
                type="button"
                @click="onEquip(item)"
              >
                {{ store.overview.equipped_title === item.item_key ? '佩戴中' : '佩戴' }}
              </button>
              <button v-else class="btn btn-primary btn-sm" type="button" @click="onRedeem(item)">兑换</button>
            </template>
            <span v-else-if="item.is_unlocked" class="tag tag-success">已解锁</span>
            <button v-else class="btn btn-primary btn-sm" type="button" @click="onRedeem(item)">兑换</button>
          </div>
        </div>
      </div>
      <p class="task-hint">称号可佩戴显示在用户名旁 · 装饰与彩蛋解锁后生效</p>
    </section>
  </div>
</template>

<style scoped>
.rewards {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 积分卡 */
.points-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 28px;
  border-radius: var(--radius-xl);
  background: var(--brand-gradient);
  color: #fff;
  box-shadow: 0 12px 32px var(--sun-soft);
}
.pc-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.pc-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.18);
}
.pc-label {
  font-size: 12px;
  opacity: 0.85;
}
.pc-balance {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  line-height: 1.15;
}
.pc-right {
  display: flex;
  gap: 24px;
}
.pc-stat {
  text-align: center;
}
.pc-num {
  display: block;
  font-size: 20px;
  font-weight: 700;
}
.pc-cap {
  font-size: 11px;
  opacity: 0.85;
}

/* 任务 */
.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.task-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
}
.task-item.done .task-icon {
  background: var(--success-soft);
  color: var(--success);
}
.task-icon {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: var(--primary-soft);
  color: var(--primary);
}
.task-main {
  flex: 1;
}
.task-name {
  font-weight: 600;
}
.task-desc {
  font-size: var(--fs-sm);
  color: var(--text-2);
}
.task-side {
  display: flex;
  align-items: center;
  gap: 10px;
}
.task-points {
  font-weight: 700;
  color: var(--sun);
}
.task-hint {
  font-size: var(--fs-xs);
  color: var(--text-3);
  text-align: center;
}

.claim-btn {
  align-self: center;
  margin-top: 4px;
}

/* 兑换站 */
.shop-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}
.shop-item {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.si-name {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
}
.si-desc {
  font-size: var(--fs-sm);
  color: var(--text-2);
  flex: 1;
}
.si-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}
.si-price {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--sun);
}
.reward-tabs {
  margin-bottom: 0;
}

@media (max-width: 768px) {
  .points-card {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
