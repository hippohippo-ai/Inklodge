// 说书楼同步脚本：把根目录当前工作小说（state/ + novel/）同步到 public/novels/<书名>/
// 并在构建前重建顶层 manifest（public/novels/index.json）。
// 由 package.json 的 prebuild 调用：node scripts/sync.mjs
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const stateDir = path.join(root, 'state')
const novelDir = path.join(root, 'novel')
const publicNovels = path.join(root, 'public', 'novels')

function read(p) {
  try {
    return fs.readFileSync(p, 'utf8')
  } catch {
    return ''
  }
}

function readJson(p, fallback) {
  try {
    return JSON.parse(read(p))
  } catch {
    return fallback
  }
}

// 主题（theme.txt 第一行）
const themeRaw = read(path.join(stateDir, 'theme.txt')).trim()
const title = themeRaw.split('\n')[0].trim()
const archive = readJson(path.join(stateDir, 'archive.json'), {
  author: '待署名',
  epigraph: '',
  volumes: 1,
})

// 新书尚未定题时，只保留已有书库，不生成「待定」书目。
if (!title || title === '待定' || title === '（待定）') {
  console.log('说书楼 · 当前工作区尚未定题，保留已有书库')
  process.exit(0)
}

// 解析进度
const progressRaw = read(path.join(stateDir, 'progress.md'))
const num = (re) => {
  const m = re.exec(progressRaw)
  return m ? Number(m[1]) : 0
}
const progress = {
  stage: num(/当前阶段[：:]\s*(\d+)/),
  currentChapter: num(/当前章节[：:]\s*(\d+)/),
  totalChapters: num(/总章节数[：:]\s*(\d+)/),
  status: (/状态[：:]\s*([^\n]+)/.exec(progressRaw)?.[1]?.trim()) || '',
}

const dest = path.join(publicNovels, title)
fs.mkdirSync(path.join(dest, 'state'), { recursive: true })
fs.mkdirSync(path.join(dest, 'chapters'), { recursive: true })

const stateFiles = []
if (fs.existsSync(stateDir)) {
  for (const f of fs.readdirSync(stateDir).filter((f) => f.endsWith('.md')).sort()) {
    fs.copyFileSync(path.join(stateDir, f), path.join(dest, 'state', f))
    stateFiles.push(f.replace(/\.md$/, ''))
  }
}

const chapters = []
if (fs.existsSync(novelDir)) {
  for (const f of fs.readdirSync(novelDir).filter((f) => f.endsWith('.md')).sort()) {
    fs.copyFileSync(path.join(novelDir, f), path.join(dest, 'chapters', f))
    chapters.push(f.replace(/\.md$/, ''))
  }
}

// 每本小说的 index.json
fs.writeFileSync(
  path.join(dest, 'index.json'),
  JSON.stringify({ title, theme: title, cover: '#5b3a1e', archive, progress, stateFiles, chapters }, null, 2)
)

// 顶层 manifest：扫描所有小说
const novels = []
if (fs.existsSync(publicNovels)) {
  for (const d of fs.readdirSync(publicNovels)) {
    if (d === 'index.json') continue
    const p = path.join(publicNovels, d, 'index.json')
    if (!fs.existsSync(p)) continue
    let j
    try {
      j = JSON.parse(fs.readFileSync(p, 'utf8'))
    } catch {
      continue
    }
    novels.push({
      id: j.title,
      title: j.title,
      theme: j.theme || '',
      cover: j.cover || '#5b3a1e',
      progress: j.progress || {},
      chapterCount: (j.chapters || []).length,
    })
  }
}
fs.writeFileSync(path.join(publicNovels, 'index.json'), JSON.stringify(novels, null, 2))
console.log(`说书楼 · 已同步《${title}》→ public/novels/，书库共 ${novels.length} 本`)
