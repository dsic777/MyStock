import { useState, useEffect } from 'react'
import { authFetch } from '../utils/auth'

export default function Settings({ onClose }) {
  const [settings, setSettings] = useState(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    authFetch('/api/settings/')
      .then(r => r.json())
      .then(setSettings)
  }, [])

  const save = async () => {
    setSaving(true)
    setMsg('')
    try {
      const res = await authFetch('/api/settings/', {
        method: 'PUT',
        body: JSON.stringify(settings),
      })
      if (res.ok) setMsg('저장되었습니다!')
      else setMsg('저장 실패')
    } catch {
      setMsg('오류가 발생했습니다')
    } finally {
      setSaving(false)
    }
  }

  if (!settings) return <div style={{ padding: 20, textAlign: 'center', color: '#888' }}>불러오는 중...</div>

  const row = (label, field, step = 1) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 0', borderBottom: '1px solid #eee' }}>
      <span style={{ fontSize: 17, fontWeight: 700 }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <input
          type="number"
          step={step}
          value={settings[field]}
          onChange={e => setSettings({ ...settings, [field]: parseFloat(e.target.value) })}
          style={{ width: 80, fontSize: 17, fontWeight: 700, padding: '6px 10px', border: '1px solid #ccc', borderRadius: 8, textAlign: 'right' }}
        />
        <span style={{ fontSize: 15, color: '#888' }}>%</span>
      </div>
    </div>
  )

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'flex-end', justifyContent: 'center', zIndex: 100
    }}>
      <div style={{
        background: '#fff', borderRadius: '16px 16px 0 0',
        width: '100%', maxWidth: 600,
        maxHeight: '85vh', display: 'flex', flexDirection: 'column',
      }}>
        {/* 헤더 — 고정 */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '20px 20px 16px', borderBottom: '1px solid #eee', flexShrink: 0
        }}>
          <span style={{ fontSize: 20, fontWeight: 700 }}>⚙️ 설정</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: '#888' }}>✕</button>
        </div>
        {/* 스크롤 영역 */}
        <div style={{ overflowY: 'auto', padding: '0 20px 40px', flex: 1 }}>

        {/* 설정 항목 */}
        {row('개별주 트레일링 비율', 'default_trailing_rate')}
        {row('ETF 트레일링 비율', 'etf_trailing_rate')}
        {row('개별주 주의 알림 기준', 'warning_rate')}
        {row('ETF 주의 알림 기준', 'etf_warning_rate')}

        {/* 기본 매도모드 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 0', borderBottom: '1px solid #eee' }}>
          <span style={{ fontSize: 17, fontWeight: 700 }}>기본 매도모드</span>
          <select
            value={settings.default_sell_mode}
            onChange={e => setSettings({ ...settings, default_sell_mode: e.target.value })}
            style={{ fontSize: 16, fontWeight: 700, padding: '6px 10px', border: '1px solid #ccc', borderRadius: 8 }}
          >
            <option value="확인">확인</option>
            <option value="자동">자동</option>
            <option value="알림">알림</option>
          </select>
        </div>

        {/* Claude AI */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 0', borderBottom: '1px solid #eee' }}>
          <span style={{ fontSize: 17, fontWeight: 700 }}>Claude AI 의견</span>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={settings.claude_ai_enabled}
              onChange={e => setSettings({ ...settings, claude_ai_enabled: e.target.checked })}
              style={{ width: 20, height: 20 }}
            />
            <span style={{ fontSize: 16, fontWeight: 700 }}>{settings.claude_ai_enabled ? '사용' : '미사용'}</span>
          </label>
        </div>

        {/* 알림 소리 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 0', borderBottom: '1px solid #eee' }}>
          <span style={{ fontSize: 17, fontWeight: 700 }}>알림 소리</span>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={settings.sound_enabled ?? true}
              onChange={e => setSettings({ ...settings, sound_enabled: e.target.checked })}
              style={{ width: 20, height: 20 }}
            />
            <span style={{ fontSize: 16, fontWeight: 700 }}>{(settings.sound_enabled ?? true) ? '사용' : '미사용'}</span>
          </label>
        </div>

        {/* 메시지 */}
        {msg && <div style={{ textAlign: 'center', padding: '10px 0', color: msg.includes('저장') ? '#4caf50' : '#f44336', fontWeight: 600 }}>{msg}</div>}

        {/* 저장 버튼 */}
        <button
          onClick={save}
          disabled={saving}
          style={{
            width: '100%', marginTop: 20, padding: '14px',
            background: '#1565c0', color: '#fff', border: 'none',
            borderRadius: 10, fontSize: 18, fontWeight: 700, cursor: 'pointer'
          }}
        >
          {saving ? '저장 중...' : '저장'}
        </button>
        </div>{/* 스크롤 영역 끝 */}
      </div>
    </div>
  )
}
