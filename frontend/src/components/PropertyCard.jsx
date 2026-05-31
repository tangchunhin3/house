import { ExternalLink, Bed, Maximize, TrendingUp } from 'lucide-react'
import { Link } from 'react-router-dom'
import SourceBadge from './SourceBadge'

function formatPrice(n) {
  if (!n) return '-'
  if (n >= 10000) return `HK$ ${(n / 10000).toFixed(0)} 萬`
  return `HK$ ${n.toLocaleString()}`
}

export default function PropertyCard({ property }) {
  return (
    <div className="group relative flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm transition hover:shadow-md">
      <div className="aspect-[4/3] bg-gray-100 overflow-hidden">
        {property.image_url ? (
          <img
            src={property.image_url}
            alt={property.title}
            className="h-full w-full object-cover transition group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-gray-400 text-sm">暫無圖片</div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold leading-tight text-gray-900 line-clamp-2">
            {property.estate_name || property.title}
          </h3>
          <SourceBadge source={property.source} />
        </div>

        <p className="text-lg font-bold text-red-600">{formatPrice(property.price)}</p>

        <div className="flex items-center gap-3 text-xs text-gray-500">
          {property.bedrooms != null && (
            <span className="flex items-center gap-1">
              <Bed size={14} /> {property.bedrooms} 房
            </span>
          )}
          {property.area_sqft != null && (
            <span className="flex items-center gap-1">
              <Maximize size={14} /> {property.area_sqft.toLocaleString()} 呎
            </span>
          )}
          {property.floor && <span>{property.floor}</span>}
        </div>

        {property.address && (
          <p className="text-xs text-gray-400 truncate">{property.address}</p>
        )}

        <div className="mt-auto flex items-center justify-between">
          {property.estate_name && (
            <Link
              to={`/estate/${encodeURIComponent(property.estate_name)}`}
              className="inline-flex items-center gap-1 text-xs font-medium text-green-600 hover:text-green-800"
            >
              <TrendingUp size={12} />
              屋苑分析
            </Link>
          )}
          <a
            href={property.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800"
          >
            <ExternalLink size={12} />
            查看原文
          </a>
        </div>
      </div>
    </div>
  )
}
