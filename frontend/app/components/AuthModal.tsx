'use client'

import { useRef, useState, useCallback, useEffect } from 'react'
import { useAuth } from '@/app/contexts/AuthContext'

type AuthMode = 'login' | 'signup'

interface AuthModalProps {
  open: boolean
  onClose: () => void
  initialMode?: AuthMode
}

export default function AuthModal({ open, onClose, initialMode = 'login' }: AuthModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const { signIn, signUp } = useAuth()
  const [mode, setMode] = useState<AuthMode>(initialMode)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    if (open && !dialog.open) {
      dialog.showModal()
    } else if (!open && dialog.open) {
      dialog.close()
    }
  }, [open])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    const handleClose = () => onClose()
    dialog.addEventListener('close', handleClose)
    return () => dialog.removeEventListener('close', handleClose)
  }, [onClose])

  const resetForm = useCallback(() => {
    setEmail('')
    setPassword('')
    setDisplayName('')
    setError(null)
    setSuccess(null)
  }, [])

  const toggleMode = useCallback(() => {
    setMode(m => m === 'login' ? 'signup' : 'login')
    resetForm()
  }, [resetForm])

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      if (mode === 'signup') {
        const { error } = await signUp(email, password, displayName)
        if (error) {
          setError(error)
        } else {
          setSuccess('Conta criada! Verifique seu email para confirmar.')
        }
      } else {
        const { error } = await signIn(email, password)
        if (error) {
          setError(error)
        } else {
          onClose()
        }
      }
    } finally {
      setLoading(false)
    }
  }, [mode, email, password, displayName, signIn, signUp, onClose])

  return (
    <dialog
      ref={dialogRef}
      className="rounded-xl p-0 backdrop:bg-black/50 w-full max-w-md bg-[var(--surface-elevated)] text-[var(--ink)]"
    >
      <form onSubmit={handleSubmit} className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">
            {mode === 'login' ? 'Entrar' : 'Criar Conta'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--ink-secondary)] hover:text-[var(--ink)] text-xl leading-none"
            aria-label="Fechar"
          >
            &times;
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-status-error-bg text-status-error-text border border-status-error text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 rounded-lg bg-status-success-bg text-status-success-text border border-status-success text-sm">
            {success}
          </div>
        )}

        {mode === 'signup' && (
          <div className="mb-4">
            <label htmlFor="auth-display-name" className="block text-sm font-medium mb-1 text-[var(--ink-secondary)]">
              Nome
            </label>
            <input
              id="auth-display-name"
              type="text"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--surface-1)] text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-blue)]"
              placeholder="Seu nome"
              autoComplete="name"
            />
          </div>
        )}

        <div className="mb-4">
          <label htmlFor="auth-email" className="block text-sm font-medium mb-1 text-[var(--ink-secondary)]">
            Email
          </label>
          <input
            id="auth-email"
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--surface-1)] text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-blue)]"
            placeholder="seu@email.com"
            autoComplete="email"
          />
        </div>

        <div className="mb-6">
          <label htmlFor="auth-password" className="block text-sm font-medium mb-1 text-[var(--ink-secondary)]">
            Senha
          </label>
          <input
            id="auth-password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            minLength={6}
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--surface-1)] text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-blue)]"
            placeholder="Min. 6 caracteres"
            autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 rounded-lg font-medium bg-[var(--brand-blue)] text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {loading
            ? 'Aguarde...'
            : mode === 'login'
              ? 'Entrar'
              : 'Criar Conta'}
        </button>

        <p className="mt-4 text-center text-sm text-[var(--ink-secondary)]">
          {mode === 'login' ? (
            <>
              Ainda nao tem conta?{' '}
              <button type="button" onClick={toggleMode} className="text-[var(--brand-blue)] hover:underline">
                Criar conta
              </button>
            </>
          ) : (
            <>
              Ja tem conta?{' '}
              <button type="button" onClick={toggleMode} className="text-[var(--brand-blue)] hover:underline">
                Entrar
              </button>
            </>
          )}
        </p>
      </form>
    </dialog>
  )
}
