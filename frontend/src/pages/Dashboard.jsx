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

// 항목 탭 시 펼쳐지는 선그래프 (좌탭:분봉 / 우탭:일봉 / 가운데:닫기 / 좌우드래그:구분변경)
const MIN_UNITS = ['1', '3', '5', '10', '20', '30']
const DAY_UNITS = ['day', 'week', 'month', 'year']
const DAY_LABEL = { day: '일', week: '주', month: '월', year: '년' }

function MiniChart({ code, onClose }) {
  const [mode, setMode] = useState('minute')   // 'minute' | 'day'
  const [unit, setUnit] = useState('1')
  const [points, setPoints] = useState([])
  const [loading, setLoading] = useState(true)
  const boxRef = useRef(null)
  const drag = useRef(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    authFetch(`/api/chart/${code}?type=${mode}&unit=${unit}`)
      .then(r => r.json())
      .then(d => { if (alive) { setPoints(d.points || []); setLoading(false) } })
      .catch(() => { if (alive) { setPoints([]); setLoading(false) } })
    return () => { alive = false }
  }, [code, mode, unit])

  // dir: +1 = 올라가기(다음 큰 단위), -1 = 내려가기
  const cycle = (dir) => {
    const list = mode === 'minute' ? MIN_UNITS : DAY_UNITS
    let i = list.indexOf(unit) + dir
    if (i < 0) i = 0
    if (i >= list.length) i = list.length - 1
    setUnit(list[i])
  }

  const onDown = (e) => { drag.current = { x0: e.clientX, moved: false } }
  const onMove = (e) => {
    if (drag.current && Math.abs(e.clientX - drag.current.x0) > 30) drag.current.moved = true
  }
  const onUp = (e) => {
    const d = drag.current; drag.current = null
    if (!d) return
    const dx = e.clientX - d.x0
    if (d.moved && Math.abs(dx) > 30) {
      cycle(dx < 0 ? +1 : -1)          // 좌드래그=올라가기 / 우드래그=내려가기
    } else {
      const rect = boxRef.current.getBoundingClientRect()
      const rel = (e.clientX - rect.left) / rect.width
      if (rel < 0.34) { setMode('minute'); setUnit('1') }
      else if (rel > 0.66) { setMode('day'); setUnit('day') }
      else onClose()
    }
  }

  // SVG 선그래프 path
  const W = 600, H = 190, pad = 6
  let path = ''
  if (points.length > 1) {
    const cs = points.map(p => p.c)
    const min = Math.min(...cs), max = Math.max(...cs), range = (max - min) || 1
    const n = points.length
    path = cs.map((cv, i) => {
      const x = pad + (i / (n - 1)) * (W - 2 * pad)
      const y = pad + (1 - (cv - min) / range) * (H - 2 * pad)
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    }).join(' ')
  }
  const label = mode === 'minute' ? `분봉 ${unit}분` : `일봉 ${DAY_LABEL[unit]}`
  const last = points.length ? points[points.length - 1].c : 0
  const first = points.length ? points[0].c : 0
  const lineColor = last >= first ? '#d32f2f' : '#1565c0'

  return (
    <div
      ref={boxRef}
      onClick={(e) => e.stopPropagation()}
      onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp}
      style={{ marginTop: 10, background: '#0b1728', borderRadius: 10, padding: 8, userSelect: 'none', touchAction: 'pan-y' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, color: '#9fb3c8', marginBottom: 4 }}>
        <span style={{ fontWeight: 700, color: '#e2e8f0' }}>{label}</span>
        <span style={{ fontSize: 10.5, color: '#6b7f95' }}>좌탭 분봉 · 우탭 일봉 · 가운데 닫기 · 드래그 구분</span>
      </div>
      {loading ? (
        <div style={{ height: H, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6b7f95', fontSize: 13 }}>불러오는 중...</div>
      ) : points.length < 2 ? (
        <div style={{ height: H, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6b7f95', fontSize: 13 }}>데이터 없음</div>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none" style={{ display: 'block' }}>
          <path d={path} fill="none" stroke={lineColor} strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
        </svg>
      )}
      <div style={{ textAlign: 'right', fontSize: 13, color: lineColor, fontWeight: 700, marginTop: 2 }}>{fmt(last)}원</div>
    </div>
  )
}

function StockCard({ stock, onAnalyze }) {
  const c = STATUS_COLOR[stock.status] || STATUS_COLOR['정상']
  const icon = STATUS_ICON[stock.status] || ''
  const profitColor = stock.profit_loss >= 0 ? '#d32f2f' : '#1565c0'
  const buyTotal = stock.buy_price * stock.quantity
  const evalTotal = stock.current_price * stock.quantity
  const dayChangeColor = (stock.day_change || 0) >= 0 ? '#d32f2f' : '#1565c0'
  const dayRate = stock.prev_close ? ((stock.current_price - stock.prev_close) / stock.prev_close * 100) : 0
  const [chartOpen, setChartOpen] = useState(false)

  return (
    <div
      onClick={() => setChartOpen(true)}
      style={{
      background: c.bg,
      border: `2px solid ${c.border}`,
      borderRadius: 12,
      padding: '16px 18px',
      marginBottom: 12,
      cursor: 'pointer',
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
            onClick={(e) => { e.stopPropagation(); onAnalyze(stock) }}
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
            <span style={{ fontSize: 13, fontWeight: 600, color: dayChangeColor, marginLeft: 4 }}>({dayRate >= 0 ? '+' : ''}{dayRate.toFixed(2)}%)</span>
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

      {chartOpen && <MiniChart code={stock.code} onClose={() => setChartOpen(false)} />}
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

  // 요약 계산 — 총 / 일반주 / ETF 각각 손익·전일대비·수익률·매입·평가
  const calcStats = (list) => {
    const buy = list.reduce((s, x) => s + (x.buy_amount || 0), 0)
    const evl = list.reduce((s, x) => s + (x.eval_amount || 0), 0)
    const dayChange = list.reduce((s, x) => s + (x.day_change || 0), 0)
    const profit = evl - buy
    const rate = buy ? ((profit / buy) * 100).toFixed(2) : 0
    const prevEval = evl - dayChange
    const dayRate = prevEval ? ((dayChange / prevEval) * 100).toFixed(2) : 0
    return { buy, evl, dayChange, profit, rate, dayRate }
  }
  const summaryGroups = [
    { label: '총 평가손익', bg: '#0d47a1', ...calcStats(stocks) },
    { label: '일반주 평가손익', bg: '#1565c0', ...calcStats(stocks.filter(s => s.stock_type !== 'ETF')) },
    { label: 'ETF 평가손익', bg: '#00838f', ...calcStats(stocks.filter(s => s.stock_type === 'ETF')) },
  ]

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
        background: '#0f2740', borderRadius: 12, padding: 8,
        color: '#fff', marginBottom: 14
      }}>
        {summaryGroups.map((g, i) => (
          <div key={g.label} style={{
            background: g.bg, borderRadius: 10, padding: '10px 12px',
            marginBottom: i < summaryGroups.length - 1 ? 8 : 0
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <div>
                <div style={{ fontSize: 12, opacity: 0.8 }}>{g.label}</div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>
                  {g.profit >= 0 ? '+' : ''}{fmt(g.profit)}원
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, opacity: 0.8 }}>전일대비</div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>
                  {g.dayChange >= 0 ? '+' : ''}{fmt(g.dayChange)}원
                  <span style={{ fontSize: 13, fontWeight: 700, opacity: 0.9, marginLeft: 4 }}>({g.dayRate > 0 ? '+' : ''}{g.dayRate}%)</span>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 12, opacity: 0.8 }}>수익률</div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>
                  {g.rate > 0 ? '+' : ''}{g.rate}%
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12, fontSize: 16, fontWeight: 600 }}>
              <span>매입 {fmt(g.buy)}원</span>
              <span>평가 {fmt(g.evl)}원</span>
            </div>
          </div>
        ))}
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
