import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Settings from './Settings'
import AlertDetail from './AlertDetail'
import AlertList from './AlertList'
import { authFetch, removeToken, getToken } from '../utils/auth'
import { playSellAlert, playWarnAlert, unlockAudio } from '../utils/sound'

const STATUS_COLOR = {
  '정상': { bg: '#fff', border: '#ddd', badge: '#4caf50', text: '#333' },
  '주의': { bg: '#fffde7', border: '#ffc107', badge: '#ff9800', text: '#333' },
  '매도': { bg: '#ffebee', border: '#f44336', badge: '#f44336', text: '#b71c1c' },
}

const STATUS_ICON = { '정상': '✅', '주의': '⚠️', '매도': '🔴' }

function fmt(n) {
  if (!n && n !== 0) return '-'
  return Number(n).toLocaleString()
}

function StockCard({ stock, onAnalyze }) {
  const c = STATUS_COLOR[stock.status] || STATUS_COLOR['정상']
  const icon = STATUS_ICON[stock.status] || ''
  const profitColor = stock.profit_loss >= 0 ? '#d32f2f' : '#1565c0'
  const buyTotal = stock.buy_price * stock.quantity
  const evalTotal = stock.current_price * stock.quantity

  return (
    <div style={{
      background: c.bg,
      border: `2px solid ${c.border}`,
      borderRadius: 12,
      padding: '16px 18px',
      marginBottom: 12,
    }}>
      {/* 1번줄: 아이콘 + 2번줄: 라벨 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div style={{ display: 'flex', gap: 10 }}>
          {/* 상태 아이콘 */}
          <div style={{
            background: c.badge, borderRadius: 8, padding: '6px 12px',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
          }}>
            <span style={{ fontSize: 20, lineHeight: 1 }}>{icon}</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>{stock.status}</span>
          </div>
          {/* 매도판단 아이콘 */}
          <button
            onClick={() => onAnalyze(stock)}
            style={{
              background: '#1565c0', color: '#fff', border: 'none',
              borderRadius: 8, padding: '6px 12px', cursor: 'pointer',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
            }}
          >
            <span style={{ fontSize: 20, lineHeight: 1 }}>🧠</span>
            <span style={{ fontSize: 12, fontWeight: 700 }}>매도판단</span>
          </button>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 19, fontWeight: 700 }}>{stock.name}</div>
          <div style={{ fontSize: 15, color: '#555' }}>{stock.code}</div>
        </div>
      </div>

      {/* 현재가 / 수익률 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <div>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>현재가</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{fmt(stock.current_price)}원</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>수익률</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: profitColor }}>
            {stock.profit_rate > 0 ? '+' : ''}{stock.profit_rate}%
          </div>
        </div>
      </div>

      {/* 손절가 / 고점가 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #eee', paddingTop: 6 }}>
        <div>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>손절가 ({stock.trailing_rate}%)</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#e53935' }}>{fmt(stock.stop_price)}원</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>고점가</div>
          <div style={{ fontSize: 18, fontWeight: 600 }}>{fmt(stock.high_price)}원</div>
        </div>
      </div>

      {/* 손익금액 / 수량 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
        <div>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>평가손익</div>
          <div style={{ fontSize: 17, fontWeight: 600, color: profitColor }}>
            {stock.profit_loss >= 0 ? '+' : ''}{fmt(stock.profit_loss)}원
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>수량 / 매입가</div>
          <div style={{ fontSize: 17, fontWeight: 500, color: '#222' }}>{stock.quantity}주 / {fmt(stock.buy_price)}원</div>
        </div>
      </div>

      {/* 매입액계 / 평가액계 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
        <div>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>매입액계</div>
          <div style={{ fontSize: 17, fontWeight: 500, color: '#222' }}>{fmt(buyTotal)}원</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>평가액계</div>
          <div style={{ fontSize: 17, fontWeight: 500, color: profitColor }}>{fmt(evalTotal)}원</div>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stocks, setStocks] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [showSettings, setShowSettings] = useState(false)

  const [audioUnlocked, setAudioUnlocked] = useState(false)
  const audioUnlockedRef = useRef(false)
  const [pendingAlerts, setPendingAlerts] = useState([])
  const [selectedAlert, setSelectedAlert] = useState(null)

  const handleLogout = () => {
    removeToken()
    navigate('/login')
  }

  const handleDemoReset = async () => {
    if (!window.confirm('데모 데이터를 초기화하시겠습니까?\n(매도 이력 포함 전체 삭제 후 6개 종목 재생성)')) return
    const res = await authFetch('/api/demo/reset', { method: 'POST' })
    if (res.ok) {
      alert('초기화 완료! 새 데모 데이터가 생성되었습니다.')
      fetchStocks()
    } else {
      alert('초기화 실패')
    }
  }

  // SSE 알림 수신
  useEffect(() => {
    const token = getToken()
    if (!token) return
    const es = new EventSource(`/api/alerts/stream?token=${encodeURIComponent(token)}&after_id=0`)
    es.onmessage = (e) => {
      try {
        const alert = JSON.parse(e.data)
        if (alert.status === '매도') {
          if (audioUnlockedRef.current) playSellAlert()
          if (alert.sell_mode === '확인') {
            setPendingAlerts(prev => {
              if (prev.find(a => a.stock_id === alert.stock_id)) return prev
              return [...prev, alert]
            })
          }
        } else if (alert.status === '주의') {
          if (audioUnlockedRef.current) playWarnAlert()
        }
      } catch {}
    }
    return () => es.close()
  }, [])

  // 팝업 처리 완료 (매도/보류)
  const handleAlertDone = (stockId) => {
    setPendingAlerts(prev => prev.filter(a => a.stock_id !== stockId))
    setSelectedAlert(null)
    fetchStocks()
  }

  // 수동 매도판단 버튼 클릭
  const handleManualAnalyze = (stock) => {
    const alert = {
      stock_id: stock.id,
      account_id: stock.account_id,
      code: stock.code,
      name: stock.name,
      stock_type: stock.stock_type,
      current_price: stock.current_price,
      stop_price: stock.stop_price,
      high_price: stock.high_price,
      buy_price: stock.buy_price,
      quantity: stock.quantity,
      profit_rate: stock.profit_rate,
      trailing_rate: stock.trailing_rate,
      sell_mode: stock.sell_mode,
      status: stock.status,
    }
    setSelectedAlert(alert)
  }

  const fetchStocks = async () => {
    try {
      const res = await authFetch('/api/stocks/')
      const data = await res.json()
      // 상태 순서: 매도 → 주의 → 정상
      const order = { '매도': 0, '주의': 1, '정상': 2 }
      data.sort((a, b) => (order[a.status] ?? 3) - (order[b.status] ?? 3))
      setStocks(data)
      setLastUpdate(new Date().toLocaleTimeString('ko-KR'))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStocks()
  }, [])

  // 요약 계산
  const totalBuy = stocks.reduce((s, x) => s + (x.buy_amount || 0), 0)
  const totalEval = stocks.reduce((s, x) => s + (x.eval_amount || 0), 0)
  const totalProfit = totalEval - totalBuy
  const totalRate = totalBuy ? ((totalProfit / totalBuy) * 100).toFixed(2) : 0
  const sellCount = stocks.filter(s => s.status === '매도').length
  const warnCount = stocks.filter(s => s.status === '주의').length

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: '0 6px 40px' }} onClick={unlockAudio}>

      {/* 헤더 */}
      <div style={{ padding: '8px 0 6px', borderBottom: '2px solid #1565c0', marginBottom: 14 }}>
        <div style={{ fontSize: 20, fontWeight: 800, color: '#1565c0', marginBottom: 6 }}>📈 MyStock</div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button onClick={() => { if (!audioUnlocked) unlockAudio(); const next = !audioUnlocked; setAudioUnlocked(next); audioUnlockedRef.current = next }} style={{
            flex: 1, background: audioUnlocked ? '#4caf50' : '#888', color: '#fff', border: 'none',
            borderRadius: 7, padding: '5px 4px', fontSize: 12, fontWeight: 700, cursor: 'pointer'
          }}>{audioUnlocked ? '🔔알림ON' : '🔕알림OFF'}</button>
          <button onClick={() => setShowSettings(true)} style={{
            flex: 1, background: '#555', color: '#fff', border: 'none',
            borderRadius: 7, padding: '5px 4px', fontSize: 12, fontWeight: 700, cursor: 'pointer'
          }}>⚙️ 설정</button>
          <button onClick={handleDemoReset} style={{
            flex: 1, background: '#e65100', color: '#fff', border: 'none',
            borderRadius: 7, padding: '5px 2px', fontSize: 12, fontWeight: 700, cursor: 'pointer'
          }}>🔁 초기화</button>
          <button onClick={handleLogout} style={{
            flex: 1, background: '#888', color: '#fff', border: 'none',
            borderRadius: 7, padding: '5px 4px', fontSize: 12, fontWeight: 700, cursor: 'pointer'
          }}>🚪 나가기</button>
        </div>
      </div>

      {/* 요약 카드 */}
      <div style={{
        background: '#1565c0', borderRadius: 12, padding: '14px 18px',
        color: '#fff', marginBottom: 14
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>총 평가손익</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>
              {totalProfit >= 0 ? '+' : ''}{fmt(totalProfit)}원
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 12, opacity: 0.8 }}>수익률</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>
              {totalRate > 0 ? '+' : ''}{totalRate}%
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12, fontSize: 16, opacity: 1, fontWeight: 600 }}>
          <span>매입 {fmt(totalBuy)}원</span>
          <span>평가 {fmt(totalEval)}원</span>
        </div>
        {(sellCount > 0 || warnCount > 0) && (
          <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
            {sellCount > 0 && <span style={{ background: '#f44336', borderRadius: 6, padding: '2px 10px', fontSize: 13 }}>🔴 매도 {sellCount}종목</span>}
            {warnCount > 0 && <span style={{ background: '#ff9800', borderRadius: 6, padding: '2px 10px', fontSize: 13 }}>⚠️ 주의 {warnCount}종목</span>}
          </div>
        )}
      </div>

      {/* 종목 수 / 갱신시간 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#888', marginBottom: 10 }}>
        <span>총 {stocks.length}종목</span>
        {lastUpdate && <span>갱신: {lastUpdate}</span>}
      </div>

      {/* 설정 모달 */}
      {showSettings && <Settings onClose={() => { setShowSettings(false); fetchStocks() }} />}

      {/* 알림 팝업 */}
      {pendingAlerts.length === 1 && !selectedAlert && (
        <AlertDetail alert={pendingAlerts[0]} onDone={handleAlertDone} />
      )}
      {pendingAlerts.length > 1 && !selectedAlert && (
        <AlertList
          alerts={pendingAlerts}
          onSelect={setSelectedAlert}
          onDismissAll={() => { setPendingAlerts([]); setSelectedAlert(null) }}
        />
      )}
      {selectedAlert && (
        <AlertDetail alert={selectedAlert} onDone={handleAlertDone} />
      )}

      {/* 종목 카드 목록 */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#888' }}>불러오는 중...</div>
      ) : stocks.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#888' }}>종목이 없습니다</div>
      ) : (
        stocks.map(s => <StockCard key={s.id} stock={s} onAnalyze={handleManualAnalyze} />)
      )}
    </div>
  )
}
