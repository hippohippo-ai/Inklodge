import { useMemo, useState } from 'react'
import { renderMarkdown } from '../lib/markdown.js'

export default function Writer({ novel, onChange }) {
  const isLocal = novel.source === 'local'
  const chapters = novel.chapters || []
  const [idx, setIdx] = useState(0)
  const [mode, setMode] = useState('edit') // edit | preview
  const [draft, setDraft] = useState('')
  const [dirty, setDirty] = useState(false)

  const current = chapters[idx]
  const safeIdx = Math.min(idx, Math.max(0, chapters.length - 1))

  const selectChapter = (i) => {
    setIdx(i)
    setDraft('')
    setDirty(false)
  }

  const addChapter = () => {
    const id = `chapter-${String(chapters.length + 1).padStart(2, '0')}`
    const next = {
      ...novel,
      chapters: [...chapters, { id, title: `第${chapters.length + 1}章`, content: '' }],
    }
    onChange(next)
    selectChapter(chapters.length)
  }

  const saveDraft = () => {
    const next = {
      ...novel,
      chapters: chapters.map((c, i) => (i === safeIdx ? { ...c, content: draft } : c)),
    }
    onChange(next)
    setDirty(false)
  }

  const display = useMemo(() => {
    if (dirty) return draft
    return current ? current.content : ''
  }, [draft, dirty, current])

  if (!isLocal) {
    return (
      <div className="writer readonly">
        <div className="notice">
          <strong>仓库内置小说为只读。</strong>
          <p>
            正文由 AI 生成器直接写在仓库的 <code>novel/</code> 目录里，
            运行 <code>npm run build</code> 同步后即可在「阅读」页查看。
            本地草稿才可在本页直接编辑。
          </p>
        </div>
        <ChapterList chapters={chapters} idx={safeIdx} onSelect={selectChapter} />
        <div className="chapter-editor">
          <div className="editor-head">
            <span>{current ? current.title : '（无章节）'}</span>
          </div>
          <div className="markdown-body preview" style={{ fontSize: '18px' }}>
            {current && (
              <div dangerouslySetInnerHTML={{ __html: renderMarkdown(current.content) }} />
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="writer">
      <div className="writer-toolbar">
        <button className="btn primary" onClick={addChapter}>
          ＋ 新建章节
        </button>
        <div className="seg">
          <button className={`seg-btn ${mode === 'edit' ? 'active' : ''}`} onClick={() => setMode('edit')}>
            编辑
          </button>
          <button className={`seg-btn ${mode === 'preview' ? 'active' : ''}`} onClick={() => setMode('preview')}>
            预览
          </button>
        </div>
        {dirty && (
          <button className="btn primary" onClick={saveDraft}>
            保存本章
          </button>
        )}
      </div>
      <ChapterList chapters={chapters} idx={safeIdx} onSelect={selectChapter} />
      <div className="chapter-editor">
        <div className="editor-head">
          <input
            className="editor-title-input"
            value={current ? current.title : ''}
            onChange={(e) => {
              const next = {
                ...novel,
                chapters: chapters.map((c, i) => (i === safeIdx ? { ...c, title: e.target.value } : c)),
              }
              onChange(next)
            }}
            placeholder="章节标题"
          />
        </div>
        {mode === 'edit' ? (
          <textarea
            className="editor-textarea"
            value={display}
            placeholder="在这里写正文……（支持 Markdown）"
            onChange={(e) => {
              setDraft(e.target.value)
              setDirty(true)
            }}
          />
        ) : (
          <div className="markdown-body preview" style={{ fontSize: '18px' }}>
            <div dangerouslySetInnerHTML={{ __html: renderMarkdown(display) }} />
          </div>
        )}
      </div>
    </div>
  )
}

function ChapterList({ chapters, idx, onSelect }) {
  if (chapters.length === 0) {
    return <p className="empty-hint">还没有章节。本地草稿点「新建章节」，仓库内置由 AI 写入。</p>
  }
  return (
    <aside className="chapter-list">
      {chapters.map((c, i) => (
        <button
          key={c.id}
          className={`chapter-item ${i === idx ? 'active' : ''}`}
          onClick={() => onSelect(i)}
        >
          <span className="toc-no">{i + 1}</span>
          <span className="toc-title">{c.title}</span>
        </button>
      ))}
    </aside>
  )
}
