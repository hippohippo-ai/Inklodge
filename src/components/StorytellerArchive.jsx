import { useState } from 'react'
import { normalizeArchive } from '../lib/novels.js'

export default function StorytellerArchive({ novel, onChange }) {
  const isLocal = novel.source === 'local'
  const archive = normalizeArchive(novel.archive)
  const progress = novel.progress || {}
  const [draft, setDraft] = useState(archive)
  const [progressDraft, setProgressDraft] = useState({
    currentChapter: progress.currentChapter || 0,
    totalChapters: progress.totalChapters || novel.chapters?.length || 0,
    status: progress.status || (isLocal ? '本地草稿' : '规划中'),
  })
  const [dirty, setDirty] = useState(false)

  const updateArchive = (key, value) => {
    setDraft((current) => ({ ...current, [key]: value }))
    setDirty(true)
  }

  const updateProgress = (key, value) => {
    setProgressDraft((current) => ({ ...current, [key]: value }))
    setDirty(true)
  }

  const save = () => {
    onChange({
      ...novel,
      archive: normalizeArchive(draft),
      progress: {
        ...progress,
        currentChapter: Math.max(0, Number(progressDraft.currentChapter) || 0),
        totalChapters: Math.max(0, Number(progressDraft.totalChapters) || 0),
        status: String(progressDraft.status || '').trim() || (isLocal ? '本地草稿' : '规划中'),
      },
    })
    setDirty(false)
  }

  const current = Number(progressDraft.currentChapter) || 0
  const total = Number(progressDraft.totalChapters) || 0
  const percent = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0

  return (
    <div className="archive-page">
      <section className="archive-hero">
        <div>
          <span className="archive-kicker">Inklodge · 人物与书稿登记</span>
          <h2>说书人档案</h2>
          <p>一部书先记下落笔之人的姓名，再记下它走过的路。</p>
        </div>
        <span className="archive-seal">{isLocal ? '案头' : '楼藏'}</span>
      </section>

      <div className="archive-grid">
        <section className="archive-card archive-profile">
          <div className="archive-card-head">
            <h3>书稿名录</h3>
            <span className="pill">{isLocal ? '可编辑' : '只读'}</span>
          </div>
          <dl className="archive-details">
            <div>
              <dt>书名</dt>
              <dd>{novel.title}</dd>
            </div>
            <div>
              <dt>作者</dt>
              <dd>
                {isLocal ? (
                  <input
                    className="archive-input"
                    value={draft.author}
                    onChange={(e) => updateArchive('author', e.target.value)}
                    placeholder="写下说书人的名字"
                  />
                ) : (
                  archive.author
                )}
              </dd>
            </div>
            <div>
              <dt>卷数</dt>
              <dd>
                {isLocal ? (
                  <input
                    className="archive-input archive-number"
                    type="number"
                    min="1"
                    value={draft.volumes}
                    onChange={(e) => updateArchive('volumes', e.target.value)}
                  />
                ) : (
                  `${archive.volumes} 卷`
                )}
              </dd>
            </div>
          </dl>
        </section>

        <section className="archive-card archive-epigraph">
          <div className="archive-card-head">
            <h3>题词</h3>
            <span className="archive-brush">卷首</span>
          </div>
          {isLocal ? (
            <textarea
              className="archive-textarea"
              value={draft.epigraph}
              onChange={(e) => updateArchive('epigraph', e.target.value)}
              placeholder="写一句留给这部书的话……"
              rows="4"
            />
          ) : (
            <blockquote>{archive.epigraph || '尚未题词'}</blockquote>
          )}
        </section>

        <section className="archive-card archive-progress-card">
          <div className="archive-card-head">
            <h3>创作进度</h3>
            <span className="archive-percent">{percent}%</span>
          </div>
          <div className="archive-progress-numbers">
            {isLocal ? (
              <>
                <label>
                  已写
                  <input
                    className="archive-input archive-number"
                    type="number"
                    min="0"
                    value={progressDraft.currentChapter}
                    onChange={(e) => updateProgress('currentChapter', e.target.value)}
                  />
                  章
                </label>
                <span>/</span>
                <label>
                  计划
                  <input
                    className="archive-input archive-number"
                    type="number"
                    min="0"
                    value={progressDraft.totalChapters}
                    onChange={(e) => updateProgress('totalChapters', e.target.value)}
                  />
                  章
                </label>
              </>
            ) : (
              <strong>{current} / {total} 章</strong>
            )}
          </div>
          <div className="progress-track big">
            <div className="progress-fill" style={{ width: `${percent}%` }} />
          </div>
          <label className="archive-status-label">
            当前状态
            {isLocal ? (
              <input
                className="archive-input"
                value={progressDraft.status}
                onChange={(e) => updateProgress('status', e.target.value)}
                placeholder="例如：大纲修订中"
              />
            ) : (
              <span className="archive-status">{progress.status || '规划中'}</span>
            )}
          </label>
        </section>
      </div>

      {isLocal && dirty && (
        <div className="archive-actions">
          <span>档案有新笔迹，尚未收存。</span>
          <button className="btn primary" onClick={save}>收存档案</button>
        </div>
      )}
    </div>
  )
}
