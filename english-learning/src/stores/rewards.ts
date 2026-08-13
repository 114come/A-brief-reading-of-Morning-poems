import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  collectRewards,
  equipReward,
  getRewardsOverview,
  getRewardsShop,
  redeemReward,
} from '@/api/english'
import type { CollectResult, RewardOverview, ShopItem } from '@/types'

export const useRewardsStore = defineStore('rewards', () => {
  const overview = ref<RewardOverview | null>(null)
  const shop = ref<ShopItem[]>([])
  const loading = ref(false)

  async function loadOverview() {
    overview.value = await getRewardsOverview()
  }

  async function loadShop() {
    shop.value = await getRewardsShop()
  }

  async function collect(): Promise<CollectResult> {
    const result = await collectRewards()
    await loadOverview()
    return result
  }

  async function redeem(itemKey: string) {
    await redeemReward(itemKey)
    await Promise.all([loadOverview(), loadShop()])
  }

  async function equip(itemKey: string | null) {
    await equipReward(itemKey)
    await loadOverview()
  }

  return { overview, shop, loading, loadOverview, loadShop, collect, redeem, equip }
})
