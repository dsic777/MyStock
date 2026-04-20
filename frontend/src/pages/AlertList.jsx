function fmt(n) {
  if (!n && n !== 0) return '-'
  return Number(n).toLocaleString()
}

export default function AlertList({ alerts, onSelect, onDismissAll }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'flex-end', justifyContent: 'center', zIndex: 200,
    }}>
      <div style={{
        background: '#fff', borderRadius: '16px 16px 0 0',
        width: '100%', maxWidth: 600, padding: '24px 20px 40px',
      }}>
        {/* 헤더 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 24 }}>🔴</span>
            <span style={{ fontSize: 20, fontWeight: 700 }}>손절가 도달 {alerts.length}종목</span>
          </div>
          <button
            onClick={onDismissAll}
            style={{
              background: '#eee', color: '#555', border: 'none',
              borderRadius: 8, padding: '6px 14px', fontSize: 14, cursor: 'pointer',
            }}
          >전체 보류</button>
        </div>

        {/* 종목 목록 */}
        <div style={{ maxHeight: '50vh', overflowY: 'auto' }}>
          {alerts.map(alert => {
            // 공시 알림
            if (alert.type === 'dart') {
              return (
                <div
                  key={alert.rcept_no}
                  style={{
                    border: '2px solid #bbdefb', borderRadius: 10, padding: '14px 16px',
                    marginBottom: 10, background: '#e3f2fd',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 700 }}>
                      📢 {alert.name} <span style={{ fontSize: 12, color: '#1565c0', fontWeight: 400 }}>{alert.code}</span>
                    </div>
                    <div style={{ fontSize: 13, color: '#333', marginTop: 4 }}>{alert.title}</div>
                    <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>{alert.date}</div>
                  </div>
                  <div style={{ fontSize: 12, color: '#1565c0', fontWeight: 700, whiteSpace: 'nowrap', marginLeft: 12 }}>
                    공시
                  </div>
                </div>
              )
            }
            // 트레일링 스탑 알림
            const profitColor = alert.profit_rate >= 0 ? '#d32f2f' : '#1565c0'
            return (
              <div
                key={alert.stock_id}
                onClick={() => onSelect(alert)}
                style={{
                  border: '2px solid #ffcdd2', borderRadius: 10, padding: '14px 16px',
                  marginBottom: 10, cursor: 'pointer', background: '#ffebee',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: 17, fontWeight: 700 }}>{alert.name}</div>
                  <div style={{ fontSize: 13, color: '#888', marginTop: 2 }}>
                    {alert.code} · 현재 {fmt(alert.current_price)}원 → 손절 {fmt(alert.stop_price)}원
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: profitColor }}>
                    {alert.profit_rate >= 0 ? '+' : ''}{alert.profit_rate}%
                  </div>
                  <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>▶ 상세보기</div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
