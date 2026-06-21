import os

with open("frontend/src/pages/Settings.jsx", "r") as f:
    content = f.read()

import_stmt = "import { TeamsPanel } from '../components/preferences/TeamsPanel'\n"
if "TeamsPanel" not in content:
    content = content.replace("import { SLMAnalyticsPanel } from '../components/preferences/SLMAnalyticsPanel'", "import { SLMAnalyticsPanel } from '../components/preferences/SLMAnalyticsPanel'\n" + import_stmt)

teams_tab_decl = """    { id: 'teams', label: 'Analyst Teams', icon: Users, adminOnly: true },
"""
if "{ id: 'teams'" not in content:
    content = content.replace("    { id: 'slm_analytics', label: 'SLM Analytics', icon: Brain, adminOnly: true },", "    { id: 'slm_analytics', label: 'SLM Analytics', icon: Brain, adminOnly: true },\n" + teams_tab_decl)

teams_render = """      {activeTab === "teams" && <TeamsPanel />}
"""
if "activeTab === \"teams\"" not in content:
    content = content.replace("{activeTab === \"slm_analytics\" && <SLMAnalyticsPanel />}", "{activeTab === \"slm_analytics\" && <SLMAnalyticsPanel />}\n" + teams_render)

with open("frontend/src/pages/Settings.jsx", "w") as f:
    f.write(content)
