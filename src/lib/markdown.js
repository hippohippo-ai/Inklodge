import { marked } from 'marked'

marked.setOptions({
  gfm: true,
  breaks: true,
})

export function renderMarkdown(text) {
  try {
    return marked.parse(text || '')
  } catch {
    return text || ''
  }
}
