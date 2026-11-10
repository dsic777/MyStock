import { useState } from 'react'
import { authFetch } from '../utils/auth'

// 수량조정 — 종목 목록에서 누르면 수량 수정, 0 이면 서버가 종목을 지운다
export default function Quantity({ stocks, onChanged, onClose }) {
  const [editId, setEditId] = useState(null)
  const [qty, setQty] = useState('')
  const [msg, setMsg] = useState('')

  const open = (s) => {
    setEditId(s.id)
    setQty(String(s.quantity))
    setMsg('')
  }

  const save = async (s) => {
    const n = parseInt(qty, 10)
    if (isNaN(n) || n < 0) { setMsg('0 이상 숫자를 넣어 주세요'); return }
    const res = await authFetch(`/api/stocks/${s.id}`, {
      method: 'PUT',
      body: JSON.stringify({ quantity: n }),
    })
    if (res.ok) {
      setMsg(n === 0 ? `${s.name} 지웠습니다` : `${s.name} ${n}주로 바꿨습니다`)
      setEditId(null)
      onChanged()
    } else setMsg('저장 실패')
  }

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
          <span style={{ fontSize: 20, fontWeight: 700 }}>🔢 수량조정</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: '#888' }}>✕</button>
        </div>
        {/* 스크롤 영역 */}
        <div style={{ overflowY: 'auto', padding: '0 20px 40px', flex: 1 }}>
          {msg && <div style={{ padding: '12px 0', color: '#1565c0', fontWeight: 700 }}>{msg}</div>}
          {stocks.map(s => (
            <div key={s.id} style={{ padding: '14px 0', borderBottom: '1px solid #eee' }}>
              <div onClick={() => open(s)} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}>
                <span style={{ fontSize: 17, fontWeight: 700 }}>{s.name}</span>
                <span style={{ fontSize: 17, fontWeight: 700, color: '#555' }}>{s.quantity}주</span>
              </div>
              {editId === s.id && (
                <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                  <input
                    type="number" inputMode="numeric" min="0" autoFocus
                    value={qty}
                    onChange={e => setQty(e.target.value)}
                    style={{ flex: 1, fontSize: 18, fontWeight: 700, padding: '8px 10px', border: '1px solid #ccc', borderRadius: 8 }}
                  />
                  <button onClick={() => save(s)} style={{
                    background: '#1565c0', color: '#fff', border: 'none',
                    borderRadius: 8, padding: '8px 16px', fontSize: 16, fontWeight: 700, cursor: 'pointer'
                  }}>저장</button>
                  <button onClick={() => setEditId(null)} style={{
                    background: '#888', color: '#fff', border: 'none',
                    borderRadius: 8, padding: '8px 12px', fontSize: 16, fontWeight: 700, cursor: 'pointer'
                  }}>취소</button>
                </div>
              )}
            </div>
          ))}
          <div style={{ paddingTop: 12, fontSize: 13, color: '#888' }}>수량을 0 으로 저장하면 그 종목은 지워집니다.</div>
        </div>
      </div>
    </div>
  )
}
