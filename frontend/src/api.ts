export type Reciter = { id: number; nom: string; dossier: string }

export type Surah = {
  number: number
  name_fr: string
  name_ar: string
  verses: number
}

export type SubtitleStyle = {
  id: string
  name: string
  description: string
  preview: { color: string; outline: string; align: string }
}

export type VideoStyle = {
  id: string
  name: string
  description: string
}

export type Background = {
  id: string
  name: string
  source: 'library' | 'upload'
  path: string
}

export type PexelsVideo = {
  id: string
  url: string
  preview: string
  duration?: number
  user: string
  width?: number
  height?: number
}

export type PexelsSearch = {
  ok: boolean
  need_key: boolean
  message: string
  videos: PexelsVideo[]
}

export type Job = {
  id: string
  status: 'queued' | 'running' | 'done' | 'failed'
  progress: number
  stage: string
  message: string
  output_name: string | null
  error: string | null
  created_at: string
}

async function json<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<T>
}

export const api = {
  reciters: () => json<Reciter[]>('/api/reciters'),
  surahs: () => json<Surah[]>('/api/surahs'),
  styles: () =>
    json<{ subtitles: SubtitleStyle[]; video: VideoStyle[] }>('/api/styles'),
  estimate: (params: {
    reciter_id: number
    surah: number
    ayah_from: number
    ayah_to: number
    include_basmala: boolean
  }) => {
    const q = new URLSearchParams({
      reciter_id: String(params.reciter_id),
      surah: String(params.surah),
      ayah_from: String(params.ayah_from),
      ayah_to: String(params.ayah_to),
      include_basmala: String(params.include_basmala),
    })
    return json<{
      seconds: number
      formatted: string
      ayah_count: number
      from_cache: number
      estimated_ayahs: number
      precise: boolean
    }>(`/api/estimate?${q}`)
  },
  backgrounds: () => json<Background[]>('/api/backgrounds'),
  searchPexels: (q: string) =>
    json<PexelsSearch>(`/api/pexels/search?q=${encodeURIComponent(q)}`),
  upload: async (file: File) => {
    const form = new FormData()
    form.append('background', file)
    const res = await fetch('/api/uploads', { method: 'POST', body: form })
    if (!res.ok) throw new Error(await res.text())
    return res.json() as Promise<Background>
  },
  job: (id: string) => json<Job>(`/api/jobs/${id}`),
  createJob: async (form: FormData) => {
    const res = await fetch('/api/jobs', { method: 'POST', body: form })
    if (!res.ok) {
      const text = await res.text()
      try {
        const data = JSON.parse(text) as { detail?: string }
        throw new Error(data.detail || text)
      } catch (e) {
        if (e instanceof Error && !e.message.startsWith('{')) throw e
        throw new Error(text)
      }
    }
    return res.json() as Promise<Job>
  },
  downloadUrl: (id: string) => `/api/jobs/${id}/download`,
  previewUrl: (id: string) => `/api/jobs/${id}/preview`,
}
