import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Settings from './Settings'
import AlertDetail from './AlertDetail'
import AlertList from './AlertList'
import { authFetch, removeToken, getToken, API_PREFIX } from '../utils/auth'
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

// 지수용 포맷 (소수 2자리)
function fmtIdx(n) {
  if (n === null || n === undefined) return '-'
  return Number(n).toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function StockCard({ stock, onAnalyze }) {
  const c = STATUS_COLOR[stock.status] || STATUS_COLOR['정상']
  const icon = STATUS_ICON[stock.status] || ''
  const profitColor = stock.profit_loss >= 0 ? '#d32f2f' : '#1565c0'
  const buyTotal = stock.buy_price * stock.quantity
  const evalTotal = stock.current_price * stock.quantity
  const dayChangeColor = (stock.day_change || 0) >= 0 ? '#d32f2f' : '#1565c0'
  const dayRate = stock.prev_close ? ((stock.current_price - stock.prev_close) / stock.prev_close * 100) : 0

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

      {/* 평가손익 / 전일대비 / 수량 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
        <div>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>평가손익</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: profitColor }}>
            {stock.profit_loss >= 0 ? '+' : ''}{fmt(stock.profit_loss)}원
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>전일대비</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: dayChangeColor }}>
            {(stock.day_change || 0) >= 0 ? '+' : ''}{fmt(stock.day_change || 0)}원
          </div>
          <div style={{ fontSize: 13, fontWeight: 600, color: dayChangeColor }}>
            ({dayRate >= 0 ? '+' : ''}{dayRate.toFixed(2)}%)
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 14, color: '#444', fontWeight: 600 }}>수량 / 매입가</div>
          <div style={{ fontSize: 15, fontWeight: 500, color: '#222' }}>{stock.quantity}주 / {fmt(stock.buy_price)}원</div>
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

  const [showMarket, setShowMarket] = useState(false)
  const [indices, setIndices] = useState([])

  const handleLogout = () => {
    removeToken()
    navigate('/login')
  }

  // 증시상황 표 토글 (열 때 지수 조회)
  const toggleMarket = async () => {
    const next = !showMarket
    setShowMarket(next)
    if (next) {
      try {
        const res = await authFetch('/api/market/indices')
        setIndices(await res.json())
      } catch {
        setIndices([])
      }
    }
  }

  // 초기화 — 확인창 없이 즉시 9종목 리셋 후 새로고침
  const handleDemoReset = async () => {
    const res = await authFetch('/api/demo/reset', { method: 'POST' })
    if (res.ok) fetchStocks()
  }

  // SSE 알림 수신
  useEffect(() => {
    const token = getToken()
    if (!token) return
    const es = new EventSource(`${API_PREFIX}/api/alerts/stream?token=${encodeURIComponent(token)}&after_id=0`)
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
  const totalDayChange = stocks.reduce((s, x) => s + (x.day_change || 0), 0)
  const totalProfit = totalEval - totalBuy
  const totalRate = totalBuy ? ((totalProfit / totalBuy) * 100).toFixed(2) : 0
  const prevTotalEval = totalEval - totalDayChange
  const totalDayRate = prevTotalEval ? ((totalDayChange / prevTotalEval) * 100).toFixed(2) : 0
  const sellCount = stocks.filter(s => s.status === '매도').length
  const warnCount = stocks.filter(s => s.status === '주의').length

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: '0 6px 40px' }} onClick={unlockAudio}>

      {/* 헤더 */}
      <div style={{ padding: '8px 0 6px', borderBottom: '2px solid #1565c0', marginBottom: 14 }}>
        <div style={{ fontSize: 20, fontWeight: 800, color: '#1565c0', marginBottom: 6 }}>📈 MyStock</div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button onClick={toggleMarket} style={{
            flex: 1, background: showMarket ? '#0d47a1' : '#1565c0', color: '#fff', border: 'none',
            borderRadius: 7, padding: '12px 4px', fontSize: 12, fontWeight: 700, cursor: 'pointer'
          }}>📊 증시상황</button>
          <button onClick={() => setShowSettings(true)} style={{
            flex: 1, background: '#555', color: '#fff', border: 'none',
            borderRadius: 7, padding: '12px 4px', fontSize: 12, fontWeight: 700, cursor: 'pointer'
          }}>⚙️ 설정</button>
          <button onClick={handleDemoReset} style={{
            flex: 1, background: '#e65100', color: '#fff', border: 'none',
            borderRadius: 7, padding: '12px 2px', fontSize: 12, fontWeight: 700, cursor: 'pointer'
          }}>🔁 초기화</button>
          <button onClick={handleLogout} style={{
            flex: 1, background: '#888', color: '#fff', border: 'none',
            borderRadius: 7, padding: '12px 4px', fontSize: 12, fontWeight: 700, cursor: 'pointer'
          }}>🚪 나가기</button>
        </div>
      </div>

      {/* 증시상황 표 */}
      {showMarket && (
        <div style={{ background: '#0f172a', borderRadius: 12, padding: '12px 14px', marginBottom: 14, color: '#e2e8f0' }}>
          <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>📊 증시상황</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ color: '#94a3b8' }}>
                <th style={{ textAlign: 'left', padding: '4px 0', fontWeight: 600 }}>지수</th>
                <th style={{ textAlign: 'right', padding: '4px 0', fontWeight: 600 }}>금일</th>
                <th style={{ textAlign: 'right', padding: '4px 0', fontWeight: 600 }}>전일</th>
                <th style={{ textAlign: 'right', padding: '4px 0', fontWeight: 600 }}>등락</th>
              </tr>
            </thead>
            <tbody>
              {indices.length === 0 ? (
                <tr><td colSpan={4} style={{ textAlign: 'center', padding: 10, color: '#94a3b8' }}>불러오는 중...</td></tr>
              ) : indices.map(ix => {
                const up = (ix.change || 0) >= 0
                const col = up ? '#f87171' : '#60a5fa'
                return (
                  <tr key={ix.name} style={{ borderTop: '1px solid rgba(148,163,184,0.2)' }}>
                    <td style={{ textAlign: 'left', padding: '6px 0', fontWeight: 700 }}>{ix.name}</td>
                    <td style={{ textAlign: 'right', padding: '6px 0' }}>{fmtIdx(ix.today)}</td>
                    <td style={{ textAlign: 'right', padding: '6px 0', color: '#94a3b8' }}>{fmtIdx(ix.prev)}</td>
                    <td style={{ textAlign: 'right', padding: '6px 0', color: col, fontWeight: 700 }}>
                      {up ? '▲' : '▼'} {fmtIdx(Math.abs(ix.change))} ({up ? '+' : '-'}{Math.abs(ix.ratio)}%)
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* 요약 카드 */}
      <div style={{
        background: '#1565c0', borderRadius: 12, padding: '14px 18px',
        color: '#fff', marginBottom: 14
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>총 평가손익</div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>
              {totalProfit >= 0 ? '+' : ''}{fmt(totalProfit)}원
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 12, opacity: 0.8 }}>전일대비</div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>
              {totalDayChange >= 0 ? '+' : ''}{fmt(totalDayChange)}원
            </div>
            <div style={{ fontSize: 13, fontWeight: 700, opacity: 0.9 }}>
              ({totalDayRate > 0 ? '+' : ''}{totalDayRate}%)
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 12, opacity: 0.8 }}>수익률</div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>
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
