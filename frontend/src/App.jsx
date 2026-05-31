import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { getProperties, getTransactions, getStats, triggerScrape, triggerSearch, getCurrentSession } from './api'
import Header from './components/Header'
import FilterBar from './components/FilterBar'
import PropertyGrid from './components/PropertyGrid'

const TABS = [
  { key: 'listings', label: '放盤', endpoint: getProperties },
  { key: 'transactions', label: '成交紀錄', endpoint: getTransactions },
]

export default function App() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState('listings')
  const [filters, setFilters] = useState({ sort_by: 'newest', page: 1 })
  const [searchInput, setSearchInput] = useState('')

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    refetchInterval: 30_000,
  })

  const fetchFn = TABS.find(t => t.key === tab)?.endpoint || getProperties
  const { data, isFetching } = useQuery({
    queryKey: ['properties', tab, filters],
    queryFn: () => fetchFn(filters),
    placeholderData: keepPreviousData,
  })

  const scrapeMutation = useMutation({
    mutationFn: triggerScrape,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['currentSession'] })
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['properties'] })
        queryClient.invalidateQueries({ queryKey: ['stats'] })
      }, 5000)
    },
  })

  const searchMutation = useMutation({
    mutationFn: triggerSearch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['currentSession'] })
    },
  })

  const { data: currentSession, isFetched: sessionFetched } = useQuery({
    queryKey: ['currentSession'],
    queryFn: getCurrentSession,
    refetchInterval: (q) => scrapeMutation.isPending || searchMutation.isPending || q.state.data?.status === 'running' ? 3000 : false,
  })

  const handleScrape = useCallback(() => {
    scrapeMutation.mutate()
  }, [scrapeMutation])

  const handleSearch = useCallback(() => {
    const kw = searchInput.trim()
    if (!kw) return
    searchMutation.mutate(kw)
    setFilters((f) => ({ ...f, estate_name: '', page: 1 }))
  }, [searchInput, searchMutation])

  const handleTabChange = useCallback((newTab) => {
    setTab(newTab)
    setFilters((f) => ({ ...f, page: 1 }))
  }, [])

  useEffect(() => {
    if (currentSession?.status === 'running' || currentSession?.status === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['properties'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    }
  }, [JSON.stringify(currentSession?.scraper_results), currentSession?.status, queryClient])

  const isScraping = scrapeMutation.isPending || (sessionFetched && currentSession?.status === 'running')

  return (
    <div className="min-h-screen bg-gray-50">
      <Header
        totalProperties={stats?.total_properties}
      />

      <main className="mx-auto max-w-7xl px-4 py-6">
        {/* Search bar */}
        <div className="mb-4 flex items-center gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="搜尋屋苑名稱 (例如 柏瓏、黃金海灣...)"
              className="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-4 pr-10 text-sm shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
            <svg className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <button
            onClick={handleSearch}
            disabled={searchMutation.isPending || !searchInput.trim()}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-50"
          >
            {searchMutation.isPending ? (
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            )}
            {searchMutation.isPending ? '搜尋中...' : '搜尋'}
          </button>
        </div>

        {/* Tab bar */}
        <div className="mb-4 flex gap-1 rounded-lg border border-gray-200 bg-white p-1 shadow-sm">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => handleTabChange(t.key)}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
                tab === t.key
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              {t.label}
              {tab === t.key && isFetching && (
                <span className="ml-2 inline-block h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
              )}
            </button>
          ))}
        </div>

        <div className="mb-6">
          <FilterBar
            filters={filters}
            onChange={(f) => setFilters({ ...f, page: 1 })}
            onScrape={handleScrape}
            scraping={isScraping}
          />
        </div>

        {isScraping && (
          <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
            <div className="mb-2 text-sm font-medium text-amber-800">爬取進度</div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5">
              {currentSession?.scraper_results ? (
                Object.entries(currentSession.scraper_results).map(([name, r]) => (
                  <div key={name} className="rounded-lg bg-white px-3 py-2 text-xs shadow-sm">
                    <div className="font-medium text-gray-700">{name}</div>
                    <div className="mt-0.5 text-gray-500">
                      {r.done ? (
                        <>找到 {r.found} 個{r.error && <span className="ml-1 text-red-500">錯誤</span>}</>
                      ) : (
                        <span className="text-amber-600">進行中...</span>
                      )}
                    </div>
                    {r.error && <div className="mt-0.5 text-red-400 truncate" title={r.error}>{r.error}</div>}
                  </div>
                ))
              ) : (
                <div className="col-span-full text-xs text-gray-400">等待爬蟲啟動...</div>
              )}
            </div>
          </div>
        )}

        <PropertyGrid
          properties={data?.items || []}
          loading={!data && isFetching}
        />

        {data && data.total > data.page_size && (
          <div className="mt-6 flex items-center justify-center gap-2">
            <button
              onClick={() => setFilters((f) => ({ ...f, page: Math.max(1, f.page - 1) }))}
              disabled={filters.page <= 1}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-40"
            >
              上一頁
            </button>
            <span className="text-sm text-gray-500">
              {filters.page} / {Math.ceil(data.total / data.page_size)}
            </span>
            <button
              onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
              disabled={filters.page >= Math.ceil(data.total / data.page_size)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-40"
            >
              下一頁
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
