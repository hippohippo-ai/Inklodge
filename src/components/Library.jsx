import { useRef, useState } from 'react'
import {
  createLocalNovel,
  exportLocalNovels,
  importLocalNovels,
} from '../lib/novels.js'

export default function Library({ library, onOpen, onChanged }) {
  const [showNew, setShowNew] = useState(false)
  const [title, setTitle] = useState('')
  const [theme, setTheme] = useState('')
  const fileRef = useRef(null)

  const createNovel = () => {
    if (!title.trim()) return
    createLocalNovel({ title: title.trim(), theme: theme.trim() })
    setTitle('')
    setTheme('')
    setShowNew(false)
    onChanged()
  }

  const handleImport = async (file) => {
    if (!file) return
    try {
      const n = await importLocalNovels(file)
      alert(`已收入楼中 ${n} 本书稿`)
      onChanged()
    } catch {
      alert('入楼失败：JSON 格式不正确')
    }
    if (fileRef.current) fileRef.current.value = ''
  }

  const bundled = library.filter((n) => n.source === 'bundled')
  const local = library.filter((n) => n.source === 'local')

  return (
    <div className="library">
      <header className="site-header">
        <div className="site-brand">
          <span className="brand-mark">Inklodge</span>
          <span className="brand-sub">墨庐 · 卷册</span>
        </div>
        <div className="header-actions">
          <button className="btn ghost" onClick={() => exportLocalNovels()}>
            导出卷册
          </button>
          <button className="btn ghost" onClick={() => fileRef.current?.click()}>
            导入卷册
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json"
            style={{ display: 'none' }}
            onChange={(e) => handleImport(e.target.files[0])}
          />
          <button className="btn primary" onClick={() => setShowNew(true)}>
            ＋ 起草新卷
          </button>
        </div>
      </header>

      <section className="stage-quote" aria-label="题词">
        <p>一盏清灯，半卷残篇；事落纸墨，方有回声。</p>
        <span>INKS, SCROLLS & TALES</span>
      </section>

      {showNew && (
        <div className="modal-mask" onClick={() => setShowNew(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>起草新卷</h3>
            <label>
              卷名
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="例如：留春信"
                autoFocus
              />
            </label>
            <label>
              立题 / 题眼
              <input
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                placeholder="例如：七日冥婚，七封残信与七条江湖路"
              />
            </label>
            <div className="modal-actions">
              <button className="btn ghost" onClick={() => setShowNew(false)}>
                暂歇
              </button>
              <button className="btn primary" onClick={createNovel} disabled={!title.trim()}>
                立卷
              </button>
            </div>
          </div>
        </div>
      )}

      <section className="shelf">
        <h2 className="shelf-title">藏卷典藏</h2>
        {bundled.length === 0 && <p className="empty-hint">暂无藏卷。</p>}
        <div className="card-grid">
          {bundled.map((n) => (
            <NovelCard key={n.id} n={n} onOpen={() => onOpen(n.id)} />
          ))}
        </div>
      </section>

      <section className="shelf">
        <h2 className="shelf-title">案头草稿</h2>
        {local.length === 0 && <p className="empty-hint">案头还没有草稿。点「起草新卷」，即可落笔。</p>}
        <div className="card-grid">
          {local.map((n) => (
            <NovelCard key={n.id} n={n} onOpen={() => onOpen(n.id)} />
          ))}
        </div>
      </section>

      <footer className="site-footer">
        Inklodge · 墨庐 · 写作与阅读空间
      </footer>
    </div>
  )
}

function NovelCard({ n, onOpen }) {
  const pct =
    n.progress.totalChapters > 0
      ? Math.min(100, Math.round((n.progress.currentChapter / n.progress.totalChapters) * 100))
      : 0
  return (
    <button className="novel-card" onClick={onOpen} style={{ '--cover': n.cover }}>
      <div className="card-cover">
        <span className="card-title">{n.title}</span>
        <span className="card-tag">{n.source === 'bundled' ? '楼中' : '案头'}</span>
      </div>
      <div className="card-body">
        <p className="card-theme">{n.theme || '（尚未立题）'}</p>
        <p className="card-archive-line">
          {n.archive?.author || '待署名'} · {n.archive?.volumes || 1} 卷
        </p>
        <div className="card-meta">
          <span>{n.chapterCount} 章</span>
          <span>{n.progress.status || '—'}</span>
        </div>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>
    </button>
  )
}
