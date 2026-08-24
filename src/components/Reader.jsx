import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { renderMarkdown } from '../lib/markdown.js'
import { getReadingPos, setReadingPos } from '../lib/novels.js'

const THEMES = [
  { key: 'paper', label: '纸色' },
  { key: 'eye', label: '护眼' },
  { key: 'ink', label: '墨色' },
  { key: 'night', label: '暗色' },
]

const VOLUMES = [
  { start: 0, title: '卷一：红灯引路' },
  { start: 8, title: '卷二：七封信' },
  { start: 16, title: '卷三：出庄之后' },
  { start: 24, title: '卷四：冥婚' },
  { start: 32, title: '卷五：灯灭之后' },
]

function volumeTitle(index) {
  return VOLUMES.find((volume, i) => {
    const next = VOLUMES[i + 1]
    return index >= volume.start && (!next || index < next.start)
  })?.title
}

const BM_KEY = 'inklodge.bookmarks'
const FONT_KEY = 'inklodge.fontsize'
const FONT_DEFAULT_KEY = 'inklodge.fontsize.default-v2'
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

function initialFontSize() {
  const stored = Number(readStorage(FONT_KEY, '') || 0)
  try {
    // 将旧版默认的 19px 只迁移一次，用户之后的字号选择继续保留。
    if (!localStorage.getItem(FONT_DEFAULT_KEY)) {
      localStorage.setItem(FONT_DEFAULT_KEY, '1')
      return stored === 19 || !stored ? 17 : stored
    }
  } catch { /* ignore */ }
  return stored || 17
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

function chapterName(title = '') {
  return title.replace(/^第[0-9０-９一二三四五六七八九十百千万]+章[：:\s·—-]*/, '').trim() || title
}

export default function Reader({ novel }) {
  const chapters = novel.chapters || []
  const [idx, setIdx] = useState(() => {
    const saved = getReadingPos(novel.id)
    return saved < chapters.length ? saved : 0
  })
  const [fontSize, setFontSize] = useState(initialFontSize)
  const [theme, setTheme] = useState(
    readStorage(THEME_KEY, 'paper') || 'paper'
  )

  // UI state
  const [showToc, setShowToc] = useState(false)
  const [showBookmarks, setShowBookmarks] = useState(false)
  const [footerVisible, setFooterVisible] = useState(true)
  const [headerVisible, setHeaderVisible] = useState(true)
  const [bookmarks, setBookmarks] = useState(() => loadBookmarks(novel.id))

  const scrollRef = useRef(null)
  const lastScrollTop = useRef(0)

  // Persist reading position
  useEffect(() => {
    if (chapters.length) setReadingPos(novel.id, idx)
  }, [idx, novel.id, chapters.length])

  // 切章后始终回到新章节开头；用 layout effect 避免先闪现上一章尾部。
  useLayoutEffect(() => {
    const el = scrollRef.current
    if (el) {
      // 覆盖 CSS 的 scroll-behavior: smooth，切章时立即跳回顶部，不做平滑动画。
      const prev = el.style.scrollBehavior
      el.style.scrollBehavior = 'auto'
      el.scrollTop = 0
      el.style.scrollBehavior = prev
    }
    lastScrollTop.current = 0
    setFooterVisible(true)
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

  // 手机上按阅读手势控制底部导航：上滑（正文向上滚动）显示，下滑隐藏。
  // 桌面端保持导航常显，滚动时不收起。
  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const st = Math.max(0, el.scrollTop)
    const delta = st - lastScrollTop.current
    if (Math.abs(delta) < 2) return
    const mobile = window.matchMedia('(max-width: 820px)').matches
    // 正文向下（scrollTop 增大）时收起；向上回滚时重新出现。
    const visible = mobile ? st <= 0 || delta < 0 : true
    setFooterVisible(visible)
    setHeaderVisible(visible)
    lastScrollTop.current = st
  }

  // Current chapter
  const current = chapters[idx]
  const currentChapterName = chapterName(current?.title || '')

  // Strip the first # heading from markdown to avoid duplicate title display
  const cleanContent = useMemo(() => {
    if (!current) return ''
    return current.content.replace(/^\uFEFF?#\s+[^\r\n]*(?:\r?\n|$)/, '')
  }, [current])

  const html = useMemo(() => {
    const rendered = renderMarkdown(cleanContent)
    return rendered.replace(/<p>([\s\S]*?)<\/p>/g, (full, inner) => {
      const text = inner.replace(/<[^>]*>/g, '').replace(/&(?:amp|lt|gt|quot|#39);/g, 'x')
      const className = text.trim().length < 15 ? 'short-paragraph' : ''
      return `<p${className ? ` class="${className}"` : ''}>${inner}</p>`
    })
  }, [cleanContent])

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

        <div className="bar-center reader-meta" aria-label="当前阅读位置">
          <span className="reader-book-title">{novel.title}</span>
          <span className="reader-meta-separator">·</span>
          <span className="reader-chapter-number">第{idx + 1}章</span>
          <span className="reader-meta-separator">·</span>
          <span className="current-chapter-text">{currentChapterName}</span>
        </div>

        <div className="mobile-font-controls" aria-label="字号设置">
          <button
            className="mobile-font-btn"
            onClick={() => setFontSize((s) => Math.max(14, s - 1))}
            aria-label="减小字号"
          >A−</button>
          <span>{fontSize}</span>
          <button
            className="mobile-font-btn"
            onClick={() => setFontSize((s) => Math.min(32, s + 1))}
            aria-label="增大字号"
          >A+</button>
        </div>

        <select
          className="mobile-theme-select"
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          aria-label="阅读模式"
        >
          {THEMES.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
        </select>

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
              {chapters.map((c, i) => {
                const volume = volumeTitle(i)
                const prevVolume = i > 0 ? volumeTitle(i - 1) : null
                const showVolumeLabel = volume && volume !== prevVolume
                return (
                  <div key={c.id}>
                    {showVolumeLabel && <div className="toc-volume-label">{volume}</div>}
                    <button
                      className={`toc-drawer-item ${i === idx ? 'active' : ''}`}
                      onClick={() => { setIdx(i); setShowToc(false) }}
                    >
                      <span className="toc-no">{String(i + 1).padStart(2, '0')}</span>
                      <span className="toc-title">{c.title}</span>
                    </button>
                  </div>
                )
              })}
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
      <footer
        className={`reader-footer-bar ${footerVisible ? 'visible' : 'hidden'}`}
        aria-label="章节导航"
      >
        <button
          className="btn ghost page-btn toc-page-btn"
          onClick={() => setShowToc(true)}
        >
          ☰ 返回目录
        </button>
        <button
          className="btn ghost page-btn"
          disabled={idx === 0}
          onClick={() => setIdx((i) => Math.max(0, i - 1))}
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
          onClick={() => setIdx((i) => Math.min(chapters.length - 1, i + 1))}
        >
          下一章 →
        </button>
      </footer>
    </div>
  )
}
