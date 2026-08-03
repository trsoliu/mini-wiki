import { readdir, readFile, stat } from 'node:fs/promises'
import path from 'node:path'

const outputRoot = path.resolve(process.cwd(), 'site/.silen/dist')

const htmlRoutes = [
  'index.html',
  'guide/index.html',
  'knowledge-network/index.html',
  'features/index.html',
  'security/index.html',
  'reference/index.html',
  'en/index.html',
  'en/guide/index.html',
  'en/knowledge-network/index.html',
  'en/features/index.html',
  'en/security/index.html',
  'en/reference/index.html',
]

const markdownRoutes = htmlRoutes.map((route) => route.replace(/\.html$/u, '.md'))
const requiredArtifacts = [
  ...htmlRoutes,
  ...markdownRoutes,
  '404.html',
  'en/404.html',
  'llms.txt',
  'llms-full.txt',
  'ai-index.json',
  'search-index.json',
  'sitemap.xml',
  'robots.txt',
  '.well-known/silen/manifest.json',
  '.well-known/silen/api.json',
  '.well-known/silen/guide.md',
]

const blockedText = [
  'sourceMappingURL',
  'docs/wechat-publish-notes.md',
  'tmp/',
  '/Users/',
  'file://',
]

const textExtensions = new Set([
  '.css',
  '.html',
  '.js',
  '.json',
  '.md',
  '.svg',
  '.txt',
  '.xml',
])

async function isFile(relativePath) {
  try {
    return (await stat(path.join(outputRoot, relativePath))).isFile()
  } catch {
    return false
  }
}

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const absolutePath = path.join(directory, entry.name)
    if (entry.isDirectory()) {
      files.push(...(await collectFiles(absolutePath)))
    } else if (entry.isFile()) {
      files.push(absolutePath)
    }
  }
  return files
}

const missing = []
for (const relativePath of requiredArtifacts) {
  if (!(await isFile(relativePath))) missing.push(relativePath)
}

if (missing.length > 0) {
  throw new Error(`Silen artifact contract is missing:\n${missing.map((file) => `- ${file}`).join('\n')}`)
}

const files = await collectFiles(outputRoot)
const leaks = []
for (const absolutePath of files) {
  const relativePath = path.relative(outputRoot, absolutePath).split(path.sep).join('/')
  if (relativePath.endsWith('.map')) {
    leaks.push(`${relativePath}: source map file`)
    continue
  }
  if (!textExtensions.has(path.extname(relativePath))) continue

  const content = await readFile(absolutePath, 'utf8')
  for (const blocked of blockedText) {
    if (content.includes(blocked)) leaks.push(`${relativePath}: contains ${JSON.stringify(blocked)}`)
  }
}

if (leaks.length > 0) {
  throw new Error(`Silen artifact contract rejected deployable content:\n${leaks.map((leak) => `- ${leak}`).join('\n')}`)
}

console.log(`Silen artifact contract passed: ${requiredArtifacts.length} required artifacts, ${files.length} files scanned.`)
