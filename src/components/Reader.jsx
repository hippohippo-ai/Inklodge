import { useEffect, useMemo, useState } from 'react'
import { renderMarkdown } from '../lib/markdown.js'
import { getReadingPos, setReadingPos } from '../lib/novels.js'

const THEMES = [
  { key: 'paper', label: '纸' },
  { key: 'ink', label: '墨' },
  { key: 'night', label: '夜' },
]

export default function Reader({ novel }) {
  const chapters = novel.chapters || []
  const [idx, setIdx] = useState(() => {
    const saved = getReadingPos(novel.id)
    return saved < chapters.length ? saved : 0
  })
  const [fontSize, setFontSize] = useState(
    Number(localStorage.getItem('shuoshulou.fontsize') || localStorage.getItem('huaben.fontsize') || 19)
  )
  const [theme, setTheme] = useState(
    localStorage.getItem('shuoshulou.theme') || localStorage.getItem('huaben.theme') || 'paper'
  )

  useEffect(() => {
    if (chapters.length) setReadingPos(novel.id, idx)
  }, [idx, novel.id, chapters.length])

  useEffect(() => {
    localStorage.setItem('shuoshulou.fontsize', String(fontSize))
  }, [fontSize])

  useEffect(() => {
    localStorage.setItem('shuoshulou.theme', theme)
  }, [theme])

  const current = chapters[idx]
  const html = useMemo(
    () => (current ? renderMarkdown(current.content) : ''),
    [current]
  )

  if (chapters.length === 0) {
    return (
      <div className="reader-empty">
        <h3>还没有正文</h3>
        <p>
          这本书的正文由 AI 生成器撰写。写好章节后同步进仓库并重新构建，
          就会出现在这里；也可以在「写作」页为本地草稿直接写。
        </p>
      </div>
    )
  }

  return (
    <div className={`reader reader-${theme}`}>
      <aside className="reader-side">
        <div className="reader-side-head">
          <span className="reader-chapter-count">{chapters.length} 章</span>
        </div>
        <div className="reader-toc">
          {chapters.map((c, i) => (
            <button
              key={c.id}
              className={`toc-item ${i === idx ? 'active' : ''}`}
              onClick={() => setIdx(i)}
            >
              <span className="toc-no">{i + 1}</span>
              <span className="toc-title">{c.title}</span>
            </button>
          ))}
        </div>
      </aside>

      <main className="reader-main">
        <div className="reader-toolbar">
          <span className="reader-chapter-label">
            {idx + 1} / {chapters.length} 章
          </span>
          <div className="toolbar-group">
            <button className="icon-btn" onClick={() => setFontSize((s) => Math.max(13, s - 1))} title="减小字号">
              A−
            </button>
            <span className="fontsize">{fontSize}</span>
            <button className="icon-btn" onClick={() => setFontSize((s) => Math.min(30, s + 1))} title="增大字号">
              A+
            </button>
          </div>
          <div className="toolbar-group">
            {THEMES.map((t) => (
              <button
                key={t.key}
                className={`icon-btn ${theme === t.key ? 'active' : ''}`}
                onClick={() => setTheme(t.key)}
                title={t.label}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <article className="reader-article" style={{ fontSize: `${fontSize}px` }}>
          {current && (
            <>
              <h1 className="chapter-title">{current.title}</h1>
              <div
                className="markdown-body"
                dangerouslySetInnerHTML={{ __html: html }}
              />
            </>
          )}
        </article>

        <div className="reader-nav">
          <button
            className="btn ghost"
            disabled={idx === 0}
            onClick={() => setIdx((i) => Math.max(0, i - 1))}
          >
            ← 上一章
          </button>
          <button
            className="btn primary"
            disabled={idx === chapters.length - 1}
            onClick={() => setIdx((i) => Math.min(chapters.length - 1, i + 1))}
          >
            下一章 →
          </button>
        </div>
      </main>
    </div>
  )
}
