import { useEffect, useMemo, useRef, useState } from 'react'
import { renderMarkdown } from '../lib/markdown.js'
import { getReadingPos, setReadingPos } from '../lib/novels.js'

const THEMES = [
  { key: 'paper', label: '纸' },
  { key: 'ink', label: '墨' },
  { key: 'night', label: '夜' },
]

const BM_KEY = 'inklodge.bookmarks'
const FONT_KEY = 'inklodge.fontsize'
const THEME_KEY = 'inklodge.theme'

// 旧版「shuoshulou.*」键名：首次读取时迁移到 inklodge.*，避免书签与设置丢失
const LEGACY_KEYS = {
  [BM_KEY]: 'shuoshulou.bookmarks',
  [FONT_KEY]: 'shuoshulou.fontsize',
  [THEME_KEY]: 'shuoshulou.theme',
}

function readStorage(key, fallback = null) {
  try {
    const current = localStorage.getItem(key)
    if (current !== null) return current
    const legacy = localStorage.getItem(LEGACY_KEYS[key])
    if (legacy !== null) {
      localStorage.setItem(key, legacy)
      localStorage.removeItem(LEGACY_KEYS[key])
      return legacy
    }
  } catch { /* ignore */ }
  return fallback
}

function loadBookmarks(novelId) {
  try {
    const all = JSON.parse(readStorage(BM_KEY, '{}') || '{}')
    return all[novelId] || []
  } catch {
    return []
  }
}

function saveBookmarks(novelId, bms) {
  try {
    const all = JSON.parse(readStorage(BM_KEY, '{}') || '{}')
    all[novelId] = bms
    localStorage.setItem(BM_KEY, JSON.stringify(all))
  } catch { /* ignore */ }
}

