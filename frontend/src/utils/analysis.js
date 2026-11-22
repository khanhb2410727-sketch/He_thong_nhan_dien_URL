export const MODEL_OPTIONS = [
  { id: 'bayesian_bert', name: 'Bayesian BERT', file: 'bayesian_bert_checkpoint.pth', description: 'BERT với lớp phân loại Bayesian' },
  { id: 'bert_phishing', name: 'BERT Phishing', file: 'bert_phishing_final.pth', description: 'Mô hình BERT phân loại URL phishing' },
  { id: 'neural_symbolic', name: 'Neural Symbolic BERT', file: 'neural_symbolic_bert.pth', description: 'Kết hợp học sâu và ràng buộc logic' },
]

export function normalizeResult(raw, request) {
  // Adapter accepts either { predictions: [...] } or { results: [...] } from the backend.
  const source = raw?.predictions ?? raw?.results ?? raw?.model_results ?? []
  const predictions = Array.isArray(source) ? source.map((item) => ({
    modelId: item.model_id ?? item.model ?? item.id ?? 'unknown',
    modelName: item.model_name ?? item.name ?? MODEL_OPTIONS.find(m => m.id === (item.model_id ?? item.model ?? item.id))?.name ?? item.model ?? 'Model',
    label: normalizeLabel(item.label_text ?? item.label ?? item.prediction ?? item.class ?? item.result),
    confidence: toPercent(item.confidence ?? item.probability ?? item.score),
    rawLabel: item.label ?? item.prediction ?? item.class ?? item.result,
    details: item.details ?? item.explanation ?? '',
  })) : []

  const info = {
    ...(raw?.domain_info ?? {}),
    ...(raw?.url_info ?? {}),
    ...(raw?.redirect_info ?? {}),
    ...(raw?.technical_details ?? {}),
    ...(raw?.metadata ?? {}),
  }
  const domainInfo = raw?.domain_info ?? {}
  const whoisInfo = domainInfo.whois ?? {}
  const sslInfo = domainInfo.ssl ?? {}
  const securitySources = raw?.security_sources ?? raw?.sources ?? []
  return {
    url: raw?.normalized_url ?? raw?.url ?? request.url,
    analyzedAt: raw?.analyzed_at ?? raw?.timestamp ?? new Date().toISOString(),
    predictions,
    summary: getSummary(raw?.summary ?? raw?.overall_result ?? raw?.verdict),
    summaryDetails: typeof raw?.summary === 'object' ? raw.summary : null,
    safetyScore: raw?.safety_score ?? raw?.score ?? null,
    urlInfo: {
      domain: info.registered_domain ?? info.domain ?? info.hostname ?? 'Chưa có dữ liệu',
      subdomain: info.subdomain ?? 'Chưa có dữ liệu',
      tld: info.tld ?? info.extension ?? 'Chưa có dữ liệu',
      ip: info.ip ?? info.ip_address ?? 'Chưa có dữ liệu',
      country: whoisInfo.country ?? info.country ?? 'Chưa có dữ liệu',
      registrar: whoisInfo.registrar ?? info.registrar ?? 'Chưa có dữ liệu',
      registeredAt: whoisInfo.creation_date ?? info.registered_at ?? info.creation_date ?? 'Chưa có dữ liệu',
      domainAgeDays: whoisInfo.domain_age_days ?? null,
      ssl: sslInfo,
      dns: info.dns ?? info.dns_records ?? null,
      redirects: info.redirect_count ?? info.redirects ?? null,
      finalUrl: info.final_url ?? null,
      protocol: info.protocol ?? null,
      features: info.features ?? null,
    },
    securitySources: Array.isArray(securitySources) ? securitySources : [],
    raw,
  }
}

function normalizeLabel(value) {
  if (typeof value === 'number') return value === 1 ? 'Malicious' : 'Safe'
  const text = String(value ?? 'Unknown').toLowerCase()
  if (['1', 'phishing', 'malicious', 'unsafe', 'dangerous', 'bad'].includes(text)) return 'Malicious'
  if (['0', 'benign', 'safe', 'legitimate', 'clean', 'good'].includes(text)) return 'Safe'
  return String(value ?? 'Unknown')
}

function toPercent(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  if (!Number.isFinite(number)) return null
  return number <= 1 ? Math.round(number * 10000) / 100 : Math.round(number * 100) / 100
}

function getSummary(value) {
  if (!value) return null
  if (typeof value === 'string') return value
  if (typeof value.verdict === 'string') {
    return value.verdict === 'malicious' ? 'Potentially Unsafe' : 'Likely Safe'
  }
  return null
}

export function isMalicious(label) { return String(label).toLowerCase() === 'malicious' }
