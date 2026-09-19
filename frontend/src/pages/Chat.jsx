import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './Chat.css'
import { deleteConversation, getConversation, listConversations, logout, sendChat, uploadDocument } from '../api'
import { clearSession, getStoredEmail } from '../auth'

let nextLocalId = 1

const EXAMPLE_PROMPTS = [
  'How do I add a path parameter in FastAPI?',
  "What's the company's travel reimbursement policy?",
  'How many sets and reps should I do for strength?',
  "What's the avalanche method for paying off debt?",
]

function LogoMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4L12 2z"
        fill="currentColor"
      />
    </svg>
  )
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" fill="currentColor" />
    </svg>
  )
}

function UploadIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 15V4M7.5 8.5L12 4l4.5 4.5M5 16v2a2 2 0 002 2h10a2 2 0 002-2v-2"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path
        d="M4 7h16M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2m-8 0v13a1 1 0 001 1h6a1 1 0 001-1V7"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function EditIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <path
        d="M4 20h4L18.5 9.5a2.121 2.121 0 00-3-3L5 17v3z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <rect x="8" y="8" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M16 8V6a2 2 0 00-2-2H6a2 2 0 00-2 2v8a2 2 0 002 2h2"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <path
        d="M5 12.5l4.5 4.5L19 7"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function LogoutIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path
        d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <span />
      <span />
      <span />
    </div>
  )
}

function SystemNotice({ message }) {
  return (
    <div className={`system-notice${message.isError ? ' system-notice-error' : ''}`}>
      {message.content}
    </div>
  )
}

