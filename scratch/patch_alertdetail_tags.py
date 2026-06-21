import os

with open("frontend/src/pages/AlertDetail.jsx", "r") as f:
    content = f.read()

import_stmt = """import { addTags, removeTag, getAllTags } from '../api/alerts'
import { Tag, Plus, X } from 'lucide-react'
"""
if "addTags" not in content:
    content = content.replace("import { Activity, AlertTriangle, ChevronRight, Shield, RefreshCw } from 'lucide-react'", "import { Activity, AlertTriangle, ChevronRight, Shield, RefreshCw, Tag, Plus, X } from 'lucide-react'\n" + import_stmt)
    # the existing import might be different
    if "import { Tag" not in content:
        content = content.replace("from 'lucide-react'", ", Tag, Plus, X } from 'lucide-react'")
        content = content.replace("import { useAlertTimeline }", "import { useAlertTimeline } from '../hooks/useAlerts'\n" + import_stmt)

tags_logic = """
  // Tags logic
  const [showTagInput, setShowTagInput] = useState(false)
  const [tagInput, setTagInput] = useState('')
  
  const { data: allTags } = useQuery({
    queryKey: ['allTags'],
    queryFn: getAllTags
  })

  const addTagsMutation = useMutation({
    mutationFn: (tags) => addTags(alert_id, tags),
    onSuccess: () => {
      refetch()
      setShowTagInput(false)
      setTagInput('')
    }
  })

  const removeTagMutation = useMutation({
    mutationFn: (tag) => removeTag(alert_id, tag),
    onSuccess: () => refetch()
  })

  const handleAddTag = (e) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      addTagsMutation.mutate([tagInput.trim()])
    }
  }
"""
if "const [showTagInput" not in content:
    content = content.replace("const { timeline } = useAlertTimeline(alert_id)", "const { timeline } = useAlertTimeline(alert_id)\n" + tags_logic)


tags_ui = """
      {/* Tags Section */}
      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-[var(--border)] mt-2">
        <Tag className="w-4 h-4 text-[var(--text\_secondary)]" />
        {alert?.tags?.map((tag) => (
          <span key={tag} className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[var(--bg\_secondary)] border border-[var(--border)] text-xs text-[var(--text\_primary)] group cursor-pointer hover:border-red-500 hover:text-red-400 transition-colors"
                onClick={() => {
                  if(window.confirm(`Remove tag '${tag}'?`)) {
                    removeTagMutation.mutate(tag)
                  }
                }}>
            {tag}
            <X className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
          </span>
        ))}
        
        {showTagInput ? (
          <div className="relative">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleAddTag}
              onBlur={() => setTimeout(() => setShowTagInput(false), 200)}
              autoFocus
              placeholder="Type tag & Enter"
              className="px-2 py-1 text-xs rounded border border-blue-500 bg-[var(--bg\_primary)] text-[var(--text\_primary)] outline-none w-32"
            />
            {tagInput && allTags?.length > 0 && (
              <div className="absolute top-full left-0 mt-1 w-48 bg-[var(--bg\_primary)] border border-[var(--border)] rounded shadow-lg z-10 max-h-40 overflow-y-auto">
                {allTags
                  .filter(t => t.tag.toLowerCase().includes(tagInput.toLowerCase()) && !alert?.tags?.includes(t.tag))
                  .slice(0, 5)
                  .map(t => (
                    <div 
                      key={t.tag}
                      className="px-2 py-1 text-xs cursor-pointer hover:bg-[var(--bg\_tertiary)] flex justify-between"
                      onMouseDown={(e) => {
                        e.preventDefault() // prevent blur
                        addTagsMutation.mutate([t.tag])
                      }}
                    >
                      <span>{t.tag}</span>
                      <span className="text-[var(--text\_secondary)]">{t.count}</span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        ) : (
          <button 
            onClick={() => setShowTagInput(true)}
            className="flex items-center gap-1 px-2 py-1 rounded-full bg-[var(--bg\_tertiary)] hover:bg-blue-500/20 text-xs text-[var(--text\_secondary)] hover:text-blue-400 transition-colors"
          >
            <Plus className="w-3 h-3" /> Add tag
          </button>
        )}
      </div>
"""

# Insert Tags UI after the header description or something
if "Tags Section" not in content:
    # Find the end of the header block
    content = content.replace("<p className=\"text-[var(--text\_secondary)] mt-1\">{alert?.description}</p>", "<p className=\"text-[var(--text\_secondary)] mt-1\">{alert?.description}</p>\n" + tags_ui)

with open("frontend/src/pages/AlertDetail.jsx", "w") as f:
    f.write(content)
