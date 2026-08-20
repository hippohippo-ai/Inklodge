import { useMemo, useState } from 'react'
import { renderMarkdown } from '../lib/markdown.js'
import { STATE_FILES } from '../lib/novels.js'

export default function StateFiles({ novel, onChange }) {
  const isLocal = novel.source === 'local'
  const files = novel.stateFiles || {}
  const [active, setActive] = useState('requirements')
  const [mode, setMode] = useState('preview')
  const [draft, setDraft] = useState('')
  const [dirty, setDirty] = useState(false)

  const current = STATE_FILES.find((f) => f.name === active) || STATE_FILES[0]
  const content = files[active] || ''

  const select = (name) => {
    setActive(name)
    setDraft('')
    setDirty(false)
    setMode('preview')
  }

  const save = () => {
    onChange({ ...novel, stateFiles: { ...files, [active]: draft } })
    setDirty(false)
  }

  const html = useMemo(() => renderMarkdown(content), [content])

  return (
    <div className="statefiles">
      <div className="statefile-tabs">
        {STATE_FILES.map((f) => (
          <button
            key={f.name}
            className={`statefile-tab ${f.name === active ? 'active' : ''}`}
            onClick={() => select(f.name)}
          >
            {f.title}
          </button>
        ))}
      </div>

      <div className="statefile-panel">
        <div className="statefile-head">
          <h3>{current.title}</h3>
          {isLocal ? (
            <div className="seg">
              <button className={`seg-btn ${mode === 'preview' ? 'active' : ''}`} onClick={() => setMode('preview')}>
                预览
              </button>
              <button className={`seg-btn ${mode === 'edit' ? 'active' : ''}`} onClick={() => setMode('edit')}>
                编辑
              </button>
            </div>
          ) : (
            <span className="pill">只读（楼中藏书）</span>
          )}
        </div>

        {!isLocal ? (
          <div className="markdown-body" dangerouslySetInnerHTML={{ __html: html }} />
        ) : mode === 'preview' ? (
          <div className="markdown-body" dangerouslySetInnerHTML={{ __html: html }} />
        ) : (
          <>
            <textarea
              className="editor-textarea tall"
              value={dirty ? draft : content}
              onChange={(e) => {
                setDraft(e.target.value)
                setDirty(true)
              }}
            />
            {dirty && (
              <div className="statefile-save">
                <button className="btn primary" onClick={save}>
                  保存此页
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
