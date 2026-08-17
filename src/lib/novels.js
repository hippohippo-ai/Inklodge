// 话本数据层
// 两类小说：
//  - bundled（仓库内置）：位于 public/novels/<书名>/，由 AI 生成器直接写 markdown，脚本同步。只读。
//  - local（浏览器本地）：存于 localStorage，可自由编辑、导入导出。

export const STATE_FILES = [
  { name: 'requirements', title: '要求' },
  { name: 'theme', title: '主题' },
  { name: 'outline', title: '大纲' },
  { name: 'characters', title: '人物' },
  { name: 'conflicts', title: '矛盾' },
  { name: 'chapters', title: '章节规划' },
  { name: 'foreshadowing', title: '伏笔' },
  { name: 'timeline', title: '时间线' },
  { name: 'knowledge', title: '知识矩阵' },
  { name: 'plot-check', title: '漏洞检查' },
  { name: 'chapter-log', title: '章节总结' },
  { name: 'revisions', title: '修订记录' },
  { name: 'final-check', title: '精校报告' },
]

const LOCAL_KEY = 'huaben.local.novels' // { id: novel }
const PROGRESS_KEY = 'huaben.reading' // { novelId: lastChapterIndex }

function localStore() {
  try {
    return JSON.parse(localStorage.getItem(LOCAL_KEY) || '{}')
  } catch {
    return {}
  }
}

function writeLocalStore(map) {
  localStorage.setItem(LOCAL_KEY, JSON.stringify(map))
}

function readingStore() {
  try {
    return JSON.parse(localStorage.getItem(PROGRESS_KEY) || '{}')
  } catch {
    return {}
  }
}

function titleToId(title) {
  return title.trim().replace(/\s+/g, '-')
}

// ---------- 读取 ----------

// 书库：bundled + local 合并
export async function loadLibrary() {
  const bundled = await fetchBundledIndex()
  const localMap = localStore()
  const local = Object.values(localMap).map((n) => ({
    id: n.id,
    title: n.title,
    theme: n.theme || '',
    cover: n.cover || '#5b3a1e',
    source: 'local',
    progress: n.progress || { stage: 0, currentChapter: 0, totalChapters: 0, status: '本地草稿' },
    chapterCount: (n.chapters || []).length,
  }))
  return [...bundled, ...local]
}

async function fetchBundledIndex() {
  try {
    const res = await fetch('novels/index.json', { cache: 'no-store' })
    if (!res.ok) return []
    const list = await res.json()
    return (list || []).map((n) => ({
      id: n.id,
      title: n.title,
      theme: n.theme || '',
      cover: n.cover || '#5b3a1e',
      source: 'bundled',
      progress: n.progress || { stage: 0, currentChapter: 0, totalChapters: 0, status: '规划中' },
      chapterCount: n.chapterCount || 0,
    }))
  } catch {
    return []
  }
}

// 加载整本小说（bundled 或 local）
export async function loadNovel(id) {
  const localMap = localStore()
  if (localMap[id]) return { ...localMap[id], source: 'local' }
  return loadBundledNovel(id)
}

async function loadBundledNovel(id) {
  const base = `novels/${encodeURIComponent(id)}`
  const idx = await fetchJson(`${base}/index.json`)
  const stateFiles = {}
  const names = (idx && idx.stateFiles) || STATE_FILES.map((f) => f.name)
  await Promise.all(
    names.map(async (name) => {
      stateFiles[name] = await fetchText(`${base}/state/${name}.md`, '')
    })
  )
  const chapters = []
  const chapterNames = (idx && idx.chapters) || []
  await Promise.all(
    chapterNames.map(async (c) => {
      const content = await fetchText(`${base}/chapters/${c}.md`, '')
      chapters.push({ id: c, title: c, content })
    })
  )
  return {
    id,
    title: (idx && idx.title) || id,
    theme: (idx && idx.theme) || '',
    cover: (idx && idx.cover) || '#5b3a1e',
    source: 'bundled',
    progress: (idx && idx.progress) || { stage: 0, currentChapter: 0, totalChapters: 0, status: '规划中' },
    stateFiles,
    chapters,
  }
}

// ---------- 本地小说 ----------

export function createLocalNovel({ title, theme = '' }) {
  const id = titleToId(title)
  const emptyState = {}
  for (const f of STATE_FILES) emptyState[f.name] = `# ${f.title}\n\n（空）\n`
  const novel = {
    id,
    title,
    theme: theme || title,
    cover: pickCover(title),
    source: 'local',
    progress: { stage: 0, currentChapter: 0, totalChapters: 0, status: '本地草稿' },
    stateFiles: emptyState,
    chapters: [],
  }
  const map = localStore()
  map[id] = novel
  writeLocalStore(map)
  return novel
}

export function saveLocalNovel(novel) {
  const map = localStore()
  map[novel.id] = novel
  writeLocalStore(map)
}

export function deleteLocalNovel(id) {
  const map = localStore()
  delete map[id]
  writeLocalStore(map)
}

export function exportLocalNovels() {
  const map = localStore()
  const blob = new Blob([JSON.stringify(Object.values(map), null, 2)], {
    type: 'application/json',
  })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'huaben-novels.json'
  a.click()
  URL.revokeObjectURL(a.href)
}

export function importLocalNovels(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result)
        const arr = Array.isArray(data) ? data : [data]
        const map = localStore()
        for (const n of arr) {
          if (n && n.title) {
            n.id = n.id || titleToId(n.title)
            n.source = 'local'
            map[n.id] = n
          }
        }
        writeLocalStore(map)
        resolve(arr.length)
      } catch (e) {
        reject(e)
      }
    }
    reader.readAsText(file)
  })
}

// ---------- 阅读进度 ----------

export function getReadingPos(id) {
  return readingStore()[id] ?? 0
}

export function setReadingPos(id, index) {
  const s = readingStore()
  s[id] = index
  localStorage.setItem(PROGRESS_KEY, JSON.stringify(s))
}

// ---------- 工具 ----------

function pickCover(title) {
  const palette = ['#5b3a1e', '#7a3b2e', '#3b4a6b', '#4a6b3b', '#6b3b5a', '#2e5b6b', '#6b552e', '#3b3b6b']
  let h = 0
  for (const ch of title) h = (h * 31 + ch.codePointAt(0)) % 997
  return palette[h % palette.length]
}

async function fetchJson(url) {
  try {
    const res = await fetch(url, { cache: 'no-store' })
    return res.ok ? res.json() : null
  } catch {
    return null
  }
}

async function fetchText(url, fallback) {
  try {
    const res = await fetch(url, { cache: 'no-store' })
    return res.ok ? res.text() : fallback
  } catch {
    return fallback
  }
}
