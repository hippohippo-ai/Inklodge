import { useState } from 'react'
import Reader from './Reader.jsx'
import Writer from './Writer.jsx'
import StateFiles from './StateFiles.jsx'
import Progress from './Progress.jsx'
import StorytellerArchive from './StorytellerArchive.jsx'
import { saveLocalNovel, deleteLocalNovel } from '../lib/novels.js'

const TABS = [
  { key: 'read', label: '入卷阅读' },
  { key: 'write', label: '落笔写作' },
  { key: 'state', label: '查看设定' },
  { key: 'progress', label: '查看进度' },
  { key: 'archive', label: '说书人档案' },
]

export default function Novel({ novel, loading, onBack, onUpdate }) {
  const [tab, setTab] = useState('read')
  const [confirmDelete, setConfirmDelete] = useState(false)

  if (loading || !novel) {
    return <div className="app-loading">Inklodge · 打开《{novel?.title || ''}》……</div>
  }

  const isLocal = novel.source === 'local'

  const save = (next) => {
    if (next.source === 'local') saveLocalNovel(next)
    onUpdate(next)
  }

  const remove = () => {
    deleteLocalNovel(novel.id)
    onBack()
  }

  return (
    <div className="novel">
      <header className="novel-header">
        <button className="btn ghost back" onClick={onBack}>
          ← 回墨庐
        </button>
        <div className="novel-title">
          <span className="novel-name">{novel.title}</span>
          <span className="novel-source">{isLocal ? '案头草稿' : '墨庐藏书'}</span>
        </div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`tab ${tab === t.key ? 'active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="novel-actions">
          {isLocal && (
            <>
              {!confirmDelete ? (
                <button className="btn danger-ghost" onClick={() => setConfirmDelete(true)}>
                  撤下草稿
                </button>
              ) : (
                <span className="confirm-row">
                  <span>确认撤下这部草稿？</span>
                  <button className="btn danger" onClick={remove}>
                    撤下
                  </button>
                  <button className="btn ghost" onClick={() => setConfirmDelete(false)}>
                    保留
                  </button>
                </span>
              )}
            </>
          )}
        </div>
      </header>

      <div className="novel-body">
        {tab === 'read' && <Reader novel={novel} />}
        {tab === 'write' && <Writer novel={novel} onChange={save} />}
        {tab === 'state' && <StateFiles novel={novel} onChange={save} />}
        {tab === 'progress' && <Progress novel={novel} />}
        {tab === 'archive' && <StorytellerArchive novel={novel} onChange={save} />}
      </div>
    </div>
  )
}
