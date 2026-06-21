import os

with open("frontend/src/api/alerts.js", "r") as f:
    content = f.read()

tag_methods = """
export const addTags = async (alert_id, tags) => {
  const response = await apiClient.post(`/api/alerts/${alert_id}/tags`, { tags })
  return response.data
}

export const removeTag = async (alert_id, tag) => {
  const response = await apiClient.delete(`/api/alerts/${alert_id}/tags/${tag}`)
  return response.data
}

export const getAllTags = async () => {
  const response = await apiClient.get('/api/alerts/tags')
  return response.data
}
"""

if "export const addTags" not in content:
    content += "\n" + tag_methods

with open("frontend/src/api/alerts.js", "w") as f:
    f.write(content)
