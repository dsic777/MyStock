const TOKEN_KEY = 'mystock_token'
const API_PREFIX = import.meta.env.VITE_API_PREFIX || ''

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token)
export const removeToken = () => localStorage.removeItem(TOKEN_KEY)
export const isLoggedIn = () => !!getToken()

export const authHeaders = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${getToken()}`,
})

export const authFetch = async (url, options = {}) => {
  const res = await fetch(`${API_PREFIX}${url}`, {
    ...options,
    headers: {
      ...authHeaders(),
      ...(options.headers || {}),
    },
  })
  if (res.status === 401) {
    removeToken()
    window.location.href = `${API_PREFIX}/login`
  }
  return res
}
