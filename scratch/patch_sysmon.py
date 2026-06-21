import os

with open("frontend/src/pages/SystemMonitor.jsx", "r") as f:
    content = f.read()

import_stmt = """import { LogViewer } from '../components/system/LogViewer'
"""

if "LogViewer" not in content:
    content = content.replace("import React, { useState } from 'react'", "import React, { useState } from 'react'\n" + import_stmt)

state_stmt = """  const [activeTab, setActiveTab] = useState('metrics') // metrics, logs
"""
if "const [activeTab" not in content:
    content = content.replace("  // Live System Metrics", state_stmt + "\n  // Live System Metrics")

tabs_ui = """        <div className="flex items-center gap-4 bg-[var(--bg\_secondary)] p-1.5 rounded-lg border border-[var(--border)]">
          <button
            onClick={() => setActiveTab('metrics')}
            className={`px-4 py-2 text-sm font-bold rounded-md transition-colors ${activeTab === 'metrics' ? 'bg-[var(--bg\_primary)] text-[var(--text\_primary)] shadow-sm' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
          >
            Metrics & Health
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-4 py-2 text-sm font-bold rounded-md transition-colors ${activeTab === 'logs' ? 'bg-[var(--bg\_primary)] text-[var(--text\_primary)] shadow-sm' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
          >
            Centralized Logs
          </button>
        </div>"""

header_replace = """        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${connected ? 'bg-green-400' : 'bg-red-400'}`}></span>
            <span className={`relative inline-flex rounded-full h-3 w-3 ${connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
          </span>
          <span className="text-sm font-medium text-[var(--text\_secondary)]">Live Telemetry</span>
        </div>"""

if "setActiveTab('metrics')" not in content:
    content = content.replace(header_replace, tabs_ui)

render_split = """      {activeTab === 'logs' ? (
        <LogViewer />
      ) : (
        <div className="space-y-8 animate-in fade-in duration-500">
"""

if "activeTab === 'logs'" not in content:
    # Insert render_split right after the header
    header_end = "      </div>\n\n      {/* 1. Live System Metrics */}"
    content = content.replace(header_end, "      </div>\n" + render_split + "      {/* 1. Live System Metrics */}")
    
    # Close the div at the very end
    content = content.replace("export const SystemMonitor", "        </div>\n      )}\n    </div>\n  )\n}\n\nexport const SystemMonitor")
    content = content.replace("    </div>\n  )\n}\n        </div>\n      )}\n    </div>\n  )\n}\n\nexport const SystemMonitor", "        </div>\n      )}\n    </div>\n  )\n}\n\nexport const SystemMonitor")

with open("frontend/src/pages/SystemMonitor.jsx", "w") as f:
    f.write(content)
