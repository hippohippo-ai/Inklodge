import { useCallback, useEffect, useState } from 'react'
import Library from './components/Library.jsx'
import Novel from './components/Novel.jsx'
import { loadLibrary, loadNovel } from './lib/novels.js'

export default function App() {
  const [library, setLibrary] = useState(null)
  const [current, setCurrent] = useState(null) // { id, title, cover }
  const [novel, setNovel] = useState(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    setLibrary(await loadLibrary())
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const openNovel = async (id) => {
    setLoading(true)
    try {
      const n = await loadNovel(id)
      setNovel(n)
      setCurrent({ id: n.id, title: n.title, cover: n.cover, source: n.source })
    } finally {
      setLoading(false)
    }
  }

  const closeNovel = () => {
    setNovel(null)
    setCurrent(null)
    refresh()
  }

  const updateNovel = (next) => {
    setNovel(next)
    if (next && next.source === 'local') {
      // 本地小说即时落盘；bundled 由仓库同步
    }
  }

  if (!library) {
    return <div className="app-loading">话本 · 加载中……</div>
  }

  if (current) {
    return (
      <Novel
        novel={novel}
        loading={loading}
        onBack={closeNovel}
        onUpdate={updateNovel}
      />
    )
  }

  return <Library library={library} onOpen={openNovel} onChanged={refresh} />
}
