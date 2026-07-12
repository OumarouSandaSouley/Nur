import { useEffect, useMemo, useState } from 'react'
import {
  api,
  type AudioReciterGroup,
  type Background,
  type HistoryItem,
  type Job,
  type PexelsVideo,
  type Reciter,
  type SubtitleStyle,
  type Surah,
  type SubtitleAnim,
  type VideoStyle,
} from './api'
import { DownloadIcon } from 'lucide-react';

type Page = 'home' | 'create' | 'history' | 'library' | 'audio'

const PAGES: { id: Page; label: string; hint: string }[] = [
  { id: 'home', label: 'Tableau de bord', hint: 'Vue d’ensemble' },
  { id: 'create', label: 'Créer', hint: 'Nouvelle vidéo' },
  { id: 'history', label: 'Historique', hint: 'Vidéos & édition' },
  { id: 'library', label: 'Fonds', hint: 'Bibliothèque vidéo' },
  { id: 'audio', label: 'Sons', hint: 'Audio en cache' },
]

const STEPS = [
  { label: 'Contenu', hint: 'Récitateur & sourate' },
  { label: 'Sous-titres', hint: 'Style & animation' },
  { label: 'Vidéo', hint: 'Fond & rendu' },
  { label: 'Générer', hint: 'Lancer le job' },
] as const

const SAMPLE_AR = 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ'

