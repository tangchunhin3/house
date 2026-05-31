import { Building2, Database } from 'lucide-react'

export default function Header({ totalProperties, sessionInfo }) {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2">
          <Building2 className="h-6 w-6 text-blue-600" />
          <h1 className="text-lg font-bold text-gray-900">屯門樓盤搜尋</h1>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          {totalProperties != null && (
            <span className="flex items-center gap-1">
              <Database size={14} />
              共 {totalProperties} 筆
            </span>
          )}
          {sessionInfo && <span>上次更新: {sessionInfo}</span>}
        </div>
      </div>
    </header>
  )
}
