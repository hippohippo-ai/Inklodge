#!/usr/bin/env node
// 比较提交前后的章节正文，只报告新增 R3/R4/R5 候选；命中、缺少工具或探针异常都不判失败。
// 用法：npm run check:style-signals -- --staged
//       npm run check:style-signals -- --base <before-sha> --head <after-sha> [--each-commit]
import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const argv = process.argv.slice(2)
const arg = (name) => {
  const i = argv.indexOf(name)
  return i >= 0 ? argv[i + 1] : null
}
const staged = argv.includes('--staged')
const eachCommit = argv.includes('--each-commit')
const base = arg('--base')
const head = arg('--head')
const EMPTY_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'

function git(args, options = {}) {
  return spawnSync('git', args, {
    cwd: ROOT,
    encoding: 'utf8',
    maxBuffer: 32 * 1024 * 1024,
    ...options,
  })
}

function reportUnavailable(message) {
  console.log(`[style-signals] ⚠ ${message}；跳过（只报告，不影响提交/CI）`)
}

function showRevision(rev, file, index = false) {
  const spec = index ? `:${file}` : `${rev}:${file}`
  const result = git(['show', spec], { encoding: null })
  return result.status === 0 ? result.stdout.toString('utf8') : ''
}

function getComparisons() {
  if (staged) return [{ label: 'staged', before: 'HEAD', after: 'INDEX', isIndex: true }]
  if (!base || !head) return null
  const normalizedBase = /^0+$/.test(base) ? EMPTY_TREE : base
  if (!eachCommit) return [{ label: `${normalizedBase.slice(0, 8)}..${head.slice(0, 8)}`, before: normalizedBase, after: head }]

  const range = normalizedBase === EMPTY_TREE ? head : `${normalizedBase}..${head}`
  const commits = git(['rev-list', '--first-parent', '--reverse', range])
  if (commits.status !== 0) return null
  return commits.stdout.split(/\r?\n/).filter(Boolean).map((commit) => {
    const parent = git(['rev-parse', `${commit}^`])
    return {
      label: commit.slice(0, 8),
      before: parent.status === 0 ? parent.stdout.trim() : EMPTY_TREE,
      after: commit,
    }
  })
}

function runComparison(comparison) {
  const diffArgs = comparison.isIndex
    ? ['-c', 'core.quotePath=false', 'diff', '--cached', '--name-only', '--diff-filter=ACMR']
    : ['-c', 'core.quotePath=false', 'diff', '--name-only', '--diff-filter=ACMR',
      comparison.before, comparison.after]
  diffArgs.push('--', 'books')
  const changed = git(diffArgs)
  if (changed.status !== 0) {
    reportUnavailable((changed.stderr || '无法读取变更文件').trim())
    return 0
  }

  const files = changed.stdout.split(/\r?\n/).filter((file) =>
    /^books\/[^/]+\/novel\/chapter-\d+\.md$/.test(file))
  if (!files.length) {
    console.log(`[style-signals] ${comparison.label}：未改动正文章节；新增 R3/R4/R5 候选：0`)
    return 0
  }

  const grouped = new Map()
  for (const file of files) {
    const book = file.split('/')[1]
    if (!grouped.has(book)) grouped.set(book, [])
    grouped.get(book).push({
      chapter: Number(file.match(/chapter-(\d+)\.md$/)[1]),
      before: showRevision(comparison.before, file),
      after: comparison.isIndex ? showRevision('', file, true) : showRevision(comparison.after, file),
    })
  }

  let total = 0
  const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3')
  for (const [book, chapters] of grouped) {
    const probe = path.join(ROOT, 'books', book, 'state', 'style-audit.py')
    if (!existsSync(probe)) {
      reportUnavailable(`${book} 没有 style-audit probe`)
      continue
    }
    const result = spawnSync(python, [probe, '--signal-delta-stdin'], {
      cwd: path.join(ROOT, 'books', book),
      encoding: 'utf8',
      input: JSON.stringify(chapters),
      maxBuffer: 32 * 1024 * 1024,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    })
    if (result.error || result.status !== 0) {
      reportUnavailable(`${book} 探针未能运行${result.stderr ? `：${result.stderr.trim()}` : ''}`)
      continue
    }
    let report
    try {
      report = JSON.parse(result.stdout)
    } catch {
      reportUnavailable(`${book} 探针输出无法解析`)
      continue
    }
    console.log(`[style-signals] ${comparison.label} · ${book}（${chapters.map((item) => `ch${item.chapter}`).join('、')}）`)
    if (!report.length) {
      console.log('  新增 R3/R4/R5 候选：0')
      continue
    }
    for (const item of report) {
      for (const signal of item.signals) {
        total += signal.count
        console.log(`  ch${item.chapter} ${signal.kind} ×${signal.count}：${signal.signal}`)
      }
    }
  }
  console.log(`[style-signals] ${comparison.label} 合计新增候选 ${total} 条。仅供人工复核，不判失败。`)
  return total
}

try {
  if ((!staged && (!base || !head)) || (staged && (base || head || eachCommit))) {
    reportUnavailable('需指定 --staged 或同时指定 --base 与 --head')
  } else {
    const comparisons = getComparisons()
    if (!comparisons) reportUnavailable('无法取得提交范围')
    else if (!comparisons.length) console.log('[style-signals] 提交范围内无提交或章节改动；新增候选：0')
    else for (const comparison of comparisons) runComparison(comparison)
  }
} catch (error) {
  reportUnavailable(error?.message || String(error))
}
