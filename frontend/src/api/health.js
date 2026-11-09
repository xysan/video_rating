export async function getHealth() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
  if (!baseUrl) throw new Error('请配置 VITE_API_BASE_URL')
  const response = await fetch(`${baseUrl.replace(/\/$/, '')}/api/health`, {
    signal: AbortSignal.timeout(10000),
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  const data = await response.json()
  if (data.status !== 'ok') throw new Error('后端返回异常状态')
  return data.status
}
