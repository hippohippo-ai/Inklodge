// 墨庐同步脚本：扫描 books/<项目>/，同步每本小说到 public/novels/<书名>/。
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const projectsDir = path.join(root, 'books')
const publicNovels = path.join(root, 'public', 'novels')

function read(p) {
  try { return fs.readFileSync(p, 'utf8') } catch { return '' }
}
function readJson(p, fallback) {
  try { return JSON.parse(read(p)) } catch { return fallback }
}
function number(re, text) {
  const match = re.exec(text)
  return match ? Number(match[1]) : 0
}
function projectTitle(projectDir, stateDir) {
  const theme = read(path.join(stateDir, 'theme.txt')).trim()
  return theme.split('\n')[0].trim() || path.basename(projectDir)
}
function syncProject(projectDir) {
  const stateDir = path.join(projectDir, 'state')
  const novelDir = path.join(projectDir, 'novel')
  if (!fs.existsSync(stateDir) || !fs.existsSync(novelDir)) return null

  const title = projectTitle(projectDir, stateDir)
  if (!title || title === '待定' || title === '（待定）') return null
  const archive = readJson(path.join(stateDir, 'archive.json'), { author: '咸鱼散翁', epigraph: '', volumes: 1 })
  const progressRaw = read(path.join(stateDir, 'progress.md'))
  const progress = {
    stage: number(/当前阶段[：:]\s*(\d+)/, progressRaw),
    currentChapter: number(/当前章节[：:]\s*(\d+)/, progressRaw),
    totalChapters: number(/总章节数[：:]\s*(\d+)/, progressRaw),
    status: (/状态[：:]\s*([^\n]+)/.exec(progressRaw)?.[1]?.trim()) || '',
  }
  const dest = path.join(publicNovels, title)
  fs.rmSync(dest, { recursive: true, force: true })
  fs.mkdirSync(path.join(dest, 'state'), { recursive: true })
  fs.mkdirSync(path.join(dest, 'chapters'), { recursive: true })

  const stateFiles = []
  for (const file of fs.readdirSync(stateDir).filter((f) => f.endsWith('.md')).sort()) {
    fs.copyFileSync(path.join(stateDir, file), path.join(dest, 'state', file))
    stateFiles.push(file.replace(/\.md$/, ''))
  }
  const chapters = []
  const publishable = (f) => /^chapter-\d+\.md$/.test(f) || f === 'copyright.md' || f === 'preface.md'
  for (const file of fs.readdirSync(novelDir).filter(publishable).sort()) {
    fs.copyFileSync(path.join(novelDir, file), path.join(dest, 'chapters', file))
    chapters.push(file.replace(/\.md$/, ''))
  }
  fs.writeFileSync(path.join(dest, 'index.json'), JSON.stringify({ title, theme: title, cover: '#5b3a1e', archive, progress, stateFiles, chapters }, null, 2))
  return { id: title, title, theme: title, cover: '#5b3a1e', archive, progress, chapterCount: chapters.length }
}

fs.mkdirSync(publicNovels, { recursive: true })
const novels = []
if (fs.existsSync(projectsDir)) {
  for (const name of fs.readdirSync(projectsDir).sort()) {
    const result = syncProject(path.join(projectsDir, name))
    if (result) novels.push(result)
  }
}
fs.writeFileSync(path.join(publicNovels, 'index.json'), JSON.stringify(novels, null, 2))
console.log(`墨庐 · 已同步 ${novels.length} 个小说项目 → public/novels/`)
