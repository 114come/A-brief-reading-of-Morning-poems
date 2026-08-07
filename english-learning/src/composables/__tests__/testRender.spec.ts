import { describe, expect, it } from 'vitest'

/** 与 FillQuestion.vue 中 blankedExample 相同的逻辑（纯函数抽离便于测试） */
export function blankWordInExample(example: string, word: string): string {
  const re = new RegExp(`\\b${word}\\b`, 'gi')
  return example.replace(re, '_____')
}

describe('例句挖空渲染', () => {
  it('替换目标词为下划线', () => {
    expect(blankWordInExample('He had to abandon the plan.', 'abandon')).toBe('He had to _____ the plan.')
  })

  it('大小写不敏感', () => {
    expect(blankWordInExample('Abandon the plan.', 'abandon')).toBe('_____ the plan.')
  })

  it('不影响其它词', () => {
    const out = blankWordInExample('She can abandon but also adapt.', 'abandon')
    expect(out).toBe('She can _____ but also adapt.')
  })

  it('多个出现全部替换', () => {
    expect(blankWordInExample('abandon x and abandon y', 'abandon')).toBe('_____ x and _____ y')
  })
})
