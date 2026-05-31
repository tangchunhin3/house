import { useState, useEffect } from 'react'
import { RefreshCw } from 'lucide-react'
import { getEstates } from '../api'

const SOURCES = ['中原', '利嘉閣', '美聯', '28Hse', 'House730', '世紀21']

export default function FilterBar({ filters, onChange, onScrape, scraping }) {
  const set = (key, val) => onChange({ ...filters, [key]: val })
  const [estates, setEstates] = useState([])
  const [estateSearch, setEstateSearch] = useState('')

  useEffect(() => {
    setEstateSearch(filters.estate_name || '')
  }, [filters.estate_name])

  useEffect(() => {
    getEstates().then(setEstates).catch(() => {})
  }, [])

  const filteredEstates = estates.filter(
    (e) => !estateSearch || e.name.includes(estateSearch)
  )

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      {/* Estate name — text input + dropdown list */}
      <div className="relative flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">屋苑</label>
        <div className="relative">
          <input
            type="text"
            placeholder="輸入篩選…"
            value={estateSearch}
            onChange={(e) => {
              setEstateSearch(e.target.value)
              if (!e.target.value) set('estate_name', undefined)
            }}
            className="w-40 rounded border border-gray-300 px-2 py-1 pr-6 text-xs"
          />
          {(filters.estate_name || estateSearch) && (
            <button
              onClick={() => { setEstateSearch(''); set('estate_name', undefined) }}
              className="absolute right-1 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
            >
              ✕
            </button>
          )}
          <div className="absolute top-full left-0 z-10 mt-0.5 max-h-48 w-56 overflow-y-auto rounded border border-gray-200 bg-white shadow-lg">
            {filteredEstates.length > 0 && (
              <button
                onMouseDown={() => { setEstateSearch(''); set('estate_name', undefined) }}
                className={`flex w-full items-center px-3 py-1.5 text-left text-xs hover:bg-blue-50 ${!filters.estate_name ? 'bg-blue-50 font-medium' : ''}`}
              >
                <span className="text-gray-500">全部屋苑</span>
              </button>
            )}
            {filteredEstates.map((s) => (
              <button
                key={s.name}
                onMouseDown={() => { setEstateSearch(s.name); set('estate_name', s.name) }}
                className={`flex w-full items-center justify-between px-3 py-1.5 text-left text-xs hover:bg-blue-50 ${filters.estate_name === s.name ? 'bg-blue-50 font-medium' : ''}`}
              >
                <span>{s.name}</span>
                <span className="text-gray-400">{s.count}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Source filter */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">來源</label>
        <div className="flex flex-wrap gap-1.5">
          {SOURCES.map((s) => (
            <button
              key={s}
              onClick={() => {
                const cur = filters.source ? filters.source.split(',') : []
                const next = cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]
                set('source', next.join(',') || undefined)
              }}
              className={`rounded-full px-2.5 py-1 text-xs font-medium transition ${
                (filters.source || '').split(',').includes(s)
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Price range */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">價格範圍 (HKD)</label>
        <div className="flex items-center gap-1">
          <input
            type="number"
            placeholder="最低"
            value={filters.min_price || ''}
            onChange={(e) => set('min_price', e.target.value || undefined)}
            className="w-24 rounded border border-gray-300 px-2 py-1 text-xs"
          />
          <span className="text-gray-400">-</span>
          <input
            type="number"
            placeholder="最高"
            value={filters.max_price || ''}
            onChange={(e) => set('max_price', e.target.value || undefined)}
            className="w-24 rounded border border-gray-300 px-2 py-1 text-xs"
          />
        </div>
      </div>

      {/* Bedrooms */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">最少房間</label>
        <select
          value={filters.min_bedrooms || ''}
          onChange={(e) => set('min_bedrooms', e.target.value || undefined)}
          className="rounded border border-gray-300 px-2 py-1 text-xs"
        >
          <option value="">不限</option>
          {[0, 1, 2, 3, 4, 5].map((n) => (
            <option key={n} value={n}>{n === 0 ? '開放式' : `${n} 房`}</option>
          ))}
        </select>
      </div>

      {/* Sort */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">排序</label>
        <select
          value={filters.sort_by || 'newest'}
          onChange={(e) => set('sort_by', e.target.value)}
          className="rounded border border-gray-300 px-2 py-1 text-xs"
        >
          <option value="newest">最新</option>
          <option value="price_asc">價格 低→高</option>
          <option value="price_desc">價格 高→低</option>
          <option value="area_asc">實用面積 小→大</option>
          <option value="area_desc">實用面積 大→小</option>
        </select>
      </div>

      {/* Scrape button */}
      <button
        onClick={onScrape}
        disabled={scraping}
        className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
      >
        <RefreshCw size={14} className={scraping ? 'animate-spin' : ''} />
        {scraping ? '爬取中...' : '重新爬取'}
      </button>
    </div>
  )
}
