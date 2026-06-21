with open("frontend/src/pages/Reports.jsx", "r") as f:
    content = f.read()

import_stmt = """
import { SLADashboard } from '../components/reports/SLADashboard'
"""

if "SLADashboard" not in content:
    content = content.replace("import { Link } from 'react-router-dom'", "import { Link } from 'react-router-dom'\n" + import_stmt)

state_addition = """
const Reports = () => {
  const [mainTab, setMainTab] = useState('shift') // shift, sla
  const [activeTab, setActiveTab] = useState(8) // 8 = Shift, 24 = Daily, 168 = Weekly
"""

if "mainTab" not in content:
    content = content.replace("const Reports = () => {\n  const [activeTab, setActiveTab] = useState(8)", state_addition)

header_addition = """
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text\_primary)] flex items-center gap-3">
            <FileText className="w-8 h-8 text-blue-500" />
            Reporting & Analytics
          </h1>
          <p className="text-[var(--text\_secondary)] mt-1">Generated AI narratives and performance metrics.</p>
        </div>

        <div className="flex items-center gap-4 bg-[var(--bg\_secondary)] p-1.5 rounded-lg border border-[var(--border)]">
          <button
            onClick={() => setMainTab('shift')}
            className={`px-4 py-2 text-sm font-bold rounded-md transition-colors ${mainTab === 'shift' ? 'bg-[var(--bg\_primary)] text-[var(--text\_primary)] shadow-sm' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
          >
            Shift Reports
          </button>
          <button
            onClick={() => setMainTab('sla')}
            className={`px-4 py-2 text-sm font-bold rounded-md transition-colors ${mainTab === 'sla' ? 'bg-[var(--bg\_primary)] text-[var(--text\_primary)] shadow-sm' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
          >
            SLA Performance
          </button>
        </div>
      </div>
"""

if "mainTab === 'sla'" not in content:
    content = content.replace("""      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text\_primary)] flex items-center gap-3">
            <FileText className="w-8 h-8 text-blue-500 p-1.5 bg-blue-500/10 rounded-lg border border-blue-500/20" />
            Shift Reports
          </h1>
          <p className="text-[var(--text\_secondary)] mt-1">AI-generated handover and summary reports</p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex bg-[var(--bg\_secondary)] rounded-lg p-1 border border-[var(--border)]">
            <button
              onClick={() => setActiveTab(8)}
              className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${activeTab === 8 ? 'bg-blue-600 text-white' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
            >
              Shift (8h)
            </button>
            <button
              onClick={() => setActiveTab(24)}
              className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${activeTab === 24 ? 'bg-blue-600 text-white' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
            >
              Daily (24h)
            </button>
            <button
              onClick={() => setActiveTab(168)}
              className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${activeTab === 168 ? 'bg-blue-600 text-white' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
            >
              Weekly (7d)
            </button>
          </div>
        </div>
      </div>""", header_addition)

sla_render = """
      {mainTab === 'sla' && <SLADashboard />}

      {mainTab === 'shift' && (
        <>
          <div className="flex justify-end mb-4">
            <div className="flex bg-[var(--bg\_secondary)] rounded-lg p-1 border border-[var(--border)]">
              <button
                onClick={() => setActiveTab(8)}
                className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${activeTab === 8 ? 'bg-blue-600 text-white' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
              >
                Shift (8h)
              </button>
              <button
                onClick={() => setActiveTab(24)}
                className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${activeTab === 24 ? 'bg-blue-600 text-white' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
              >
                Daily (24h)
              </button>
              <button
                onClick={() => setActiveTab(168)}
                className={`px-4 py-1.5 text-sm font-bold rounded-md transition-colors ${activeTab === 168 ? 'bg-blue-600 text-white' : 'text-[var(--text\_secondary)] hover:text-[var(--text\_primary)]'}`}
              >
                Weekly (7d)
              </button>
            </div>
          </div>
"""

if "mainTab === 'sla'" not in content:
    # Need to find the exact place where we start rendering the document body
    # It is right after the header div we replaced above.
    body_start = """      {/* Document Body */}
      <div className="bg-[var(--bg\_primary)] border border-[var(--border)] rounded-xl shadow-lg print:border-none print:shadow-none bg-white print:bg-white text-black font-sans max-w-5xl mx-auto overflow-hidden">"""
    
    content = content.replace(body_start, sla_render + "\n" + body_start)

    # Need to close the fragment for mainTab === 'shift' at the very end
    content = content.replace("export default Reports", "        </>\n      )}\n    </div>\n  )\n}\n\nexport default Reports")
    # Clean up the extra closing tags
    content = content.replace("    </div>\n  )\n}\n        </>\n      )}\n    </div>\n  )\n}", "        </>\n      )}\n    </div>\n  )\n}")

with open("frontend/src/pages/Reports.jsx", "w") as f:
    f.write(content)
