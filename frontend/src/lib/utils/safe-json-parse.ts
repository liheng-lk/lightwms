/**
 * 安全 JSON 解析：避免非 JSON 响应导致崩溃
 *
 * 先读取 response.text()，再尝试 JSON.parse。
 * 如果解析失败，返回 { detail: ... } 以保持统一的错误格式。
 */
export async function safeJsonParse(response: Response): Promise<any> {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text || 'Unknown error' };
  }
}
