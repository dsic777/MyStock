import { useState, useEffect } from 'react'
import { authFetch } from '../utils/auth'
import { playSoldSound } from '../utils/sound'

function fmt(n) {
  if (!n && n !== 0) return '-'
  return Number(n).toLocaleString()
}

export default function AlertDetail({ alert, onDone }) {
  const [opinion, setOpinion] = useState('')
  const [opinionStatus, setOpinionStatus] = useState('')
  const [opinionLoading, setOpinionLoading] = useState(false)
  const [disclosureSummary, setDisclosureSummary] = useState('')
  const [selling, setSelling] = useState(false)
  const [soldResult, setSoldResult] = useState(null)
  const [confirmMode, setConfirmMode] = useState(false)

  const profitColor = alert.profit_rate >= 0 ? '#d32f2f' : '#1565c0'
  const statusIcon = alert.status === '매도' ? '🔴' : alert.status === '주의' ? '⚠️' : '📊'

  useEffect(() => {
    setOpinion('')
    setOpinionStatus('')
    setConfirmMode(false)
    setSoldResult(null)
    setOpinionLoading(true)
    authFetch('/api/ai/opinion', {
      method: 'POST',
      body: JSON.stringify({
        name: alert.name,
        code: alert.code,
        stock_type: alert.stock_type,
        current_price: alert.current_price,
        stop_price: alert.stop_price,
        high_price: alert.high_price,
        buy_price: alert.buy_price,
        profit_rate: alert.profit_rate,
        trailing_rate: alert.trailing_rate,
      }),
    })
      .then(r => r.json())
      .then(d => { setOpinion(d.opinion || ''); setOpinionStatus(d.status || ''); setDisclosureSummary(d.disclosure_summary || '') })
      .catch(() => { setOpinion(''); setOpinionStatus('error') })
      .finally(() => setOpinionLoading(false))
  }, [alert.stock_id])

  const handleSellConfirm = async () => {
    setSelling(true)
    setConfirmMode(false)
    try {
      const res = await authFetch(
        `/api/stocks/${alert.stock_id}/sell?ai_opinion=${encodeURIComponent(opinion)}`,
        { method: 'POST' }
      )
      const data = await res.json()
      setSoldResult(data)
      playSoldSound()
      setTimeout(() => onDone(alert.stock_id), 2000)
    } catch {
      setSelling(false)
    }
  }

  const handleHold = () => onDone(alert.stock_id)

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'flex-end', justifyContent: 'center', zIndex: 200,
    }}>
      <div style={{
        background: '#fff', borderRadius: '16px 16px 0 0',
        width: '100%', maxWidth: 600,
        maxHeight: '90vh', display: 'flex', flexDirection: 'column',
      }}>
      <div style={{ overflowY: 'auto', padding: '28px 22px 44px', flex: 1 }}>

        {/* 헤더 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 22 }}>
          <span style={{ fontSize: 32 }}>{statusIcon}</span>
          <div>
            <div style={{ fontSize: 24, fontWeight: 900 }}>{alert.name}</div>
            <div style={{ fontSize: 15, color: '#888', fontWeight: 700 }}>{alert.code} · {alert.stock_type} · {alert.status}</div>
          </div>
        </div>

        {/* 가격 정보 */}
        <div style={{
          background: '#ffebee', borderRadius: 12, padding: '16px 18px', marginBottom: 18,
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14,
        }}>
          <div>
            <div style={{ fontSize: 14, color: '#888', fontWeight: 700 }}>현재가</div>
            <div style={{ fontSize: 24, fontWeight: 900 }}>{fmt(alert.current_price)}원</div>
          </div>
          <div>
            <div style={{ fontSize: 14, color: '#888', fontWeight: 700 }}>손절가</div>
            <div style={{ fontSize: 24, fontWeight: 900, color: '#e53935' }}>{fmt(alert.stop_price)}원</div>
          </div>
          <div>
            <div style={{ fontSize: 14, color: '#888', fontWeight: 700 }}>수익률</div>
            <div style={{ fontSize: 20, fontWeight: 900, color: profitColor }}>
              {alert.profit_rate >= 0 ? '+' : ''}{alert.profit_rate}%
            </div>
          </div>
          <div>
            <div style={{ fontSize: 14, color: '#888', fontWeight: 700 }}>고점가 ({alert.trailing_rate}%)</div>
            <div style={{ fontSize: 20, fontWeight: 900 }}>{fmt(alert.high_price)}원</div>
          </div>
        </div>

        {/* Claude AI 의견 */}
        <div style={{
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
          borderRadius: 14, padding: '18px 20px', marginBottom: 22,
          minHeight: 80, boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
        }}>
          {/* Claude 헤더 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{
              background: 'linear-gradient(135deg, #e07a5f, #f4a261)',
              borderRadius: 8, width: 34, height: 34,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 18, fontWeight: 900, color: '#fff', flexShrink: 0,
            }}>C</div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 900, color: '#fff', letterSpacing: 0.5 }}>Claude AI 매도 의견</div>
              <div style={{ fontSize: 11, color: '#88aacc', fontWeight: 700 }}>Powered by Anthropic</div>
            </div>
          </div>

          {/* 의견 내용 */}
          {opinionLoading ? (
            <div style={{ color: '#88aacc', fontSize: 16, fontWeight: 700 }}>🔍 분석 중...</div>
          ) : opinion ? (
            <div style={{
              fontSize: 16, lineHeight: 1.8, color: '#e8f4fd',
              fontWeight: 700, borderLeft: '3px solid #e07a5f', paddingLeft: 12,
            }}>{opinion}</div>
          ) : opinionStatus === 'disabled' ? (
            <div style={{ color: '#88aacc', fontSize: 15, fontWeight: 700 }}>설정에서 비활성화됨</div>
          ) : opinionStatus === 'no_api_key' ? (
            <div style={{ color: '#ffb74d', fontSize: 15, fontWeight: 700 }}>.env에 ANTHROPIC_API_KEY 미설정</div>
          ) : opinionStatus === 'error' ? (
            <div style={{ color: '#ff8a80', fontSize: 15, fontWeight: 700 }}>API 호출 오류 — FastAPI 로그 확인</div>
          ) : (
            <div style={{ color: '#88aacc', fontSize: 15, fontWeight: 700 }}>-</div>
          )}
        </div>

        {/* DART 핵심 공시 요약 */}
        {disclosureSummary && (
          <div style={{
            background: 'linear-gradient(135deg, #1b5e20 0%, #2e7d32 50%, #1a6b25 100%)',
            borderRadius: 14, padding: '18px 20px', marginBottom: 22,
            boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
          }}>
            <div style={{ fontSize: 13, fontWeight: 900, color: '#a5d6a7', marginBottom: 10, letterSpacing: 0.5 }}>📋 핵심 공시</div>
            <div style={{ fontSize: 16, color: '#e8f5e9', lineHeight: 1.8, fontWeight: 700, borderLeft: '3px solid #69f0ae', paddingLeft: 12 }}>
              {disclosureSummary.split(/(\d{1,2}\.\d{2})/).map((part, i) =>
                /^\d{1,2}\.\d{2}$/.test(part)
                  ? <span key={i} style={{ background: '#fdd835', color: '#1565c0', fontWeight: 700, borderRadius: 3, padding: '1px 4px' }}>{part}</span>
                  : part
              )}
            </div>
          </div>
        )}

        {/* 매도 완료 */}
        {soldResult && (
          <div style={{ textAlign: 'center', color: '#1565c0', fontWeight: 700, fontSize: 18, marginBottom: 14 }}>
            ✅ 매도 완료 · {fmt(soldResult.sell_price)}원 · {soldResult.profit_rate >= 0 ? '+' : ''}{soldResult.profit_rate}%
          </div>
        )}

        {/* 최종 확인 단계 */}
        {!soldResult && confirmMode && (
          <div style={{
            background: '#fff3e0', borderRadius: 12, padding: '16px 18px', marginBottom: 16,
            border: '2px solid #ff9800', textAlign: 'center',
          }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#e65100', marginBottom: 14 }}>
              ⚠️ 정말 매도하시겠습니까?
            </div>
            <div style={{ fontSize: 15, color: '#555', marginBottom: 18 }}>
              {alert.name} {alert.quantity}주 · 현재가 {fmt(alert.current_price)}원
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              <button
                onClick={() => setConfirmMode(false)}
                style={{
                  flex: 1, padding: '14px', fontSize: 17, fontWeight: 700,
                  background: '#eee', color: '#555', border: 'none',
                  borderRadius: 10, cursor: 'pointer',
                }}
              >취소</button>
              <button
                onClick={handleSellConfirm}
                disabled={selling}
                style={{
                  flex: 2, padding: '14px', fontSize: 17, fontWeight: 700,
                  background: '#f44336', color: '#fff', border: 'none',
                  borderRadius: 10, cursor: 'pointer',
                }}
              >확인 · 매도 실행</button>
            </div>
          </div>
        )}

        {/* 기본 버튼 */}
        {!soldResult && !confirmMode && (
          <div style={{ display: 'flex', gap: 12 }}>
            <button
              onClick={handleHold}
              style={{
                flex: 1, padding: '16px', fontSize: 18, fontWeight: 700,
                background: '#eee', color: '#555', border: 'none',
                borderRadius: 10, cursor: 'pointer',
              }}
            >보류</button>
            <button
              onClick={() => setConfirmMode(true)}
              style={{
                flex: 2, padding: '16px', fontSize: 18, fontWeight: 700,
                background: '#f44336', color: '#fff', border: 'none',
                borderRadius: 10, cursor: 'pointer',
              }}
            >매도 실행</button>
          </div>
        )}
      </div>{/* 스크롤 영역 끝 */}
      </div>
    </div>
  )
}
