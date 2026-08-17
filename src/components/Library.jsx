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
      alert(`已导入 ${n} 本小说`)
      onChanged()
    } catch {
      alert('导入失败：JSON 格式不对')
    }
    if (fileRef.current) fileRef.current.value = ''
  }

  const bundled = library.filter((n) => n.source === 'bundled')
  const local = library.filter((n) => n.source === 'local')

  return (
    <div className="library">
      <header className="site-header">
        <div className="site-brand">
          <span className="brand-mark">话本</span>
          <span className="brand-sub">写书 · 读书 · 说书</span>
        </div>
        <div className="header-actions">
          <button className="btn ghost" onClick={() => exportLocalNovels()}>
            导出本地小说
          </button>
          <button className="btn ghost" onClick={() => fileRef.current?.click()}>
            导入
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json"
            style={{ display: 'none' }}
            onChange={(e) => handleImport(e.target.files[0])}
          />
          <button className="btn primary" onClick={() => setShowNew(true)}>
            ＋ 新建小说
          </button>
        </div>
      </header>

      {showNew && (
        <div className="modal-mask" onClick={() => setShowNew(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>新建小说（本地草稿）</h3>
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
              主题 / 一句话
              <input
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                placeholder="例如：老农死后入地府造反，一路打上天庭西天"
              />
            </label>
            <div className="modal-actions">
              <button className="btn ghost" onClick={() => setShowNew(false)}>
                取消
              </button>
              <button className="btn primary" onClick={createNovel} disabled={!title.trim()}>
                创建
              </button>
            </div>
            <p className="hint">
              在浏览器里快速起草。正式写作建议用仓库里的 AI 生成器流程（见 README），
              写好后同步进「仓库内置」书库。
            </p>
          </div>
        </div>
      )}

      <section className="shelf">
        <h2 className="shelf-title">仓库内置</h2>
        {bundled.length === 0 && <p className="empty-hint">暂无。用 AI 生成器写好小说后，运行 <code>npm run build</code> 即会同步到这里。</p>}
        <div className="card-grid">
          {bundled.map((n) => (
            <NovelCard key={n.id} n={n} onOpen={() => onOpen(n.id)} />
          ))}
        </div>
      </section>

      <section className="shelf">
        <h2 className="shelf-title">本地草稿</h2>
        {local.length === 0 && <p className="empty-hint">暂无本地草稿。点右上角「新建小说」即可开始。</p>}
        <div className="card-grid">
          {local.map((n) => (
            <NovelCard key={n.id} n={n} onOpen={() => onOpen(n.id)} />
          ))}
        </div>
      </section>

      <footer className="site-footer">
        话本 · 多小说写作与阅读平台 · 正文由 AI 生成器撰写，本页负责管理与阅读
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
        <span className="card-tag">{n.source === 'bundled' ? '仓库' : '草稿'}</span>
      </div>
      <div className="card-body">
        <p className="card-theme">{n.theme || '（未填主题）'}</p>
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
