/**
 * 奖励结算 · 统一入口
 *
 * 学习行为完成后调用 collectAndNotify()：
 * 1. 调后端 /rewards/collect 结算当日任务积分（幂等，后端保证每日一次）
 * 2. 积分到账 → 浮层动效 + toast
 * 3. 里程碑达成 → 庆祝弹窗
 *
 * 组件（有组件树上下文）用 inject 拿浮层实例；store 层不适用（无 inject），
 * 用单独导出的 collectQuiet() 静默结算 + 文字提示。
 */
import { inject } from 'vue'
import type { Ref } from 'vue'
import { useRewardsStore } from '@/stores/rewards'
import { useUiStore } from '@/stores/ui'
import type PointToast from '@/components/PointToast.vue'
import type RewardCelebrationModal from '@/components/RewardCelebrationModal.vue'

const MILESTONE_LABELS: Record<string, string> = {
  milestone_7: '习惯正在发芽',
  milestone_30: '你已走出一条路',
  milestone_100: '百日铸就晨读人',
}

/** 静默结算（store 层用）：不弹浮层，仅文字提示 */
export async function collectQuiet(): Promise<{ earned_total: number }> {
  const rewards = useRewardsStore()
  const ui = useUiStore()
  try {
    const result = await rewards.collect()
    if (result.earned_total > 0) {
      ui.showToast(`奖励到账 +${result.earned_total} 分 · ${result.message}`)
    }
    return { earned_total: result.earned_total }
  } catch {
    /* 奖励结算失败不阻塞学习流程 */
    return { earned_total: 0 }
  }
}

/** 完整结算（组件层用）：浮层动效 + 里程碑庆祝弹窗 */
export function useRewardCollect() {
  const pointToast = inject<Ref<InstanceType<typeof PointToast> | null> | undefined>('pointToast')
  const celebrationModal = inject<Ref<InstanceType<typeof RewardCelebrationModal> | null> | undefined>(
    'celebrationModal',
  )

  async function collectAndNotify(): Promise<{ earned_total: number }> {
    const rewards = useRewardsStore()
    const ui = useUiStore()
    try {
      const result = await rewards.collect()
      if (result.earned_total > 0) {
        ui.showToast(`奖励到账 +${result.earned_total} 分 · ${result.message}`)
        pointToast?.value?.show(result.earned_total, result.message)
      }
      if (result.milestones.length > 0) {
        const m = result.milestones[0]!
        celebrationModal?.value?.show(
          MILESTONE_LABELS[m] || '里程碑达成',
          `${result.message} · 额外奖励已到账，去奖励站看看吧`,
        )
      }
      return { earned_total: result.earned_total }
    } catch {
      return { earned_total: 0 }
    }
  }

  return { collectAndNotify }
}
