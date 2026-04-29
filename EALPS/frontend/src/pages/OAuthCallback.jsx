import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../App'
import api from '../api/client'

const ERROR_MESSAGES = {
  oauth_cancelled:       'Sign-in was cancelled. Please try again.',
  token_exchange_failed: 'Could not complete sign-in. Please try again.',
  userinfo_failed:       'Could not retrieve your profile. Please try again.',
  db_error:              'Account error. Please try again.',
  no_token:              'Sign-in failed. No token received.',
  auth_failed:           'Authentication failed. Please sign in again.',
}

export default function OAuthCallback() {
  const { login }          = useAuth()
  const navigate           = useNavigate()
  const [searchParams]     = useSearchParams()
  const [errorMsg, setErr] = useState('')

  useEffect(() => {
    const errorCode   = searchParams.get('error')
    const accessToken = searchParams.get('access_token')
    const refreshToken = searchParams.get('refresh_token') || ''

    if (errorCode) {
      setErr(ERROR_MESSAGES[errorCode] || 'Sign-in failed. Please try again.')
      setTimeout(() => navigate('/login'), 3000)
      return
    }

    if (!accessToken) {
      setErr(ERROR_MESSAGES.no_token)
      setTimeout(() => navigate('/login'), 3000)
      return
    }

    localStorage.setItem('access_token', accessToken)
    if (refreshToken) localStorage.setItem('refresh_token', refreshToken)

    api.get('/auth/me')
      .then(r => {
        login({ access_token: accessToken, refresh_token: refreshToken }, r.data)
        navigate('/dashboard')
      })
      .catch(() => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setErr(ERROR_MESSAGES.auth_failed)
        setTimeout(() => navigate('/login'), 3000)
      })
  }, [])

  if (errorMsg) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-6">
        <div className="text-red-400 text-lg font-medium">{errorMsg}</div>
        <p className="text-slate-500 text-sm">Redirecting to sign in…</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-3">
      <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      <p className="text-slate-400 text-sm">Completing sign in…</p>
    </div>
  )
}