function Message({ message, onEdit }) {
  const isFormatted = message.role === 'assistant' && !message.isError
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    let ok = true
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable')
      await navigator.clipboard.writeText(message.content)
    } catch {
      try {
        const textarea = document.createElement('textarea')
        textarea.value = message.content
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      } catch {
        ok = false
      }
    }
    if (ok) {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }
  }

  return (
    <div className={`message message-${message.role}${message.isError ? ' message-error' : ''}`}>
      <div className="message-column">
        <div className="message-bubble">
          {isFormatted ? (
            <div className="markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          ) : (
            <p>{message.content}</p>
          )}
          {message.sources?.length > 0 && (
            <div className="sources">
              {message.sources.map((source) => (
                <span className="source-chip" key={source}>
                  {source}
                </span>
              ))}
            </div>
          )}
        </div>

        {isUser && (
          <div className="message-actions">
            <button className="message-action" onClick={() => onEdit(message.content)}>
              <EditIcon />
              Edit
            </button>
          </div>
        )}

        {isFormatted && (
          <div className="message-actions">
            <button className="message-action" onClick={handleCopy}>
              {copied ? <CheckIcon /> : <CopyIcon />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Chat() {
  const [conversations, setConversations] = useState([])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [initializing, setInitializing] = useState(true)
  const [switching, setSwitching] = useState(false)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)
  const navigate = useNavigate()
  const email = getStoredEmail()

  // On mount: load the conversation list and resume the most recently
  // active one, if any — this is the actual "cross-device continuity" bit,
  // since the list now comes from the server instead of localStorage.
  useEffect(() => {
    let cancelled = false
    async function init() {
      try {
        const list = await listConversations()
        if (cancelled) return
        setConversations(list)
        if (list.length > 0) {
          const detail = await getConversation(list[0].id)
          if (cancelled) return
          setActiveConversationId(detail.id)
          setMessages(detail.messages)
        }
      } catch {
        // listing failed (e.g. session expired) — RequireAuth will already
        // have bounced to /login on the next render if the token is gone
      } finally {
        if (!cancelled) setInitializing(false)
      }
    }
    init()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }, [input])

  function appendMessages(newOnes) {
    setMessages((prev) => [...prev, ...newOnes])
  }

  function updateMessageById(id, patch) {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)))
  }

  async function handleToggleHistory() {
    const opening = !historyOpen
    setHistoryOpen(opening)
    if (opening) {
      try {
        setConversations(await listConversations())
      } catch {
        // keep whatever list we already have rather than blanking it
      }
    }
  }

  function handleNewChat() {
    if (loading || switching) return
    if (activeConversationId === null && messages.length === 0) {
      setHistoryOpen(false)
      return // already on a fresh, empty draft — nothing to do
    }
    setActiveConversationId(null)
    setMessages([])
    setInput('')
    setHistoryOpen(false)
  }

  async function handleSelectSession(id) {
    if (loading || switching || id === activeConversationId) {
      setHistoryOpen(false)
      return
    }
    setHistoryOpen(false)
    setSwitching(true)
    try {
      const detail = await getConversation(id)
      setActiveConversationId(detail.id)
      setMessages(detail.messages)
      setInput('')
    } catch (err) {
      appendMessages([
        { id: nextLocalId++, role: 'system', content: err.message || 'Could not load that conversation.', isError: true },
      ])
    } finally {
      setSwitching(false)
    }
  }

  async function handleDeleteSession(e, id) {
    e.stopPropagation()
    if (loading) return
    try {
      await deleteConversation(id)
    } catch {
      // best-effort — still remove it locally so the UI doesn't feel stuck
    }
    setConversations((prev) => prev.filter((c) => c.id !== id))
    if (id === activeConversationId) {
      setActiveConversationId(null)
      setMessages([])
    }
  }

  async function handleLogout() {
    try {
      await logout()
    } catch {
      // best-effort — clear the local session regardless
    }
    clearSession()
    navigate('/login')
  }

  async function submitQuestion(question) {
    if (!question || loading) return

    const userMessage = { id: nextLocalId++, role: 'user', content: question }
    appendMessages([userMessage])
    setInput('')
    setLoading(true)

    try {
      const result = await sendChat(question, activeConversationId)
      appendMessages([
        { id: nextLocalId++, role: 'assistant', content: result.answer, sources: result.sources },
      ])
      if (activeConversationId === null) {
        setActiveConversationId(result.conversation_id)
        setConversations((prev) => [
          { id: result.conversation_id, title: question, updated_at: new Date().toISOString() },
          ...prev,
        ])
      }
    } catch (err) {
      appendMessages([
        {
          id: nextLocalId++,
          role: 'assistant',
          isError: true,
          content: err.message || 'Something went wrong reaching the server.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    submitQuestion(input.trim())
  }

  function handleEdit(content) {
    if (loading) return
    setInput(content)
    textareaRef.current?.focus()
  }

  function handleUploadClick() {
    if (uploading) return
    fileInputRef.current?.click()
  }

  async function handleFileSelected(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    const noticeId = nextLocalId++
    appendMessages([{ id: noticeId, role: 'system', content: `Uploading ${file.name}…` }])
    setUploading(true)

    try {
      const result = await uploadDocument(file)
      const text = result.warning
        ? `${result.filename}: ${result.warning}`
        : `Added ${result.filename} — ${result.chunks_indexed} chunk${
            result.chunks_indexed === 1 ? '' : 's'
          } indexed`
      updateMessageById(noticeId, { content: text, isError: !!result.warning })
    } catch (err) {
      updateMessageById(noticeId, { content: err.message || 'Upload failed.', isError: true })
    } finally {
      setUploading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submitQuestion(input.trim())
    }
  }

  return (
    <div className="app-shell">
      <div className="app">
        <header className="app-header">
          <button className="icon-button" onClick={handleToggleHistory} aria-label="Toggle chat history">
            <MenuIcon />
          </button>
          <Link to="/" className="app-header-text" aria-label="Docs Assistant home">
            <span className="app-logo">
              <LogoMark />
            </span>
            <span>
              <h1>Docs Assistant</h1>
              <p>Answers cite the source pages they come from</p>
            </span>
          </Link>
          <button className="new-chat-button" onClick={handleNewChat} disabled={loading}>
            <PlusIcon />
            New
          </button>
        </header>

        {historyOpen && (
          <>
            <div className="history-backdrop" onClick={() => setHistoryOpen(false)} />
            <aside className="history-panel">
              <div className="history-panel-header">
                <span>History</span>
                <button className="icon-button" onClick={() => setHistoryOpen(false)} aria-label="Close history">
                  <CloseIcon />
                </button>
              </div>
              <ul className="history-list">
                {conversations.map((c) => (
                  <li key={c.id}>
                    <button
                      className={`history-item${c.id === activeConversationId ? ' active' : ''}`}
                      onClick={() => handleSelectSession(c.id)}
                    >
                      <span className="history-item-title">{c.title || 'New conversation'}</span>
                      <span
                        className="history-item-delete"
                        role="button"
                        tabIndex={0}
                        aria-label="Delete conversation"
                        onClick={(e) => handleDeleteSession(e, c.id)}
                      >
                        <TrashIcon />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              <div className="history-panel-footer">
                <span className="history-panel-email">{email}</span>
                <button className="message-action" onClick={handleLogout}>
                  <LogoutIcon />
                  Log out
                </button>
              </div>
            </aside>
          </>
        )}

        <main className="chat">
          {!initializing && messages.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-badge">DA</div>
              <h2>What would you like to know?</h2>
              <p>
                I only know what's in the indexed documents — technical guides, company
                policy, and reference material. I won't guess about anything outside that.
              </p>
              <div className="example-chips">
                {EXAMPLE_PROMPTS.map((prompt) => (
                  <button key={prompt} className="example-chip" onClick={() => submitQuestion(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) =>
            message.role === 'system' ? (
              <SystemNotice key={message.id} message={message} />
            ) : (
              <Message key={message.id} message={message} onEdit={handleEdit} />
            )
          )}

          {loading && (
            <div className="message message-assistant">
              <div className="message-bubble message-loading">
                <TypingIndicator />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </main>

        <form className="composer" onSubmit={handleSubmit}>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            onChange={handleFileSelected}
            hidden
          />
          <button
            type="button"
            className="upload-button"
            onClick={handleUploadClick}
            disabled={uploading}
            aria-label="Upload a PDF"
            title="Upload a PDF"
          >
            <UploadIcon />
          </button>
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question…"
            disabled={loading}
            aria-label="Question"
          />
          <button type="submit" disabled={loading || !input.trim()} aria-label="Send">
            <SendIcon />
          </button>
        </form>
      </div>
    </div>
  )
}