export default function Reader({ novel }) {
  const chapters = novel.chapters || []
  const [idx, setIdx] = useState(() => {
    const saved = getReadingPos(novel.id)
    return saved < chapters.length ? saved : 0
  })
  const [fontSize, setFontSize] = useState(
    Number(readStorage(FONT_KEY, '19') || 19)
  )
  const [theme, setTheme] = useState(
    readStorage(THEME_KEY, 'paper') || 'paper'
  )

  // UI state
  const [showToc, setShowToc] = useState(false)
  const [showBookmarks, setShowBookmarks] = useState(false)
  const [headerVisible, setHeaderVisible] = useState(true)
  const [bookmarks, setBookmarks] = useState(() => loadBookmarks(novel.id))

  const scrollRef = useRef(null)
  const lastScrollTop = useRef(0)

  // Persist reading position
  useEffect(() => {
    if (chapters.length) setReadingPos(novel.id, idx)
    if (scrollRef.current) scrollRef.current.scrollTop = 0
    lastScrollTop.current = 0
    setHeaderVisible(true)
  }, [idx, novel.id, chapters.length])

  // Persist preferences
  useEffect(() => {
    localStorage.setItem(FONT_KEY, String(fontSize))
  }, [fontSize])

  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  useEffect(() => {
    saveBookmarks(novel.id, bookmarks)
  }, [bookmarks, novel.id])

  // Scroll-to-hide logic
  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const st = el.scrollTop
    if (Math.abs(st - lastScrollTop.current) < 8) return
    if (st > lastScrollTop.current && st > 60) {
      setHeaderVisible(false)
    } else {
      setHeaderVisible(true)
    }
    lastScrollTop.current = st
  }

  const toggleBars = () => setHeaderVisible((v) => !v)

  // Current chapter
  const current = chapters[idx]

  // Strip the first # heading from markdown to avoid duplicate title display
  const cleanContent = useMemo(() => {
    if (!current) return ''
    return current.content.replace(/^#\s+.+(\r?\n)+/, '')
  }, [current])

  const html = useMemo(() => renderMarkdown(cleanContent), [cleanContent])

  // Bookmark helpers
  const isBookmarked = bookmarks.some((b) => b.chapterIdx === idx)
  const toggleBookmark = () => {
    if (isBookmarked) {
      setBookmarks(bookmarks.filter((b) => b.chapterIdx !== idx))
    } else {
      const bm = {
        id: Date.now(),
        chapterIdx: idx,
        chapterTitle: current?.title || `第${idx + 1}章`,
        time: new Date().toLocaleDateString('zh-CN', {
          month: 'numeric',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
      }
      setBookmarks([bm, ...bookmarks])
    }
  }

  const jumpToBookmark = (chapterIdx) => {
    setIdx(chapterIdx)
    setShowBookmarks(false)
  }

  const removeBookmark = (e, id) => {
    e.stopPropagation()
    setBookmarks(bookmarks.filter((b) => b.id !== id))
  }

  // Empty state
  if (chapters.length === 0) {
    return (
      <div className="reader-empty">
        <h3>此卷尚无正文</h3>
        <p>
          正文由 AI 生成器落笔。写好章节后同步书库并重新构建，书稿便会出现在这里。
        </p>
      </div>
    )
  }

  return (
    <div className={`reader reader-${theme}`}>
      {/* Floating header */}
      <header className={`reader-header-bar ${headerVisible ? 'visible' : 'hidden'}`}>
        <div className="bar-left">
          <button className="icon-btn-text" onClick={() => setShowToc(true)} title="目录">
            ☰ 目录
          </button>
          <button
            className={`icon-btn-text ${isBookmarked ? 'bookmarked' : ''}`}
            onClick={toggleBookmark}
            title={isBookmarked ? '取消书签' : '加入书签'}
          >
            {isBookmarked ? '★ 已书签' : '☆ 存书签'}
          </button>
          <button className="icon-btn-text" onClick={() => setShowBookmarks(true)} title="书签列表">
            书签盒 ({bookmarks.length})
          </button>
        </div>

        <div className="bar-center">
          <span className="current-chapter-text">{current?.title}</span>
        </div>

        <div className="bar-right">
          <div className="font-controls">
            <button className="icon-btn" onClick={() => setFontSize((s) => Math.max(14, s - 1))}>A−</button>
            <span className="fontsize">{fontSize}</span>
            <button className="icon-btn" onClick={() => setFontSize((s) => Math.min(32, s + 1))}>A+</button>
          </div>
          <div className="theme-controls">
            {THEMES.map((t) => (
              <button
                key={t.key}
                className={`theme-dot ${theme === t.key ? 'active' : ''}`}
                onClick={() => setTheme(t.key)}
                title={t.label}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Drawer TOC */}
      {showToc && (
        <div className="drawer-mask" onClick={() => setShowToc(false)}>
          <aside className="drawer-content toc-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-head">
              <h3>目录（共 {chapters.length} 章）</h3>
              <button className="close-btn" onClick={() => setShowToc(false)}>✕</button>
            </div>
            <div className="drawer-list">
              {chapters.map((c, i) => (
                <button
                  key={c.id}
                  className={`toc-drawer-item ${i === idx ? 'active' : ''}`}
                  onClick={() => { setIdx(i); setShowToc(false) }}
                >
                  <span className="toc-no">{String(i + 1).padStart(2, '0')}</span>
                  <span className="toc-title">{c.title}</span>
                </button>
              ))}
            </div>
          </aside>
        </div>
      )}

      {/* Bookmarks drawer */}
      {showBookmarks && (
        <div className="drawer-mask" onClick={() => setShowBookmarks(false)}>
          <aside className="drawer-content bookmarks-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-head">
              <h3>书签记录</h3>
              <button className="close-btn" onClick={() => setShowBookmarks(false)}>✕</button>
            </div>
            <div className="drawer-list">
              {bookmarks.length === 0 ? (
                <div className="empty-bookmarks">暂无书签。阅读时点击顶部「☆ 存书签」添加。</div>
              ) : (
                bookmarks.map((b) => (
                  <div key={b.id} className="bookmark-item" onClick={() => jumpToBookmark(b.chapterIdx)}>
                    <div className="bm-info">
                      <span className="bm-title">{b.chapterTitle}</span>
                      <span className="bm-time">{b.time}</span>
                    </div>
                    <button className="bm-del" onClick={(e) => removeBookmark(e, b.id)}>删除</button>
                  </div>
                ))
              )}
            </div>
          </aside>
        </div>
      )}

      {/* Scrollable reading area */}
      <main
        className="reader-scroll-container"
        ref={scrollRef}
        onScroll={handleScroll}
        onClick={toggleBars}
      >
        <article className="reader-article" style={{ fontSize: `${fontSize}px` }}>
          {current && (
            <>
              <h1 className="chapter-main-title">{current.title}</h1>
              <div className="markdown-body" dangerouslySetInnerHTML={{ __html: html }} />
            </>
          )}
        </article>
      </main>

      {/* Floating footer */}
      <footer className={`reader-footer-bar ${headerVisible ? 'visible' : 'hidden'}`}>
        <button
          className="btn ghost page-btn"
          disabled={idx === 0}
          onClick={(e) => { e.stopPropagation(); setIdx((i) => Math.max(0, i - 1)) }}
        >
          ← 上一章
        </button>

        <div className="chapter-slider-wrap" onClick={(e) => e.stopPropagation()}>
          <input
            type="range"
            min={0}
            max={chapters.length - 1}
            value={idx}
            onChange={(e) => setIdx(Number(e.target.value))}
            className="chapter-slider"
          />
          <span className="slider-label">{idx + 1} / {chapters.length}</span>
        </div>

        <button
          className="btn primary page-btn"
          disabled={idx === chapters.length - 1}
          onClick={(e) => { e.stopPropagation(); setIdx((i) => Math.min(chapters.length - 1, i + 1)) }}
        >
          下一章 →
        </button>
      </footer>
    </div>
  )
}
