import type { ReactNode } from 'react'
import DefaultTheme, { defineTheme } from '@aicode-nexus/silen/theme'

import './custom.css'

function Note({ children }: { readonly children?: ReactNode }) {
  return <aside className="product-note">{children}</aside>
}

export default defineTheme({
  extends: DefaultTheme,
  components: { Note },
  wrapRoot({ children }) {
    return <div data-product-docs="mini-wiki">{children}</div>
  },
})
