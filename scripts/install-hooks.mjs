#!/usr/bin/env node
// 安装/卸载 pre-commit 钩子（跨平台）。用法：
//   node scripts/install-hooks.mjs            安装（复制 scripts/pre-commit → .git/hooks/pre-commit）
//   node scripts/install-hooks.mjs --uninstall 卸载
// npm 别名：npm run hooks:install / npm run hooks:uninstall
import fs from 'node:fs'
import path from 'node:path'
import { execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const uninstall = process.argv.includes('--uninstall')

let gitDir
try {
  gitDir = execSync('git rev-parse --git-dir', { cwd: root, encoding: 'utf8' }).trim()
} catch {
  console.error('不是 Git 仓库（或未安装 git），无法安装钩子。')
  process.exit(1)
}
const hooksDir = path.resolve(root, gitDir, 'hooks')
const dst = path.join(hooksDir, 'pre-commit')
const src = path.join(root, 'scripts', 'pre-commit')

if (uninstall) {
  if (fs.existsSync(dst)) { fs.rmSync(dst); console.log(`已卸载：${dst}`) }
  else console.log('未安装，无需卸载。')
  process.exit(0)
}

if (!fs.existsSync(src)) {
  console.error(`缺少源文件：${src}`)
  process.exit(1)
}
fs.mkdirSync(hooksDir, { recursive: true })
if (fs.existsSync(dst)) console.log(`覆盖已有钩子：${dst}`)
fs.copyFileSync(src, dst)
try { fs.chmodSync(dst, 0o755) } catch { /* Windows 下无需可执行位 */ }
console.log(`已安装 pre-commit 钩子 → ${dst}`)
console.log('  跳过单次检查：git commit --no-verify')
console.log('  卸载：npm run hooks:uninstall')
