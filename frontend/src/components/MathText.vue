<script setup lang="ts">
import { computed } from 'vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const props = defineProps<{ text: string | null | undefined }>()

interface Segment {
  type: 'text' | 'math'
  value: string
}

// 将一段文本按 $...$ 拆分为普通文本段与LaTeX公式段
function parseInline(raw: string): Segment[] {
  const segments: Segment[] = []
  const regex = /\$([^$]+?)\$/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = regex.exec(raw)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', value: raw.slice(lastIndex, match.index) })
    }
    segments.push({ type: 'math', value: match[1] })
    lastIndex = regex.lastIndex
  }
  if (lastIndex < raw.length) {
    segments.push({ type: 'text', value: raw.slice(lastIndex) })
  }
  return segments
}

function renderMath(expr: string): string {
  try {
    return katex.renderToString(expr, { throwOnError: false, displayMode: false })
  } catch {
    return expr
  }
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

// 渲染含内联公式的文本(不含换行处理)
function renderInline(raw: string): string {
  return parseInline(raw)
    .map((seg) =>
      seg.type === 'math' ? renderMath(seg.value) : escapeHtml(seg.value),
    )
    .join('')
}

// 判断是否为Markdown表格行
function isTableRow(line: string): boolean {
  return /^\s*\|.*\|\s*$/.test(line)
}

// 判断是否为表格分隔行 | --- | --- |
function isTableSeparator(line: string): boolean {
  return /^\s*\|?[\s:|-]+\|?\s*$/.test(line) && line.includes('-')
}

function splitRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\||\|$/g, '')
    .split('|')
    .map((c) => c.trim())
}

// 渲染Markdown表格为HTML
function renderTable(rows: string[]): string {
  if (rows.length < 2) return rows.map((r) => renderInline(r)).join('<br>')
  const header = splitRow(rows[0])
  const bodyRows = rows.slice(2) // 跳过表头与分隔行
  const thead =
    '<thead><tr>' +
    header.map((c) => `<th>${renderInline(c)}</th>`).join('') +
    '</tr></thead>'
  const tbody =
    '<tbody>' +
    bodyRows
      .map(
        (r) =>
          '<tr>' +
          splitRow(r)
            .map((c) => `<td>${renderInline(c)}</td>`)
            .join('') +
          '</tr>',
      )
      .join('') +
    '</tbody>'
  return `<table class="md-table">${thead}${tbody}</table>`
}

// 主渲染：按行扫描，聚合表格块，其余按内联文本+换行渲染
const html = computed(() => {
  const raw = props.text ?? ''
  const lines = raw.split('\n')
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    // 检测表格块：当前行是表格行且下一行是分隔行
    if (isTableRow(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const block: string[] = [line, lines[i + 1]]
      i += 2
      while (i < lines.length && isTableRow(lines[i])) {
        block.push(lines[i])
        i += 1
      }
      out.push(renderTable(block))
    } else {
      out.push(renderInline(line))
      i += 1
    }
  }
  return out.join('<br>')
})
</script>

<template>
  <span class="math-text" v-html="html" />
</template>

<style scoped>
.math-text {
  white-space: normal;
}
.math-text :deep(.md-table) {
  border-collapse: collapse;
  margin: 8px 0;
}
.math-text :deep(.md-table th),
.math-text :deep(.md-table td) {
  border: 1px solid #303133;
  padding: 4px 12px;
  text-align: center;
}
.math-text :deep(.md-table th) {
  background: #f5f7fa;
  font-weight: 600;
}
</style>
