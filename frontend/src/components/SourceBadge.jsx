const SOURCE_COLORS = {
  '中原': { bg: 'bg-red-100', text: 'text-red-700', ring: 'ring-red-600/20' },
  '利嘉閣': { bg: 'bg-blue-100', text: 'text-blue-700', ring: 'ring-blue-600/20' },
  '美聯': { bg: 'bg-green-100', text: 'text-green-700', ring: 'ring-green-600/20' },
  '28Hse': { bg: 'bg-purple-100', text: 'text-purple-700', ring: 'ring-purple-600/20' },
  'House730': { bg: 'bg-orange-100', text: 'text-orange-700', ring: 'ring-orange-600/20' },
  '世紀21': { bg: 'bg-teal-100', text: 'text-teal-700', ring: 'ring-teal-600/20' },
}

export default function SourceBadge({ source }) {
  const colors = SOURCE_COLORS[source] || { bg: 'bg-gray-100', text: 'text-gray-700', ring: 'ring-gray-500/20' }
  return (
    <span className={`inline-flex items-center rounded-full ${colors.bg} px-2 py-0.5 text-xs font-medium ${colors.text} ring-1 ring-inset ${colors.ring}`}>
      {source}
    </span>
  )
}
