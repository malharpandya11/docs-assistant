import { Link } from 'react-router-dom'
import './Landing.css'

function LogoMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4L12 2z"
        fill="currentColor"
      />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path
        d="M5 12h14M13 6l6 6-6 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function SourceIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path
        d="M7 3h7l5 5v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M14 3v5h5M9 13h6M9 17h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

function HistoryIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path
        d="M3 12a9 9 0 109-9v4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M3 4v3h3M12 8v5l3 2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function LayersIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 3l9 5-9 5-9-5 9-5z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M3 13l9 5 9-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

const FEATURES = [
  {
    icon: <SourceIcon />,
    title: 'Grounded in your documents',
    body: 'Answers are drawn from whatever you index — Markdown, PDFs, anything with real text — and cite the exact source pages they came from.',
  },
  {
    icon: <HistoryIcon />,
    title: 'Keeps every conversation',
    body: 'Every chat is saved and resumable — pick up any past conversation exactly where you left it, or start a clean one anytime.',
  },
  {
    icon: <LayersIcon />,
    title: 'Never boxed into one topic',
    body: "Index anything — a handbook, a technical guide, a reference doc — and it just knows it. Nothing to reconfigure per document.",
  },
]

export default function Landing() {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <span className="landing-logo">
          <span className="landing-logo-mark">
            <LogoMark />
          </span>
          Docs Assistant
        </span>
        <Link to="/chat" className="landing-nav-cta">
          Open chat
        </Link>
      </nav>

      <header className="landing-hero">
        <h1>
          Ask your documents
          <br />
          anything.
        </h1>
        <p>
          A chat assistant that actually knows what's in your files — and says so, plainly,
          whenever it doesn't.
        </p>
        <Link to="/chat" className="landing-cta">
          Start chatting
          <ArrowIcon />
        </Link>
      </header>

      <section className="landing-features">
        {FEATURES.map((f) => (
          <div className="landing-feature" key={f.title}>
            <div className="landing-feature-icon">{f.icon}</div>
            <h3>{f.title}</h3>
            <p>{f.body}</p>
          </div>
        ))}
      </section>

      <section className="landing-scope">
        <div className="landing-scope-col">
          <h4>Works with</h4>
          <ul>
            <li>Markdown documents</li>
            <li>PDFs with real, extractable text</li>
            <li>Well-structured guides &amp; policies</li>
          </ul>
        </div>
        <div className="landing-scope-col landing-scope-not">
          <h4>Not yet</h4>
          <ul>
            <li>Scanned or image-only PDFs</li>
            <li>Spreadsheets, images, audio/video</li>
            <li>Unstructured notes with no real content</li>
          </ul>
        </div>
      </section>

      <footer className="landing-footer">Built as a demo — answers may be imperfect.</footer>
    </div>
  )
}