export default function App() {
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [page, setPage] = useState<Page>('home')
  const [step, setStep] = useState(0)

  const [reciters, setReciters] = useState<Reciter[]>([])
  const [surahs, setSurahs] = useState<Surah[]>([])
  const [subStyles, setSubStyles] = useState<SubtitleStyle[]>([])
  const [subAnims, setSubAnims] = useState<SubtitleAnim[]>([])
  const [videoStyles, setVideoStyles] = useState<VideoStyle[]>([])
  const [backgrounds, setBackgrounds] = useState<Background[]>([])

  const [reciterId, setReciterId] = useState(3)
  const [surah, setSurah] = useState(1)
  const [ayahFrom, setAyahFrom] = useState(1)
  const [ayahTo, setAyahTo] = useState(7)
  const [includeBasmala, setIncludeBasmala] = useState(true)
  const [translation, setTranslation] = useState<'none' | 'fr' | 'en'>('none')
  const [subtitleStyle, setSubtitleStyle] = useState('classic')
  const [subtitleAnim, setSubtitleAnim] = useState('fade')
  const [longVerseMode, setLongVerseMode] = useState<'pages' | 'block'>('pages')
  const [fontSize, setFontSize] = useState(22)
  const [videoStyle, setVideoStyle] = useState('clean')
  const [showCredits, setShowCredits] = useState(false)

  const [bgMode, setBgMode] = useState<'url' | 'search' | 'upload' | 'library'>('search')
  const [backgroundUrl, setBackgroundUrl] = useState('')
  const [backgroundId, setBackgroundId] = useState('')
  const [montageIds, setMontageIds] = useState<string[]>([])
  const [bgFile, setBgFile] = useState<File | null>(null)
  const [pexelsQuery, setPexelsQuery] = useState('nature')
  const [pexelsVideos, setPexelsVideos] = useState<PexelsVideo[]>([])
  const [pexelsMsg, setPexelsMsg] = useState('')
  const [pexelsBusy, setPexelsBusy] = useState(false)
  const [selectedPexelsUrl, setSelectedPexelsUrl] = useState('')
  const [importingId, setImportingId] = useState<string | null>(null)
  const [libTab, setLibTab] = useState<'browse' | 'search' | 'upload'>('browse')
  const [audioGroups, setAudioGroups] = useState<AudioReciterGroup[]>([])
  const [audioOpen, setAudioOpen] = useState<string | null>(null)
  const [audioPlayingUrl, setAudioPlayingUrl] = useState<string | null>(null)

  const [job, setJob] = useState<Job | null>(null)
  const [queue, setQueue] = useState<Job[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [estimate, setEstimate] = useState<string | null>(null)
  const [estimatePrecise, setEstimatePrecise] = useState(false)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)
  const [audioPreview, setAudioPreview] = useState<HTMLAudioElement | null>(null)
  const [audioPlaying, setAudioPlaying] = useState(false)
  const [editTarget, setEditTarget] = useState('')
  const [editStart, setEditStart] = useState(0)
  const [editEnd, setEditEnd] = useState(0)
  const [editSelected, setEditSelected] = useState<string[]>([])
  const [editBusy, setEditBusy] = useState(false)

  const currentSurah = useMemo(
    () => surahs.find((s) => s.number === surah),
    [surahs, surah],
  )
  const maxVerses = currentSurah?.verses ?? 7
  const selectedReciter = reciters.find((r) => r.id === reciterId)
  const selectedSub = subStyles.find((s) => s.id === subtitleStyle)
  const selectedVid = videoStyles.find((s) => s.id === videoStyle)
  const uploads = backgrounds.filter((b) => b.source === 'upload')
  const libraryAssets = backgrounds.filter((b) => b.source === 'library')
  const urlFonds = backgrounds.filter((b) => b.source === 'url')
  const allFonds = backgrounds
  const availableSurahs = useMemo(() => {
    if (selectedReciter?.surahs?.length) {
      const allow = new Set(selectedReciter.surahs)
      return surahs.filter((s) => allow.has(s.number))
    }
    return surahs
  }, [surahs, selectedReciter])

  const creditLine1 = useMemo(() => {
    const name = currentSurah?.name_fr || `Sourate ${surah}`
    return ayahFrom === ayahTo ? `${name} - ${ayahFrom}` : `${name} - ${ayahFrom}-${ayahTo}`
  }, [currentSurah, surah, ayahFrom, ayahTo])

  async function refreshBackgrounds() {
    setBackgrounds(await api.backgrounds())
  }

  async function refreshHistory() {
    try {
      setHistory(await api.history())
    } catch {
      /* ignore */
    }
  }

  async function refreshAudio() {
    try {
      setAudioGroups(await api.audioCache())
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    if (page === 'history' || page === 'home' || job?.status === 'done') refreshHistory()
  }, [page, job?.status])

  useEffect(() => {
    if (page === 'library' || page === 'home' || page === 'create') {
      refreshBackgrounds().catch(() => undefined)
    }
  }, [page])

  useEffect(() => {
    if (page === 'audio' || page === 'home') refreshAudio()
  }, [page])

  useEffect(() => {
    Promise.all([
      api.reciters(),
      api.surahs(),
      api.styles(),
      api.backgrounds(),
      api.history().catch(() => [] as HistoryItem[]),
      api.listJobs().catch(() => [] as Job[]),
    ])
      .then(([r, s, st, b, h, jobs]) => {
        setReciters(r)
        setSurahs(s)
        setSubStyles(st.subtitles)
        setSubAnims(st.anims || [])
        setVideoStyles(st.video)
        setBackgrounds(b)
        setHistory(h)
        setQueue(jobs)
        const prefer = r.find((x) => x.id === 3) ?? r[0]
        if (prefer) setReciterId(prefer.id)
      })
      .catch((e: unknown) => {
        setLoadError(e instanceof Error ? e.message : 'Impossible de charger l’API')
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!availableSurahs.length) return
    if (!availableSurahs.some((s) => s.number === surah)) {
      setSurah(availableSurahs[0].number)
    }
  }, [availableSurahs, surah])

  useEffect(() => {
    if (!currentSurah) return
    setAyahFrom(1)
    setAyahTo(Math.min(7, currentSurah.verses))
  }, [surah]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let cancelled = false
    const t = setTimeout(() => {
      api
        .estimate({
          reciter_id: reciterId,
          surah,
          ayah_from: ayahFrom,
          ayah_to: ayahTo,
          include_basmala: includeBasmala,
        })
        .then((e) => {
          if (cancelled) return
          setEstimate(e.formatted)
          setEstimatePrecise(e.precise)
        })
        .catch(() => {
          if (!cancelled) setEstimate(null)
        })
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [reciterId, surah, ayahFrom, ayahTo, includeBasmala])

  useEffect(() => {
    if (!job || job.status === 'done' || job.status === 'failed' || job.status === 'cancelled')
      return
    const t = setInterval(() => {
      api.job(job.id).then(setJob).catch(() => undefined)
      api.listJobs().then(setQueue).catch(() => undefined)
    }, 1200)
    return () => clearInterval(t)
  }, [job])

  async function runPexelsSearch() {
    setPexelsBusy(true)
    setPexelsMsg('')
    try {
      const res = await api.searchPexels(pexelsQuery)
      setPexelsVideos(res.videos)
      setPexelsMsg(res.message || (res.videos.length ? '' : 'Aucun résultat'))
    } catch (e: unknown) {
      setPexelsMsg(e instanceof Error ? e.message : 'Erreur recherche')
    } finally {
      setPexelsBusy(false)
    }
  }

  async function startGeneration() {
    setError(null)
    setBusy(true)
    setJob(null)
    setPage('create')
    setStep(3)
    try {
      const form = new FormData()
      form.append('reciter_id', String(reciterId))
      form.append('surah', String(surah))
      form.append('ayah_from', String(ayahFrom))
      form.append('ayah_to', String(ayahTo))
      form.append('subtitle_style', subtitleStyle)
      form.append('subtitle_anim', subtitleAnim)
      form.append('long_verse_mode', longVerseMode)
      form.append('font_size', String(fontSize))
      form.append('video_style', videoStyle)
      form.append('include_basmala', String(includeBasmala))
      form.append('translation', translation)
      form.append('show_credits', String(showCredits))

      if (bgMode === 'url' && backgroundUrl.trim()) {
        form.append('background_url', backgroundUrl.trim())
      } else if (bgMode === 'search' && selectedPexelsUrl) {
        form.append('background_url', selectedPexelsUrl)
      } else if (bgFile) {
        form.append('background', bgFile)
      } else if (montageIds.length > 1) {
        form.append('background_ids', JSON.stringify(montageIds))
      } else if (montageIds.length === 1) {
        form.append('background_id', montageIds[0])
      } else if (backgroundId) {
        form.append('background_id', backgroundId)
      }

      const created = await api.createJob(form)
      setJob(created)
      setPreviewSrc(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur de création')
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="dash loading-screen">
        <p className="loading">Chargement du studio…</p>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="dash loading-screen">
        <div className="panel">
          <h2>API inaccessible</h2>
          <p className="hint">Lance <code>start.bat</code> puis recharge.</p>
          <p className="error">{loadError}</p>
        </div>
      </div>
    )
  }

  const bgLabel =
    montageIds.length > 1
      ? `Montage · ${montageIds.length} fonds`
      : bgMode === 'url' && backgroundUrl
        ? 'URL personnalisée'
        : bgMode === 'search' && selectedPexelsUrl
          ? 'Pexels sélectionné'
          : bgFile?.name ||
            backgrounds.find((b) => b.id === (montageIds[0] || backgroundId))?.name ||
            'Fond uni auto'

  function toggleMontage(id: string) {
    setMontageIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= 6) return prev
      return [...prev, id]
    })
    setBackgroundId(id)
    setBgFile(null)
    setBackgroundUrl('')
    setSelectedPexelsUrl('')
  }


  function useAsBackground(id: string) {
    setMontageIds([id])
    setBackgroundId(id)
    setBgFile(null)
    setBackgroundUrl('')
    setSelectedPexelsUrl('')
    setBgMode('library')
    setPage('create')
    setStep(2)
  }

  async function addPexelsToLibrary(v: PexelsVideo) {
    setImportingId(v.id)
    setError(null)
    try {
      const item = await api.importBackground(v.url, `pexels_${v.user}`)
      await refreshBackgrounds()
      setLibTab('browse')
      setPexelsMsg(`Ajouté : ${item.name}`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Import échoué')
    } finally {
      setImportingId(null)
    }
  }

  function playCachedAudio(url: string) {
    if (audioPreview) {
      audioPreview.pause()
    }
    if (audioPlayingUrl === url) {
      setAudioPlayingUrl(null)
      setAudioPlaying(false)
      return
    }
    const a = new Audio(url)
    a.onended = () => {
      setAudioPlaying(false)
      setAudioPlayingUrl(null)
    }
    a.play()
      .then(() => {
        setAudioPlaying(true)
        setAudioPlayingUrl(url)
        setAudioPreview(a)
      })
      .catch(() => {
        setAudioPlaying(false)
        setAudioPlayingUrl(null)
      })
  }

  function moveMontage(index: number, dir: -1 | 1) {
    setMontageIds((prev) => {
      const next = [...prev]
      const j = index + dir
      if (j < 0 || j >= next.length) return prev
      ;[next[index], next[j]] = [next[j], next[index]]
      return next
    })
  }

  const activePage = PAGES.find((p) => p.id === page) ?? PAGES[0]
  const activeJobs = queue.filter((j) => j.status === 'queued' || j.status === 'running')
  const recentHistory = history.slice(0, 5)
  const showPreview = page === 'create' || page === 'history'

  return (
    <div className="dash">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <img src="/nur-logo.png" alt="" className="brand-logo" width={36} height={36} />
          <div>
            <p className="brand">
              Nur<span>.</span>
            </p>
            <p className="tagline">Studio vidéo</p>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Navigation">
          {PAGES.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${page === item.id ? 'active' : ''}`}
              onClick={() => {
                setPage(item.id)
                if (item.id === 'create' && job?.status === 'done') {
                  /* keep preview */
                }
              }}
            >
              <span className="nav-copy">
                <strong>{item.label}</strong>
                <small>{item.hint}</small>
              </span>
              {item.id === 'history' && history.length > 0 && (
                <span className="nav-badge">{history.length}</span>
              )}
              {item.id === 'library' && allFonds.length > 0 && (
                <span className="nav-badge">{allFonds.length}</span>
              )}
              {item.id === 'audio' && audioGroups.length > 0 && (
                <span className="nav-badge">
                  {audioGroups.reduce((n, g) => n + g.file_count, 0)}
                </span>
              )}
              {item.id === 'create' && activeJobs.length > 0 && (
                <span className="nav-badge live">{activeJobs.length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <button
            type="button"
            className="btn btn-gold sidebar-cta"
            onClick={() => {
              setPage('create')
              setStep(0)
            }}
          >
            Nouvelle vidéo
          </button>
        </div>
      </aside>

      <main className="dash-main">
        <header className="dash-top">
          <div>
            <h1>{activePage.label}</h1>
            <p className="dash-sub">{activePage.hint}</p>
          </div>
          <div className="dash-top-actions">
            {page === 'create' && step < 3 && (
              <button type="button" className="btn btn-primary" onClick={() => setStep(step + 1)}>
                Suivant
              </button>
            )}
            {page === 'create' && step === 3 && (
              <button
                type="button"
                className="btn btn-gold"
                disabled={busy || job?.status === 'running' || job?.status === 'queued'}
                onClick={startGeneration}
              >
                {busy ? 'Lancement…' : 'Générer'}
              </button>
            )}
            {page === 'home' && (
              <button
                type="button"
                className="btn btn-gold"
                onClick={() => {
                  setPage('create')
                  setStep(0)
                }}
              >
                Créer
              </button>
            )}
          </div>
        </header>

        {page === 'create' && (
          <nav className="wizard-steps" aria-label="Étapes de création">
            {STEPS.map((s, i) => (
              <button
                key={s.label}
                type="button"
                className={`wizard-step ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}
                onClick={() => setStep(i)}
              >
                <span>{i + 1}</span>
                {s.label}
              </button>
            ))}
          </nav>
        )}

        <div className={`dash-body ${showPreview ? '' : 'full'}`}>
          <div className="dash-content">
            {page === 'home' && (
              <section className="home-grid">
                <div className="stat-row">
                  <article className="stat-card">
                    <p>Vidéos</p>
                    <strong>{history.length}</strong>
                  </article>
                  <article className="stat-card">
                    <p>Fonds</p>
                    <strong>{backgrounds.length}</strong>
                  </article>
                  <article className="stat-card">
                    <p>En cours</p>
                    <strong>{activeJobs.length}</strong>
                  </article>
                </div>

                {activeJobs.length > 0 && (
                  <div className="panel">
                    <h2 className="panel-title">File d&apos;attente</h2>
                    {activeJobs.map((j) => (
                      <div key={j.id} className="queue-row">
                        <span>
                          {j.id.slice(0, 6)} · {j.status} · {j.progress}% — {j.message}
                        </span>
                        <button
                          type="button"
                          className="btn btn-ghost"
                          onClick={async () => {
                            const updated = await api.cancelJob(j.id)
                            if (job?.id === j.id) setJob(updated)
                            setQueue(await api.listJobs())
                          }}
                        >
                          Annuler
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="panel">
                  <div className="panel-head">
                    <h2 className="panel-title">Récentes</h2>
                    <button type="button" className="btn btn-ghost" onClick={() => setPage('history')}>
                      Tout voir
                    </button>
                  </div>
                  {recentHistory.length === 0 && (
                    <p className="empty-line">Aucune vidéo pour l’instant.</p>
                  )}
                  <div className="history-list">
                    {recentHistory.map((h) => (
                      <div key={h.id} className="history-item">
                        <div className="history-meta">
                          <strong title={h.name}>{h.name}</strong>
                          <span>
                            {(h.size / (1024 * 1024)).toFixed(1)} Mo
                            {typeof h.meta.duration_seconds === 'number'
                              ? ` · ${Math.round(h.meta.duration_seconds as number)}s`
                              : ''}
                          </span>
                        </div>
                        <div className="history-actions">
                          <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={() => {
                              setPreviewSrc(h.preview_url)
                              setEditTarget(h.id)
                              setPage('history')
                            }}
                          >
                            Ouvrir
                          </button>
                          <a className="btn btn-primary" href={h.download_url} download>
                            <DownloadIcon className="w-4 h-4 mr-2" />
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="panel home-cta">
                  <h2 className="panel-title">Créer une vidéo</h2>
                  <p className="hint">Choisis un récitateur, une sourate, un fond.</p>
                  <button
                    type="button"
                    className="btn btn-gold"
                    onClick={() => {
                      setPage('create')
                      setStep(0)
                    }}
                  >
                    Lancer le studio
                  </button>
                </div>
              </section>
            )}

            {page === 'create' && step === 0 && (
              <section className="panel step-panel">
                <div className="field-grid">
                  <label className="field">
                    Récitateur
                    <select
                      value={reciterId}
                      onChange={(e) => setReciterId(Number(e.target.value))}
                    >
                      {reciters.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.nom}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="btn btn-ghost audio-btn"
                    onClick={() => {
                      if (audioPlaying && audioPreview) {
                        audioPreview.pause()
                        setAudioPlaying(false)
                        return
                      }
                      const url = api.reciterPreviewUrl(reciterId, surah, ayahFrom)
                      const a = new Audio(url)
                      a.onended = () => setAudioPlaying(false)
                      a.play()
                        .then(() => setAudioPlaying(true))
                        .catch(() => setAudioPlaying(false))
                      setAudioPreview(a)
                    }}
                  >
                    {audioPlaying ? 'Pause aperçu' : 'Écouter un verset'}
                  </button>
                  <label className="field">
                    Sourate
                    <select value={surah} onChange={(e) => setSurah(Number(e.target.value))}>
                      {availableSurahs.map((s) => (
                        <option key={s.number} value={s.number}>
                          {s.number}. {s.name_fr} ({s.verses} v.)
                        </option>
                      ))}
                    </select>
                  </label>
                  {currentSurah && <p className="surah-ar">{currentSurah.name_ar}</p>}
                  <div className="field-grid two">
                    <label className="field">
                      De
                      <input
                        type="number"
                        min={1}
                        max={maxVerses}
                        value={ayahFrom}
                        onChange={(e) => {
                          const v = Math.max(1, Math.min(maxVerses, Number(e.target.value) || 1))
                          setAyahFrom(v)
                          if (v > ayahTo) setAyahTo(v)
                        }}
                      />
                    </label>
                    <label className="field">
                      À
                      <input
                        type="number"
                        min={ayahFrom}
                        max={maxVerses}
                        value={ayahTo}
                        onChange={(e) => {
                          const v = Math.max(
                            ayahFrom,
                            Math.min(maxVerses, Number(e.target.value) || ayahFrom),
                          )
                          setAyahTo(v)
                        }}
                      />
                    </label>
                  </div>
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={includeBasmala}
                      onChange={(e) => setIncludeBasmala(e.target.checked)}
                      disabled={surah === 1 || surah === 9 || ayahFrom !== 1}
                    />
                    Inclure la basmala
                  </label>
                  <label className="field">
                    Traduction sous-titres
                    <select
                      value={translation}
                      onChange={(e) => setTranslation(e.target.value as 'none' | 'fr' | 'en')}
                    >
                      <option value="none">Arabe seul</option>
                      <option value="fr">Arabe + Français</option>
                      <option value="en">Arabe + Anglais</option>
                    </select>
                  </label>
                  {estimate && (
                    <p className="estimate-chip">
                      Durée {estimatePrecise ? '' : '~'}
                      <strong>{estimate}</strong>
                      {!estimatePrecise && <span> (approx.)</span>}
                    </p>
                  )}
                </div>
              </section>
            )}

            {page === 'create' && step === 1 && (
              <section className="panel step-panel">
                <div className="preset-grid compact">
                  {subStyles.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      className={`preset ${subtitleStyle === s.id ? 'selected' : ''}`}
                      onClick={() => setSubtitleStyle(s.id)}
                    >
                      <strong>{s.name}</strong>
                      <div
                        className="sub-preview"
                        style={{
                          color: s.preview.color,
                          textShadow: `0 0 2px ${s.preview.outline}`,
                        }}
                      >
                        {SAMPLE_AR}
                      </div>
                    </button>
                  ))}
                </div>
                <label className="field" style={{ marginTop: '0.75rem' }}>
                  Taille du texte ({fontSize})
                  <input
                    type="range"
                    min={14}
                    max={36}
                    value={fontSize}
                    onChange={(e) => setFontSize(Number(e.target.value))}
                  />
                  <span className="field-hint">14 = discret · 22 = confort · 36 = grand Reels</span>
                </label>
                <p className="field-label" style={{ marginTop: '0.85rem' }}>
                  Animation
                </p>
                <div className="anim-grid">
                  {subAnims.map((a) => (
                    <button
                      key={a.id}
                      type="button"
                      className={`anim-chip ${subtitleAnim === a.id ? 'selected' : ''}`}
                      onClick={() => setSubtitleAnim(a.id)}
                      title={a.description}
                    >
                      {a.name}
                    </button>
                  ))}
                </div>
                <p className="field-label" style={{ marginTop: '0.85rem' }}>
                  Versets longs
                </p>
                <div className="anim-grid">
                  <button
                    type="button"
                    className={`anim-chip ${longVerseMode === 'pages' ? 'selected' : ''}`}
                    onClick={() => setLongVerseMode('pages')}
                  >
                    Petits blocs
                  </button>
                  <button
                    type="button"
                    className={`anim-chip ${longVerseMode === 'block' ? 'selected' : ''}`}
                    onClick={() => setLongVerseMode('block')}
                  >
                    D&apos;un coup
                  </button>
                </div>
              </section>
            )}

            {page === 'create' && step === 2 && (
              <section className="panel step-panel">
                <div className="preset-grid compact">
                  {videoStyles.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      className={`preset ${videoStyle === s.id ? 'selected' : ''}`}
                      onClick={() => setVideoStyle(s.id)}
                    >
                      <strong>{s.name}</strong>
                      <span>{s.description}</span>
                    </button>
                  ))}
                </div>

                <div className="panel-head" style={{ marginTop: '0.9rem' }}>
                  <p className="field-label" style={{ margin: 0 }}>Fond sélectionné</p>
                  <button type="button" className="btn btn-ghost" onClick={() => setPage('library')}>
                    Gérer les fonds
                  </button>
                </div>
                <p className="hint tight">{bgLabel}</p>
                {montageIds.length > 1 && (
                  <div className="montage-bar">
                    <p className="field-label">Montage ({montageIds.length}/6)</p>
                    <div className="montage-list">
                      {montageIds.map((id, i) => {
                        const item = backgrounds.find((b) => b.id === id)
                        return (
                          <div key={`${id}-${i}`} className="montage-chip">
                            <span>
                              {i + 1}. {item?.name || id}
                            </span>
                            <button
                              type="button"
                              className="btn btn-ghost tiny"
                              disabled={i === 0}
                              onClick={() => moveMontage(i, -1)}
                            >
                              ↑
                            </button>
                            <button
                              type="button"
                              className="btn btn-ghost tiny"
                              disabled={i === montageIds.length - 1}
                              onClick={() => moveMontage(i, 1)}
                            >
                              ↓
                            </button>
                            <button
                              type="button"
                              className="btn btn-ghost tiny"
                              onClick={() => setMontageIds((prev) => prev.filter((_, j) => j !== i))}
                            >
                              ×
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
                <div className="lib-grid">
                  {allFonds.map((b) => (
                    <div
                      key={b.id}
                      className={`lib-card static ${montageIds.includes(b.id) || backgroundId === b.id ? 'selected' : ''}`}
                    >
                      {b.thumb_url ? <img src={b.thumb_url} alt="" /> : <div className="lib-ph" />}
                      <span>
                        {b.name}
                        {b.duration ? ` · ${Math.round(b.duration)}s` : ''}
                      </span>
                      <div className="lib-actions">
                        <button type="button" className="btn btn-gold tiny" onClick={() => useAsBackground(b.id)}>
                          Utiliser
                        </button>
                        <button
                          type="button"
                          className="btn btn-ghost tiny"
                          disabled={montageIds.includes(b.id) || montageIds.length >= 6}
                          onClick={() => toggleMontage(b.id)}
                        >
                          + Montage
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                {!allFonds.length && (
                  <p className="empty-line">
                    Aucun fond — va dans Fonds pour rechercher ou uploader.
                  </p>
                )}
                {error && step === 2 && <p className="error">{error}</p>}
              </section>
            )}

            {page === 'create' && step === 3 && (
              <section className="panel step-panel">
                <ul className="summary">
                  <li>
                    <span>Récitateur</span>
                    <span>{selectedReciter?.nom}</span>
                  </li>
                  <li>
                    <span>Sourate</span>
                    <span>
                      {currentSurah?.number}. {currentSurah?.name_fr} ({ayahFrom}–{ayahTo})
                    </span>
                  </li>
                  <li>
                    <span>Traduction</span>
                    <span>
                      {translation === 'none' ? 'Aucune' : translation.toUpperCase()}
                    </span>
                  </li>
                  <li>
                    <span>Sous-titres</span>
                    <span>
                      {selectedSub?.name}
                      {subAnims.find((a) => a.id === subtitleAnim)
                        ? ` · ${subAnims.find((a) => a.id === subtitleAnim)?.name}`
                        : ''}
                    </span>
                  </li>
                  <li>
                    <span>Longs versets</span>
                    <span>{longVerseMode === 'block' ? "D'un coup" : 'Petits blocs'}</span>
                  </li>
                  <li>
                    <span>Style</span>
                    <span>{selectedVid?.name}</span>
                  </li>
                  <li>
                    <span>Fond</span>
                    <span>{bgLabel}</span>
                  </li>
                  <li>
                    <span>Watermark</span>
                    <span>Logo Nur</span>
                  </li>
                  <li>
                    <span>Crédits bas</span>
                    <span>{showCredits ? 'Oui' : 'Non'}</span>
                  </li>
                </ul>

                <label className="checkbox-row credits-toggle">
                  <input
                    type="checkbox"
                    checked={showCredits}
                    onChange={(e) => setShowCredits(e.target.checked)}
                  />
                  Afficher en bas : sourate · versets, puis récitateur
                </label>
                {showCredits && (
                  <div className="credits-preview">
                    <p>{creditLine1}</p>
                    <p>{selectedReciter?.nom}</p>
                  </div>
                )}

                {error && <p className="error">{error}</p>}
                {queue.some((j) => j.status === 'queued' || j.status === 'running') && (
                  <div className="queue-box">
                    <h3>File d&apos;attente</h3>
                    {queue
                      .filter((j) => j.status === 'queued' || j.status === 'running')
                      .map((j) => (
                        <div key={j.id} className="queue-row">
                          <span>
                            {j.id.slice(0, 6)} · {j.status} · {j.progress}%
                          </span>
                          <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={async () => {
                              const updated = await api.cancelJob(j.id)
                              if (job?.id === j.id) setJob(updated)
                              setQueue(await api.listJobs())
                            }}
                          >
                            Annuler
                          </button>
                        </div>
                      ))}
                  </div>
                )}
              </section>
            )}

            {page === 'history' && (
              <section className="panel step-panel">
                <div className="edit-tools">
                  <label className="field">
                    Vidéo
                    <select
                      value={editTarget}
                      onChange={(e) => {
                        const name = e.target.value
                        setEditTarget(name)
                        const item = history.find((h) => h.id === name)
                        const dur =
                          typeof item?.meta.duration_seconds === 'number'
                            ? (item.meta.duration_seconds as number)
                            : 0
                        setEditStart(0)
                        setEditEnd(dur > 0 ? Math.round(dur * 10) / 10 : 0)
                        if (item) {
                          setPreviewSrc(item.preview_url)
                          setJob(null)
                        }
                      }}
                    >
                      <option value="">Choisir…</option>
                      {history.map((h) => (
                        <option key={h.id} value={h.id}>
                          {h.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <div className="field-grid two">
                    <label className="field">
                      Début (s)
                      <input
                        type="number"
                        min={0}
                        step={0.1}
                        value={editStart}
                        onChange={(e) => setEditStart(Math.max(0, Number(e.target.value) || 0))}
                      />
                    </label>
                    <label className="field">
                      Fin (s)
                      <input
                        type="number"
                        min={0}
                        step={0.1}
                        value={editEnd}
                        onChange={(e) => setEditEnd(Math.max(0, Number(e.target.value) || 0))}
                      />
                    </label>
                  </div>

                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={!editTarget || editBusy}
                    onClick={async () => {
                      setEditBusy(true)
                      setError(null)
                      try {
                        const res = await api.trimVideo(
                          editTarget,
                          editStart,
                          editEnd > 0 ? editEnd : null,
                        )
                        await refreshHistory()
                        setEditTarget(res.name)
                        setPreviewSrc(res.preview_url)
                        setEditStart(0)
                        setEditEnd(res.duration)
                      } catch (e: unknown) {
                        setError(e instanceof Error ? e.message : 'Trim échoué')
                      } finally {
                        setEditBusy(false)
                      }
                    }}
                  >
                    {editBusy ? 'Coupe…' : 'Couper'}
                  </button>
                </div>

                <p className="field-label" style={{ marginTop: '0.85rem' }}>
                  Montage ({editSelected.length})
                </p>
                <div className="history-list">
                  {history.length === 0 && <p className="empty-line">Aucune vidéo</p>}
                  {history.map((h) => {
                    const selected = editSelected.includes(h.id)
                    return (
                      <div
                        key={h.id}
                        className={`history-item ${selected ? 'selected' : ''}`}
                      >
                        <label className="history-check">
                          <input
                            type="checkbox"
                            checked={selected}
                            onChange={() => {
                              setEditSelected((prev) =>
                                prev.includes(h.id)
                                  ? prev.filter((x) => x !== h.id)
                                  : prev.length >= 8
                                    ? prev
                                    : [...prev, h.id],
                              )
                            }}
                          />
                          <div className="history-meta">
                            <strong title={h.name}>{h.name}</strong>
                            <span>
                              {(h.size / (1024 * 1024)).toFixed(1)} Mo
                              {typeof h.meta.duration_seconds === 'number'
                                ? ` · ${Math.round(h.meta.duration_seconds as number)}s`
                                : ''}
                            </span>
                          </div>
                        </label>
                        <div className="history-actions">
                          <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={() => {
                              setPreviewSrc(h.preview_url)
                              setEditTarget(h.id)
                              const dur =
                                typeof h.meta.duration_seconds === 'number'
                                  ? (h.meta.duration_seconds as number)
                                  : 0
                              setEditStart(0)
                              setEditEnd(dur)
                              setJob(null)
                            }}
                          >
                            Voir
                          </button>
                          <a className="btn btn-primary" href={h.download_url} download>
                            DL
                          </a>
                          <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={async () => {
                              await api.deleteHistory(h.id)
                              if (previewSrc === h.preview_url) setPreviewSrc(null)
                              if (editTarget === h.id) setEditTarget('')
                              setEditSelected((prev) => prev.filter((x) => x !== h.id))
                              refreshHistory()
                            }}
                          >
                            ×
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>

                <div className="nav-row">
                  <span />
                  <button
                    type="button"
                    className="btn btn-gold"
                    disabled={editSelected.length < 2 || editBusy}
                    onClick={async () => {
                      setEditBusy(true)
                      setError(null)
                      try {
                        const res = await api.concatVideos(editSelected)
                        await refreshHistory()
                        setEditTarget(res.name)
                        setPreviewSrc(res.preview_url)
                        setEditSelected([])
                        setEditStart(0)
                        setEditEnd(res.duration)
                      } catch (e: unknown) {
                        setError(e instanceof Error ? e.message : 'Montage échoué')
                      } finally {
                        setEditBusy(false)
                      }
                    }}
                  >
                    {editBusy ? 'Montage…' : 'Assembler'}
                  </button>
                </div>
                {error && <p className="error">{error}</p>}
              </section>
            )}

            {page === 'library' && (
              <section className="panel step-panel">
                <div className="bg-tabs">
                  {(
                    [
                      ['browse', 'Bibliothèque'],
                      ['search', 'Recherche Pexels'],
                      ['upload', 'Upload'],
                    ] as const
                  ).map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      className={`bg-tab ${libTab === id ? 'active' : ''}`}
                      onClick={() => setLibTab(id)}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className="bg-body">
                  {libTab === 'browse' && (
                    <>
                      <p className="hint tight">
                        {allFonds.length} fond{allFonds.length > 1 ? 's' : ''} —
                        assets {libraryAssets.length}, uploads {uploads.length}, Pexels/URL {urlFonds.length}
                      </p>
                      <div className="lib-grid large">
                        {allFonds.map((b) => (
                          <div
                            key={b.id}
                            className={`lib-card static ${montageIds[0] === b.id ? 'selected' : ''}`}
                          >
                            {b.thumb_url ? <img src={b.thumb_url} alt="" /> : <div className="lib-ph" />}
                            <span>
                              {b.name}
                              {b.duration ? ` · ${Math.round(b.duration)}s` : ''}
                              {' · '}
                              {b.source === 'url' ? 'Pexels/URL' : b.source === 'upload' ? 'Upload' : 'Asset'}
                            </span>
                            <div className="lib-actions">
                              <button
                                type="button"
                                className="btn btn-gold tiny"
                                onClick={() => useAsBackground(b.id)}
                              >
                                Utiliser
                              </button>
                              {(b.source === 'upload' || b.source === 'url') && (
                                <button
                                  type="button"
                                  className="btn btn-ghost tiny"
                                  onClick={async () => {
                                    await api.deleteBackground(b.id)
                                    setMontageIds((prev) => prev.filter((x) => x !== b.id))
                                    if (backgroundId === b.id) setBackgroundId('')
                                    refreshBackgrounds()
                                  }}
                                >
                                  Suppr.
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                      {!allFonds.length && (
                        <p className="empty-line">Bibliothèque vide — recherche Pexels ou upload.</p>
                      )}
                    </>
                  )}

                  {libTab === 'search' && (
                    <>
                      <div className="search-row">
                        <input
                          type="text"
                          value={pexelsQuery}
                          onChange={(e) => setPexelsQuery(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && runPexelsSearch()}
                          placeholder="nature, ocean, mosque…"
                        />
                        <button
                          type="button"
                          className="btn btn-primary"
                          disabled={pexelsBusy}
                          onClick={runPexelsSearch}
                        >
                          {pexelsBusy ? '…' : 'OK'}
                        </button>
                      </div>
                      {pexelsMsg && <p className="hint tight">{pexelsMsg}</p>}
                      <div className="lib-grid large">
                        {pexelsVideos.map((v) => (
                          <div key={v.id} className="lib-card static">
                            <img src={v.preview} alt="" />
                            <span>
                              {v.user}
                              {v.duration ? ` · ${v.duration}s` : ''}
                            </span>
                            <div className="lib-actions">
                              <button
                                type="button"
                                className="btn btn-primary tiny"
                                disabled={importingId === v.id}
                                onClick={() => addPexelsToLibrary(v)}
                              >
                                {importingId === v.id ? 'Ajout…' : 'Ajouter'}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="url-import" style={{ marginTop: '0.85rem' }}>
                        <label className="field">
                          Ou coller une URL .mp4
                          <div className="search-row">
                            <input
                              type="text"
                              placeholder="https://…/video.mp4"
                              value={backgroundUrl}
                              onChange={(e) => setBackgroundUrl(e.target.value)}
                            />
                            <button
                              type="button"
                              className="btn btn-primary"
                              disabled={!backgroundUrl.trim() || importingId === 'url'}
                              onClick={async () => {
                                setImportingId('url')
                                setError(null)
                                try {
                                  await api.importBackground(backgroundUrl.trim())
                                  setBackgroundUrl('')
                                  await refreshBackgrounds()
                                  setLibTab('browse')
                                } catch (e: unknown) {
                                  setError(e instanceof Error ? e.message : 'Import échoué')
                                } finally {
                                  setImportingId(null)
                                }
                              }}
                            >
                              Ajouter
                            </button>
                          </div>
                        </label>
                      </div>
                    </>
                  )}

                  {libTab === 'upload' && (
                    <div className="upload-zone">
                      <input
                        type="file"
                        accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm"
                        multiple
                        onChange={async (e) => {
                          const files = Array.from(e.target.files || [])
                          if (!files.length) return
                          setError(null)
                          try {
                            for (const f of files) {
                              await api.upload(f)
                            }
                            await refreshBackgrounds()
                            setLibTab('browse')
                          } catch (err: unknown) {
                            setError(err instanceof Error ? err.message : 'Upload échoué')
                          }
                        }}
                      />
                      <p className="hint tight">Les fichiers sont ajoutés à la bibliothèque.</p>
                    </div>
                  )}
                </div>
                {error && <p className="error">{error}</p>}
              </section>
            )}

            {page === 'audio' && (
              <section className="panel step-panel">
                <p className="hint tight">
                  MP3 déjà téléchargés, classés par récitateur puis sourate.
                </p>
                {!audioGroups.length && (
                  <p className="empty-line">Aucun son en cache — génère une vidéo pour en télécharger.</p>
                )}
                <div className="audio-groups">
                  {audioGroups.map((g) => (
                    <div key={g.dossier} className="audio-group">
                      <button
                        type="button"
                        className={`audio-group-head ${audioOpen === g.dossier ? 'open' : ''}`}
                        onClick={() =>
                          setAudioOpen((prev) => (prev === g.dossier ? null : g.dossier))
                        }
                      >
                        <strong>{g.nom}</strong>
                        <span>
                          {g.file_count} fichier{g.file_count > 1 ? 's' : ''} ·{' '}
                          {(g.total_bytes / (1024 * 1024)).toFixed(1)} Mo · {g.surahs.length}{' '}
                          sourate{g.surahs.length > 1 ? 's' : ''}
                        </span>
                      </button>
                      {audioOpen === g.dossier && (
                        <div className="audio-group-body">
                          {g.surahs.map((s) => (
                            <div key={s.surah} className="audio-surah">
                              <p className="audio-surah-title">
                                {s.surah}. {s.name_fr}
                                {s.name_ar ? ` — ${s.name_ar}` : ''}
                              </p>
                              <div className="audio-files">
                                {s.files.map((f) => (
                                  <div key={f.name} className="audio-file">
                                    <span>
                                      {f.kind === 'full'
                                        ? 'Sourate complète'
                                        : f.kind === 'basmala'
                                          ? 'Basmala'
                                          : `Verset ${f.ayah}`}
                                      {f.duration != null ? ` · ${f.duration}s` : ''}
                                    </span>
                                    <button
                                      type="button"
                                      className="btn btn-ghost tiny"
                                      onClick={() => playCachedAudio(f.play_url)}
                                    >
                                      {audioPlayingUrl === f.play_url ? 'Pause' : 'Écouter'}
                                    </button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

          </div>

          {showPreview && (
          <aside className="dash-preview">
            <div className="preview-sticky">
              <h2 className="preview-title">Aperçu</h2>
              <div className="phone">
                {previewSrc || job?.status === 'done' ? (
                  <video
                    key={previewSrc || job?.id}
                    className="phone-video"
                    src={previewSrc || (job ? api.previewUrl(job.id) : undefined)}
                    controls
                    playsInline
                    autoPlay
                  />
                ) : (
                  <div className="phone-placeholder">
                    {(job?.status === 'queued' || job?.status === 'running') && (
                      <>
                        <div className="progress-bar">
                          <i style={{ width: `${job.progress}%` }} />
                        </div>
                        <p>
                          {job.message}
                          <br />
                          <strong>{job.progress}%</strong>
                        </p>
                      </>
                    )}
                    {job?.status === 'failed' && (
                      <p className="error" style={{ margin: '0.5rem' }}>
                        {job.error || 'Échec'}
                      </p>
                    )}
                    {!job && page === 'create' && (
                      <>
                        <img src="/nur-logo.png" alt="" className="phone-wm-logo" />
                        <p className="phone-brand">Nur</p>
                        <p
                          className="phone-sample"
                          style={{
                            color: selectedSub?.preview.color ?? '#fff',
                            textShadow: `0 1px 3px ${selectedSub?.preview.outline ?? '#000'}`,
                            fontSize: `${Math.max(14, fontSize * 0.7)}px`,
                          }}
                        >
                          {SAMPLE_AR}
                        </p>
                        {translation !== 'none' && (
                          <p className="phone-tr">
                            {translation === 'fr'
                              ? 'Traduction française…'
                              : 'English translation…'}
                          </p>
                        )}
                        {showCredits && (
                          <div className="phone-credits">
                            <p>{creditLine1}</p>
                            <p>{selectedReciter?.nom}</p>
                          </div>
                        )}
                        <p className="phone-hint">{bgLabel}</p>
                      </>
                    )}
                    {!job && page === 'history' && (
                      <p className="phone-hint">Sélectionne une vidéo</p>
                    )}
                  </div>
                )}
              </div>

              {job?.status === 'done' && (
                <div className="preview-actions">
                  <a className="btn btn-gold" href={api.downloadUrl(job.id)} download>
                    Télécharger
                  </a>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={async () => {
                      await refreshHistory()
                      if (job.output_name) {
                        setEditTarget(job.output_name)
                        setPreviewSrc(api.previewUrl(job.id))
                        setEditStart(0)
                        setEditEnd(0)
                      }
                      setPage('history')
                    }}
                  >
                    Éditer
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => {
                      setJob(null)
                      setStep(0)
                      setPage('create')
                    }}
                  >
                    Nouvelle
                  </button>
                </div>
              )}
              {job?.status === 'failed' && (
                <button type="button" className="btn btn-ghost" onClick={() => setJob(null)}>
                  Réessayer
                </button>
              )}
            </div>
          </aside>
          )}
        </div>
      </main>
    </div>
  )
}
