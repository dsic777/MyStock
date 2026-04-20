import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { setToken } from '../utils/auth'

const API_PREFIX = import.meta.env.VITE_API_PREFIX || ''

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('test')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API_PREFIX}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (res.ok) {
        const data = await res.json()
        setToken(data.access_token)
        navigate('/')
      } else {
        const data = await res.json()
        setError(data.detail || '로그인 실패')
      }
    } catch {
      setError('서버에 연결할 수 없습니다')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '16px 18px', fontSize: 18, fontWeight: 700,
    border: 'none', borderRadius: 12, boxSizing: 'border-box', outline: 'none',
    background: '#e8f4fd', color: '#111',
  }

  return (
    <div style={{
      minHeight: '100vh', width: '100vw',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(160deg, #0a0a0a 0%, #0d1b2a 50%, #111 100%)',
    }}>
      <div style={{ width: '100%', maxWidth: 400, padding: '0 24px' }}>

        {/* 로고 */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ fontSize: 56, marginBottom: 10 }}>📈</div>
          <div style={{ fontSize: 32, fontWeight: 900, color: '#fff', letterSpacing: 2 }}>MyStock</div>
          <div style={{ fontSize: 15, color: '#88aacc', marginTop: 6, fontWeight: 600 }}>
            트레일링 스탑 매도 알리미
          </div>
        </div>

        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: 16 }}>
            <input
              type="text"
              placeholder="아이디"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoFocus
              autoCapitalize="none"
              autoCorrect="off"
              style={inputStyle}
            />
          </div>
          <div style={{ marginBottom: 28 }}>
            <input
              type="password"
              placeholder="비밀번호"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoCapitalize="none"
              autoCorrect="off"
              style={inputStyle}
            />
          </div>

          {error && (
            <div style={{
              color: '#ff8a80', fontSize: 15, textAlign: 'center',
              marginBottom: 16, fontWeight: 700,
            }}>{error}</div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '16px', fontSize: 19, fontWeight: 900,
              background: loading ? '#444' : 'linear-gradient(135deg, #1565c0, #1976d2)',
              color: '#fff', border: 'none', borderRadius: 12,
              cursor: loading ? 'default' : 'pointer',
              boxShadow: loading ? 'none' : '0 4px 20px rgba(21,101,192,0.5)',
            }}
          >
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </form>
      </div>
    </div>
  )
}
