<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Music, Volume2, VolumeX } from 'lucide-vue-next'

/**
 * 晨间氛围音 · Ambient Music
 *
 * 用 Web Audio API 实时合成轻柔的钢琴琶音 + 温暖和声垫底，
 * 无需外部音频文件，离线可用。和声进行选用宁静的大调色彩
 * （C → Am → F → G），与「晨光森林」主题呼应。
 *
 * 浏览器自动播放策略要求用户手势后才能出声，因此默认静默，
 * 首次点击播放按钮（或用户上次开启后首次任意点击）时启动。
 */

const STORAGE_KEY = 'ccqy_ambient_music'

const playing = ref(false)
const panelOpen = ref(false)
const volume = ref(0.5)

const AC =
  typeof window !== 'undefined'
    ? window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    : undefined
const supported = ref(Boolean(AC))

let ctx: AudioContext | null = null
let master: GainNode | null = null
let arpTimer: number | null = null
let chordIdx = 0

interface Pref {
  volume: number
  enabled: boolean
}

// ── 音符名 → 频率（440Hz 十二平均律）────────────────────────────
const SEMI = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
function noteFreq(name: string): number {
  const m = /^([A-G]#?)(\d)$/.exec(name)
  if (!m) return 0
  const midi = SEMI.indexOf(m[1]!) + (parseInt(m[2]!, 10) + 1) * 12
  return 440 * Math.pow(2, (midi - 69) / 12)
}

// ── 宁静的和弦进行：C → Am → F → G ─────────────────────────────
// arp 为琶音音符（低音先行），pad 为垫底和声
const CHORDS = [
  { arp: ['C3', 'E4', 'G4', 'B4'], pad: ['C3', 'G3', 'E4'] },
  { arp: ['A2', 'E4', 'A3', 'C4'], pad: ['A2', 'E3', 'C4'] },
  { arp: ['F2', 'C4', 'F3', 'A3'], pad: ['F2', 'C3', 'A3'] },
  { arp: ['G2', 'D4', 'G3', 'B3'], pad: ['G2', 'D3', 'B3'] },
]

function ensureCtx(): AudioContext | null {
  if (!AC) return null
  if (!ctx) {
    ctx = new AC()
    master = ctx.createGain()
    master.gain.value = 0
    master.connect(ctx.destination)
  }
  if (ctx.state === 'suspended') void ctx.resume()
  return ctx
}

/** 钢琴式音符：基频 + 柔和泛音，快起音、缓慢衰减 */
function pluck(freq: number, when: number, peak = 0.11) {
  if (!ctx || !master) return
  const g = ctx.createGain()
  const osc = ctx.createOscillator()
  const osc2 = ctx.createOscillator()
  const g2 = ctx.createGain()
  osc.type = 'sine'
  osc.frequency.value = freq
  osc2.type = 'sine'
  osc2.frequency.value = freq * 2
  g2.gain.value = 0.35
  g.gain.setValueAtTime(0.0001, when)
  g.gain.exponentialRampToValueAtTime(peak, when + 0.02)
  g.gain.exponentialRampToValueAtTime(0.0001, when + 2.2)
  osc.connect(g)
  osc2.connect(g2)
  g2.connect(g)
  g.connect(master)
  osc.start(when)
  osc2.start(when)
  osc.stop(when + 2.4)
  osc2.stop(when + 2.4)
}

/** 温暖 pad：低音量持续和声，低通滤波柔化 */
function playPad(freqs: string[]) {
  if (!ctx || !master) return
  for (const f of freqs) {
    const osc = ctx.createOscillator()
    const flt = ctx.createBiquadFilter()
    const g = ctx.createGain()
    osc.type = 'triangle'
    osc.frequency.value = noteFreq(f)
    flt.type = 'lowpass'
    flt.frequency.value = 900
    g.gain.setValueAtTime(0.0001, ctx.currentTime)
    g.gain.exponentialRampToValueAtTime(0.045, ctx.currentTime + 1.2)
    g.gain.setValueAtTime(0.045, ctx.currentTime + 4.6)
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 6.4)
    osc.connect(flt)
    flt.connect(g)
    g.connect(master)
    osc.start()
    osc.stop(ctx.currentTime + 6.6)
  }
}

function scheduleNext() {
  if (!ctx) return
  const chord = CHORDS[chordIdx]!
  chordIdx = (chordIdx + 1) % CHORDS.length
  const t0 = ctx.currentTime + 0.05
  playPad(chord.pad)
  chord.arp.forEach((n, i) => pluck(noteFreq(n), t0 + i * 0.9, i === 0 ? 0.13 : 0.1))
}

function startLoop() {
  if (!ctx) return
  scheduleNext()
  arpTimer = window.setTimeout(() => startLoop(), 4100)
}

function start() {
  const ac = ensureCtx()
  if (!ac || !master) return
  if (playing.value) return
  playing.value = true
  if (!arpTimer) startLoop()
  // exponentialRamp 起始值不能为 0，先钳到极小正值再渐变
  master.gain.cancelScheduledValues(ac.currentTime)
  master.gain.setValueAtTime(Math.max(master.gain.value, 0.0001), ac.currentTime)
  master.gain.exponentialRampToValueAtTime(Math.max(volume.value, 0.01), ac.currentTime + 1.2)
  save()
}

