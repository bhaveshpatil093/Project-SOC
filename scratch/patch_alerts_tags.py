import os

with open("frontend/src/pages/Alerts.jsx", "r") as f:
    content = f.read()

import_stmt = "import { getAllTags } from '../api/alerts'\n"
if "getAllTags" not in content:
    content = content.replace("import { useAlerts, useUpdateAlertStatus } from '../hooks/useAlerts'", "import { useAlerts, useUpdateAlertStatus } from '../hooks/useAlerts'\n" + import_stmt)
    if "import { Tag" not in content:
        content = content.replace("from 'lucide-react'", ", Tag } from 'lucide-react'")

tags_query = """
  const { data: allTags } = useQuery({
    queryKey: ['allTags'],
    queryFn: getAllTags
  })
"""

if "const { data: allTags }" not in content:
    content = content.replace("const [selectedAlert, setSelectedAlert] = useState(null)", "const [selectedAlert, setSelectedAlert] = useState(null)\n" + tags_query)

tags_filter_ui = """
          <select 
            className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded px-3 py-1.5 text-sm"
            onChange={(e) => setFilters({ ...filters, tag: e.target.value })}
            value={filters.tag || ''}
          >
            <option value="">All Tags</option>
            {allTags?.map(t => (
              <option key={t.tag} value={t.tag}>{t.tag} ({t.count})</option>
            ))}
          </select>
"""

if "All Tags" not in content:
    content = content.replace("</select>\n          \n          {Object.keys(filters).length > 0 &&", "</select>\n" + tags_filter_ui + "\n          {Object.keys(filters).length > 0 &&")

# Add tags to the table headers
th_tags = """              {prefs.columns.tags !== false && <th className="text-left py-3 px-4 text-xs font-medium text-[var(--text\_secondary)] uppercase tracking-wider">Tags</th>}
"""
if "<th>Tags</th>" not in content and ">Tags<" not in content:
    content = content.replace("{prefs.columns.occurrences !== false && <th className=\"text-left py-3 px-4 text-xs font-medium text-[var(--text\_secondary)] uppercase tracking-wider\">Occurrences</th>}", "{prefs.columns.occurrences !== false && <th className=\"text-left py-3 px-4 text-xs font-medium text-[var(--text\_secondary)] uppercase tracking-wider\">Occurrences</th>}\n" + th_tags)

# Add tags to table row
td_tags = """                  {prefs.columns.tags !== false && (
                    <td className="py-3 px-4 border-b border-[var(--border)]">
                      <div className="flex flex-wrap gap-1">
                        {alert.tags?.slice(0, 2).map(tag => (
                          <span key={tag} className="text-[10px] px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded-full border border-blue-500/30 truncate max-w-[80px]" title={tag}>
                            {tag}
                          </span>
                        ))}
                        {alert.tags?.length > 2 && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-[var(--bg\_tertiary)] text-[var(--text\_secondary)] rounded-full border border-[var(--border)]">
                            +{alert.tags.length - 2}
                          </span>
                        )}
                        {(!alert.tags || alert.tags.length === 0) && <span className="text-[10px] text-[var(--text\_secondary)]">-</span>}
                      </div>
                    </td>
                  )}
"""

if "alert.tags?.slice(0, 2)" not in content:
    content = content.replace("{prefs.columns.occurrences !== false && (\n                    <td className=\"py-3 px-4 border-b border-[var(--border)]\">\n                      {alert.occurrence_count > 1 ? (\n                        <span className=\"inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 font-bold text-xs\">\n                          {alert.occurrence_count}x\n                        </span>\n                      ) : (\n                        <span className=\"text-gray-500\">-</span>\n                      )}\n                    </td>\n                  )}", "{prefs.columns.occurrences !== false && (\n                    <td className=\"py-3 px-4 border-b border-[var(--border)]\">\n                      {alert.occurrence_count > 1 ? (\n                        <span className=\"inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 font-bold text-xs\">\n                          {alert.occurrence_count}x\n                        </span>\n                      ) : (\n                        <span className=\"text-gray-500\">-</span>\n                      )}\n                    </td>\n                  )}\n" + td_tags)

with open("frontend/src/pages/Alerts.jsx", "w") as f:
    f.write(content)
