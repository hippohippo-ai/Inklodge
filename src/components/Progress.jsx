const STAGES = [
  { n: 0, name: '主题确认', file: 'theme' },
  { n: 1, name: '大纲', file: 'outline' },
  { n: 2, name: '人物', file: 'characters' },
  { n: 3, name: '矛盾关系', file: 'conflicts' },
  { n: 4, name: '章节规划', file: 'chapters' },
  { n: 5, name: '伏笔暗线', file: 'foreshadowing' },
  { n: 6, name: '时间线', file: 'timeline' },
  { n: 7, name: '知识矩阵', file: 'knowledge' },
  { n: 8, name: '漏洞检查', file: 'plot-check' },
  { n: 9, name: '写章节', file: null },
  { n: 10, name: '章节总结', file: 'chapter-log' },
  { n: 11, name: '循环写作', file: null },
  { n: 12, name: '润色衔接', file: null },
  { n: 13, name: '精校交付', file: 'final-check' },
]

export default function Progress({ novel }) {
  const p = novel.progress || {}
  const stage = Number.isFinite(p.stage) ? p.stage : 0
  const total = p.totalChapters || 0
  const current = p.currentChapter || 0
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0
  const files = novel.stateFiles || {}
  const chapters = novel.chapters || []

  return (
    <div className="progress">
      <section className="progress-card">
        <h3>写作进度</h3>
        <div className="progress-big">
          <span className="progress-num">{current}</span>
          <span className="progress-total">/ {total} 章</span>
        </div>
        <div className="progress-track big">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <p className="progress-status">状态：{p.status || '—'}</p>
      </section>

      <section className="progress-card">
        <h3>生成器阶段</h3>
        <ol className="stage-list">
          {STAGES.map((s) => {
            const done = s.n < stage
            const active = s.n === stage
            const hasFile = s.file && files[s.file] && files[s.file].trim().length > 2
            return (
              <li
                key={s.n}
                className={`stage-item ${active ? 'active' : ''} ${done ? 'done' : ''}`}
              >
                <span className="stage-dot">{done ? '✓' : s.n}</span>
                <span className="stage-name">{s.name}</span>
                {hasFile && <span className="pill">已写</span>}
              </li>
            )
          })}
        </ol>
      </section>

      <section className="progress-card">
        <h3>章节</h3>
        {chapters.length === 0 ? (
          <p className="empty-hint">尚未开始写正文。</p>
        ) : (
          <ul className="chapter-status-list">
            {chapters.map((c, i) => (
              <li key={c.id}>
                <span className="toc-no">{i + 1}</span>
                <span>{c.title}</span>
                <span className="pill">{c.content.trim() ? '已写' : '空'}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
