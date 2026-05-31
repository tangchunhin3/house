import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, TrendingUp, Home, DollarSign, BarChart3 } from 'lucide-react'
import { getEstateAnalysis } from '../api'

function formatPrice(n) {
  if (!n) return '-'
  if (n >= 10000) return `HK$ ${(n / 10000).toFixed(0)} 萬`
  return `HK$ ${n.toLocaleString()}`
}

export default function EstateAnalysis() {
  const { name } = useParams()
  const decoded = decodeURIComponent(name)

  const { data, isLoading, error } = useQuery({
    queryKey: ['estate-analysis', decoded],
    queryFn: () => getEstateAnalysis(decoded),
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="mx-auto max-w-4xl animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3" />
          <div className="h-4 bg-gray-200 rounded w-1/4" />
          <div className="h-64 bg-gray-200 rounded" />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="mx-auto max-w-4xl">
          <Link to="/" className="mb-4 inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
            <ArrowLeft size={16} /> 返回列表
          </Link>
          <p className="mt-8 text-center text-gray-400">無法載入 {decoded} 的分析資料</p>
        </div>
      </div>
    )
  }

  const distBins = []
  const binSize = Math.max(1, Math.floor((data.max_呎價 - data.min_呎價) / 10))
  for (let i = 0; i < 10; i++) {
    const low = data.min_呎價 + i * binSize
    const high = low + binSize
    const count = data.listings.filter(l => l.呎價 >= low && (i === 9 ? l.呎價 <= high : l.呎價 < high)).length
    distBins.push({ low, high, count, pct: data.total_listings > 0 ? (count / data.total_listings * 100) : 0 })
  }
  const maxCount = Math.max(...distBins.map(b => b.count), 1)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-5xl px-4 py-6">
        <Link to="/" className="mb-4 inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
          <ArrowLeft size={16} /> 返回列表
        </Link>

        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">{data.estate_name}</h1>
          <p className="text-sm text-gray-500">
            {data.total_listings} 個放盤 · 來自 {Object.keys(data.sources).length} 間代理
          </p>
        </div>

        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: '平均呎價', value: `HK$${(data.avg_呎價 || 0).toLocaleString()}`, icon: TrendingUp, color: 'text-blue-600' },
            { label: '預期呎價範圍', value: `$${(data.expected_呎價_range?.low || 0).toLocaleString()} - $${(data.expected_呎價_range?.high || 0).toLocaleString()}`, icon: BarChart3, color: 'text-green-600' },
            { label: '平均總價', value: formatPrice(data.avg_price), icon: DollarSign, color: 'text-red-600' },
            { label: '價格範圍', value: `${formatPrice(data.min_price)} - ${formatPrice(data.max_price)}`, icon: Home, color: 'text-purple-600' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
              <div className="mb-1 flex items-center gap-1.5 text-xs text-gray-500">
                <Icon size={14} className={color} />
                {label}
              </div>
              <p className="text-sm font-semibold text-gray-900">{value}</p>
            </div>
          ))}
        </div>

        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">呎價分佈</h2>
          <div className="flex items-end gap-1">
            {distBins.map((bin, i) => (
              <div key={i} className="group relative flex flex-1 flex-col items-center" title={`$${bin.low.toLocaleString()} - $${bin.high.toLocaleString()}: ${bin.count} 個`}>
                <div
                  className="w-full rounded-t bg-blue-500 transition hover:bg-blue-600"
                  style={{ height: `${(bin.count / maxCount) * 120}px`, minHeight: bin.count > 0 ? '4px' : '0' }}
                />
                <span className="mt-1 text-[10px] text-gray-400">{bin.count}</span>
              </div>
            ))}
          </div>
          <div className="mt-1 flex justify-between text-[10px] text-gray-400">
            <span>${(data.min_呎價 || 0).toLocaleString()}</span>
            <span>${(data.max_呎價 || 0).toLocaleString()}</span>
          </div>
        </div>

        <div className="mb-6 rounded-lg border border-gray-200 bg-white shadow-sm">
          <h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold text-gray-900">放盤列表 (按呎價排序)</h2>
          <div className="divide-y divide-gray-100">
            {data.listings.map((l) => (
              <a
                key={l.id}
                href={l.source_url || '#'}
                target={l.source_url ? '_blank' : undefined}
                rel="noopener noreferrer"
                className="flex items-center justify-between px-4 py-2.5 text-sm transition hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  <span className="font-medium text-gray-900">${(l.呎價 || 0).toLocaleString()}/呎</span>
                  <span className="text-gray-500">{formatPrice(l.price)}</span>
                  {l.bedrooms != null && <span className="text-gray-400">{l.bedrooms}房</span>}
                  {l.floor && <span className="text-gray-400">{l.floor}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500">{l.source}</span>
                  {l.area_sqft && <span className="text-gray-400">{l.area_sqft.toLocaleString()}呎</span>}
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
