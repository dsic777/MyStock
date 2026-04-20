/**
 * Web Audio API 알림음 — 외부 파일 없이 브라우저에서 직접 생성
 * 브라우저 자동재생 차단 대응: 공유 AudioContext + 사용자 첫 상호작용 시 unlock
 */

let _ctx = null

function getCtx() {
  if (!_ctx) {
    _ctx = new (window.AudioContext || window.webkitAudioContext)()
  }
  if (_ctx.state === 'suspended') {
    _ctx.resume()
  }
  return _ctx
}

/** 페이지 첫 클릭/터치 시 호출 — AudioContext 사전 unlock */
export function unlockAudio() {
  getCtx()
}

function beep(freq, duration, volume = 0.3, type = 'sine') {
  try {
    const ctx = getCtx()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.value = freq
    osc.type = type
    gain.gain.setValueAtTime(volume, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + duration)
  } catch (e) {
    console.warn('[사운드] 재생 실패:', e)
  }
}

/** 매도 알림음 — 긴박한 3연타 */
export function playSellAlert() {
  beep(880, 0.2, 0.4, 'square')
  setTimeout(() => beep(880, 0.2, 0.4, 'square'), 250)
  setTimeout(() => beep(1100, 0.4, 0.5, 'square'), 500)
}

/** 주의 알림음 — 단타 경고음 */
export function playWarnAlert() {
  beep(660, 0.3, 0.3, 'sine')
  setTimeout(() => beep(550, 0.3, 0.3, 'sine'), 350)
}

/** 매도 완료음 — 상쾌한 완료음 */
export function playSoldSound() {
  beep(523, 0.15, 0.3, 'sine')
  setTimeout(() => beep(659, 0.15, 0.3, 'sine'), 150)
  setTimeout(() => beep(784, 0.3, 0.3, 'sine'), 300)
}
