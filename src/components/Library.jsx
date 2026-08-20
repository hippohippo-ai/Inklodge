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
          <span className="brand-mark">说书楼</span>
          <span className="brand-sub">写书 · 读书 · 说书</span>
        </div>
        <div className="header-actions">
          <button className="btn ghost" onClick={() => exportLocalNovels()}>
            导出书稿
          </button>
          <button className="btn ghost" onClick={() => fileRef.current?.click()}>
            导入书稿
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json"
            style={{ display: 'none' }}
            onChange={(e) => handleImport(e.target.files[0])}
          />
          <button className="btn primary" onClick={() => setShowNew(true)}>
            ＋ 开新书
          </button>
        </div>
      </header>

      <section className="story-stage" aria-label="说书台">
        <div className="story-scroll">
          <span className="scroll-kicker">说书楼</span>
          <strong>一盏灯，半卷书</strong>
          <small>今日开讲，诸位请坐</small>
        </div>
        <div className="story-desk">
          <span className="desk-lamp">◆</span>
          <span>书场已开</span>
        </div>
      </section>

      {showNew && (
        <div className="modal-mask" onClick={() => setShowNew(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>开一部新书（案头草稿）</h3>
            <label>
              书名
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="例如：高太公造反"
                autoFocus
              />
            </label>
            <label>
              题眼 / 一句话
              <input
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                placeholder="例如：老农死后入地府造反，一路打上天庭西天"
              />
            </label>
            <div className="modal-actions">
              <button className="btn ghost" onClick={() => setShowNew(false)}>
                先不落笔
              </button>
              <button className="btn primary" onClick={createNovel} disabled={!title.trim()}>
                立卷
              </button>
            </div>
            <p className="hint">
              先在案头起草。若要正式开写，请按 README 使用 AI 生成器；写成后运行构建，书稿便会收入「楼中藏书」。
            </p>
          </div>
        </div>
      )}

      <section className="shelf">
        <h2 className="shelf-title">楼中藏书</h2>
        {bundled.length === 0 && <p className="empty-hint">楼中暂时空着。用 AI 生成器写好书稿后，运行 <code>npm run build</code>，它便会登楼。</p>}
        <div className="card-grid">
          {bundled.map((n) => (
            <NovelCard key={n.id} n={n} onOpen={() => onOpen(n.id)} />
          ))}
        </div>
      </section>

      <section className="shelf">
        <h2 className="shelf-title">案头草稿</h2>
        {local.length === 0 && <p className="empty-hint">案头还没有草稿。点右上角「开新书」，即可落笔。</p>}
        <div className="card-grid">
          {local.map((n) => (
            <NovelCard key={n.id} n={n} onOpen={() => onOpen(n.id)} />
          ))}
        </div>
      </section>

      <footer className="site-footer">
        说书楼 · 多小说写作与阅读平台 · 正文由 AI 生成器撰写，本页负责管理与阅读
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