function stop() {
  if (!ctx || !master) return
  playing.value = false
  if (arpTimer) {
    clearTimeout(arpTimer)
    arpTimer = null
  }
  master.gain.cancelScheduledValues(ctx.currentTime)
  master.gain.setValueAtTime(Math.max(master.gain.value, 0.0001), ctx.currentTime)
  master.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.8)
  save()
}

function toggle() {
  if (playing.value) stop()
  else start()
}

function setVolume(v: number) {
  volume.value = v
  if (ctx && master) {
    master.gain.cancelScheduledValues(ctx.currentTime)
    master.gain.setTargetAtTime(v, ctx.currentTime, 0.1)
  }
  save()
}

function save() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ volume: volume.value, enabled: playing.value } satisfies Pref),
    )
  } catch {
    /* 忽略存储失败 */
  }
}

function restore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const pref = JSON.parse(raw) as Pref
    if (typeof pref.volume === 'number') volume.value = pref.volume
    if (pref.enabled) {
      // 自动播放需用户手势：等首次交互后自动续播
      const boot = () => {
        start()
        window.removeEventListener('pointerdown', boot)
      }
      window.addEventListener('pointerdown', boot)
    }
  } catch {
    /* 忽略损坏的存储 */
  }
}

onMounted(restore)
onBeforeUnmount(() => {
  if (arpTimer) clearTimeout(arpTimer)
  if (ctx) void ctx.close()
})
</script>

<template>
  <div v-if="supported" class="ambient">
    <!-- 音量面板 -->
    <transition name="fade">
      <div v-if="panelOpen" class="ambient-panel">
        <span class="ambient-label">氛围音量</span>
        <input
          class="volume-range"
          type="range"
          min="0"
          max="1"
          step="0.01"
          :value="volume"
          @input="setVolume(parseFloat(($event.target as HTMLInputElement).value))"
        />
      </div>
    </transition>

    <!-- 悬浮控制条 -->
    <div class="ambient-dock">
      <button
        class="ambient-toggle"
        :class="{ playing }"
        type="button"
        :title="playing ? '暂停晨间氛围音' : '播放晨间氛围音'"
        :aria-pressed="playing"
        @click="toggle"
      >
        <span v-if="playing" class="eq" aria-hidden="true"><i></i><i></i><i></i></span>
        <Music v-else :size="17" :stroke-width="1.8" />
      </button>
      <button
        class="ambient-vol"
        :class="{ open: panelOpen }"
        type="button"
        :title="panelOpen ? '收起音量' : '调节音量'"
        @click="panelOpen = !panelOpen"
      >
        <VolumeX v-if="volume === 0" :size="15" :stroke-width="1.8" />
        <Volume2 v-else :size="15" :stroke-width="1.8" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.ambient-dock {
  position: fixed;
  right: 24px;
  bottom: 96px;
  z-index: 920;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px;
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--border);
  border-radius: 999px;
  box-shadow: var(--shadow);
}

.ambient-toggle,
.ambient-vol {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--text-2);
  border-radius: 999px;
  transition: color 0.18s ease, background 0.18s ease;
}

.ambient-toggle {
  width: 34px;
  height: 34px;
}

.ambient-vol {
  width: 28px;
  height: 28px;
}

.ambient-toggle:hover,
.ambient-vol:hover {
  color: var(--primary);
  background: var(--primary-soft);
}

.ambient-vol.open {
  color: var(--primary);
  background: var(--primary-soft);
}

/* 播放中：柔光呼吸 + 声波动画 */
.ambient-toggle.playing {
  color: var(--primary);
  background: var(--primary-soft);
  animation: breathe 3.2s ease-in-out infinite;
}

@keyframes breathe {
  0%,
  100% {
    box-shadow: 0 0 0 0 var(--sun-soft);
  }
  50% {
    box-shadow: 0 0 0 12px transparent;
  }
}

.eq {
  display: inline-flex;
  align-items: flex-end;
  gap: 2.5px;
  height: 14px;
}

.eq i {
  width: 3px;
  border-radius: 2px;
  background: var(--primary);
  animation: eq-bounce 1.6s ease-in-out infinite;
}

.eq i:nth-child(2) {
  animation-delay: 0.3s;
}

.eq i:nth-child(3) {
  animation-delay: 0.6s;
}

@keyframes eq-bounce {
  0%,
  100% {
    height: 5px;
  }
  50% {
    height: 13px;
  }
}

/* 音量面板 */
.ambient-panel {
  position: fixed;
  right: 24px;
  bottom: 148px;
  z-index: 920;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: var(--shadow-lg);
}

.ambient-label {
  font-size: 12px;
  color: var(--text-2);
  white-space: nowrap;
}

.volume-range {
  width: 140px;
  accent-color: var(--primary);
  cursor: pointer;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@media (max-width: 480px) {
  .ambient-dock,
  .ambient-panel {
    right: 16px;
  }
}
</style>
