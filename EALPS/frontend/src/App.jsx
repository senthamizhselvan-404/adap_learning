import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { createContext, useContext, useState, useEffect } from 'react'
import api from './api/client'

import Login         from './pages/Login'
import Register      from './pages/Register'
import Dashboard     from './pages/Dashboard'
import Roadmap       from './pages/Roadmap'
import Skills        from './pages/Skills'
import Admin         from './pages/Admin'
import Curriculum    from './pages/Curriculum'
import IDE           from './pages/IDE'
import YouTube       from './pages/YouTube'
import OAuthCallback from './pages/OAuthCallback'
import Navbar        from './components/Navbar'

export const AuthContext = createContext(null)

export function useAuth() { return useContext(AuthContext) }

function ProtectedRoute({ children, adminOnly = false }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && !['admin', 'instructor'].includes(user.role))
    return <Navigate to="/dashboard" replace />
  return children
}

export default function App() {
  const [user, setUser]   = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      api.get('/auth/me').then(r => setUser(r.data)).catch(() => {
        localStorage.clear()
      }).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = (tokens, learnerData) => {
    localStorage.setItem('access_token',  tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
    setUser(learnerData)
  }

  const logout = () => {
    localStorage.clear()
    setUser(null)
  }

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-brand-500 text-xl animate-pulse">Loading EALPS…</div>
    </div>
  )

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <BrowserRouter>
        {user && <Navbar />}
        <div className={user ? 'pt-16' : ''}>
          <Routes>
            <Route path="/login"         element={user ? <Navigate to="/dashboard" /> : <Login />} />
            <Route path="/register"      element={user ? <Navigate to="/dashboard" /> : <Register />} />
            <Route path="/auth/callback" element={<OAuthCallback />} />
            <Route path="/dashboard"     element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/roadmap/:id?"  element={<ProtectedRoute><Roadmap /></ProtectedRoute>} />
            <Route path="/skills"        element={<ProtectedRoute><Skills /></ProtectedRoute>} />
            <Route path="/ide" element={<ProtectedRoute><IDE /></ProtectedRoute>} />
            <Route path="/youtube"       element={<ProtectedRoute><YouTube /></ProtectedRoute>} />
            <Route path="/curriculum"    element={<ProtectedRoute><Curriculum /></ProtectedRoute>} />
            <Route path="/admin"         element={<ProtectedRoute adminOnly><Admin /></ProtectedRoute>} />
            <Route path="*"              element={<Navigate to={user ? '/dashboard' : '/login'} />} />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}
