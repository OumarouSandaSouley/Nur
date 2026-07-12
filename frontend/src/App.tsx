import { useEffect, useMemo, useState } from 'react'
import {
  api,
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

const STEPS = ['Contenu', 'Sous-titres', 'Vidéo', 'Générer', 'Éditer'] as const
const SAMPLE_AR = 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ'

export default function App() {
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
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
  const [watermarkMode, setWatermarkMode] = useState<'none' | 'logo' | 'text'>('none')
  const [watermarkText, setWatermarkText] = useState('')

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
  const library = backgrounds.filter((b) => b.source === 'library')
  const availableSurahs = useMemo(() => {
    if (selectedReciter?.surahs?.length) {
      const allow = new Set(selectedReciter.surahs)
      return surahs.filter((s) => allow.has(s.number))
    }
    return surahs
  }, [surahs, selectedReciter])

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

  useEffect(() => {
    if (step === 4 || job?.status === 'done') refreshHistory()
  }, [step, job?.status])

  useEffect(() => {
    Promise.all([api.reciters(), api.surahs(), api.styles(), api.backgrounds()])
      .then(([r, s, st, b]) => {
        setReciters(r)
        setSurahs(s)
        setSubStyles(st.subtitles)
        setSubAnims(st.anims || [])
        setVideoStyles(st.video)
        setBackgrounds(b)
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
      form.append('watermark_mode', watermarkMode)
      if (watermarkMode === 'text' && watermarkText.trim()) {
        form.append('watermark_text', watermarkText.trim())
      }

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
      <div className="app shell">
        <p className="loading">Chargement du studio…</p>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="app shell">
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

  function moveMontage(index: number, dir: -1 | 1) {
    setMontageIds((prev) => {
      const next = [...prev]
      const j = index + dir
      if (j < 0 || j >= next.length) return prev
      ;[next[index], next[j]] = [next[j], next[index]]
      return next
    })
  }

  return (
    <div className="app shell">
      <header className="hero compact">
        <div className="brand-row">
          <img src="/nur-logo.png" alt="Nur" className="brand-logo" width={40} height={40} />
          <div className="brand-text">
            <h1 className="brand">
              Nur<span>.</span>
            </h1>
            <p className="tagline">Studio video coranique</p>
          </div>
        </div>
      </header>

      <nav className="steps" aria-label="Étapes">
        {STEPS.map((label, i) => (
          <button
            key={label}
            type="button"
            className={`step-pill ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}
            onClick={() => setStep(i)}
          >
            {i + 1}. {label}
          </button>
        ))}
      </nav>

      <div className="layout">
        <div className="col-left">
          {step === 0 && (
            <section className="panel step-panel">
              <h2>Contenu</h2>
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
                    a.play().then(() => setAudioPlaying(true)).catch(() => setAudioPlaying(false))
                    setAudioPreview(a)
                  }}
                >
                  {audioPlaying ? 'Pause apercu' : 'Ecouter un verset'}
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
                    <option value="fr">Arabe + Francais</option>
                    <option value="en">Arabe + Anglais</option>
                  </select>
                </label>
                {estimate && (
                  <p className="estimate-chip">
                    Duree {estimatePrecise ? '' : '~'}
                    <strong>{estimate}</strong>
                    {!estimatePrecise && <span> (approx.)</span>}
                  </p>
                )}
              </div>
              <div className="nav-row">
                <span />
                <button type="button" className="btn btn-primary" onClick={() => setStep(1)}>
                  Continuer
                </button>
              </div>
            </section>
          )}

          {step === 1 && (
            <section className="panel step-panel">
              <h2>Sous-titres</h2>
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
              <div className="nav-row">
                <button type="button" className="btn btn-ghost" onClick={() => setStep(0)}>
                  Retour
                </button>
                <button type="button" className="btn btn-primary" onClick={() => setStep(2)}>
                  Continuer
                </button>
              </div>
            </section>
          )}

          {step === 2 && (
            <section className="panel step-panel">
              <h2>Vidéo & fond</h2>

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

              <div className="bg-tabs" style={{ marginTop: '0.9rem' }}>
                {(
                  [
                    ['search', 'Recherche'],
                    ['url', 'URL'],
                    ['upload', 'Upload'],
                    ['library', 'Bibliothèque'],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    className={`bg-tab ${bgMode === id ? 'active' : ''}`}
                    onClick={() => setBgMode(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <div className="bg-body">
                {bgMode === 'url' && (
                  <label className="field">
                    URL directe .mp4
                    <input
                      type="text"
                      placeholder="https://…/video.mp4"
                      value={backgroundUrl}
                      onChange={(e) => {
                        setBackgroundUrl(e.target.value)
                        setBackgroundId('')
                        setSelectedPexelsUrl('')
                        setBgFile(null)
                      }}
                    />
                  </label>
                )}

                {bgMode === 'search' && (
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
                    <div className="pexels-grid">
                      {pexelsVideos.map((v) => (
                        <button
                          key={v.id}
                          type="button"
                          className={`pexels-card ${selectedPexelsUrl === v.url ? 'selected' : ''}`}
                          onClick={() => {
                            setSelectedPexelsUrl(v.url)
                            setBackgroundUrl('')
                            setBackgroundId('')
                            setBgFile(null)
                          }}
                        >
                          <img src={v.preview} alt="" />
                          <span>
                            {v.user}
                            {v.duration ? ` · ${v.duration}s` : ''}
                          </span>
                        </button>
                      ))}
                    </div>
                  </>
                )}

                {bgMode === 'upload' && (
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
                          const ids: string[] = []
                          for (const f of files) {
                            const saved = await api.upload(f)
                            ids.push(saved.id)
                          }
                          await refreshBackgrounds()
                          setMontageIds((prev) => [...prev, ...ids].slice(0, 6))
                          setBackgroundId(ids[ids.length - 1] || '')
                          setBgMode('library')
                          setBgFile(null)
                          setBackgroundUrl('')
                          setSelectedPexelsUrl('')
                        } catch (err: unknown) {
                          setError(err instanceof Error ? err.message : 'Upload échoué')
                        }
                      }}
                    />
                  </div>
                )}

                {bgMode === 'library' && (
                  <>
                    {montageIds.length > 0 && (
                      <div className="montage-bar">
                        <p className="field-label">
                          Montage ({montageIds.length}/6)
                        </p>
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
                                  aria-label="Monter"
                                >
                                  ↑
                                </button>
                                <button
                                  type="button"
                                  className="btn btn-ghost tiny"
                                  disabled={i === montageIds.length - 1}
                                  onClick={() => moveMontage(i, 1)}
                                  aria-label="Descendre"
                                >
                                  ↓
                                </button>
                                <button
                                  type="button"
                                  className="btn btn-ghost tiny"
                                  onClick={() =>
                                    setMontageIds((prev) => prev.filter((_, j) => j !== i))
                                  }
                                  aria-label="Retirer"
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
                      {[...uploads, ...library].map((b) => (
                        <button
                          key={b.id}
                          type="button"
                          className={`lib-card ${montageIds.includes(b.id) || backgroundId === b.id ? 'selected' : ''}`}
                          onClick={() => toggleMontage(b.id)}
                        >
                          {b.thumb_url ? (
                            <img src={b.thumb_url} alt="" />
                          ) : (
                            <div className="lib-ph" />
                          )}
                          <span>
                            {b.name}
                            {b.duration ? ` · ${Math.round(b.duration)}s` : ''}
                            {montageIds.includes(b.id)
                              ? ` · #${montageIds.indexOf(b.id) + 1}`
                              : ''}
                          </span>
                          {b.source === 'upload' && (
                            <em
                              role="button"
                              tabIndex={0}
                              onClick={async (e) => {
                                e.stopPropagation()
                                await api.deleteBackground(b.id)
                                setMontageIds((prev) => prev.filter((x) => x !== b.id))
                                if (backgroundId === b.id) setBackgroundId('')
                                refreshBackgrounds()
                              }}
                            >
                              x
                            </em>
                          )}
                        </button>
                      ))}
                    </div>
                    {!uploads.length && !library.length && (
                      <p className="empty-line">Aucune video</p>
                    )}
                  </>
                )}
              </div>

              <div className="nav-row">
                <button type="button" className="btn btn-ghost" onClick={() => setStep(1)}>
                  Retour
                </button>
                <button type="button" className="btn btn-primary" onClick={() => setStep(3)}>
                  Continuer
                </button>
              </div>
            </section>
          )}

          {step === 3 && (
            <section className="panel step-panel">
              <h2>Générer</h2>
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
                  <span>
                    {watermarkMode === 'none'
                      ? 'Aucun'
                      : watermarkMode === 'logo'
                        ? 'Logo Nur'
                        : watermarkText.trim()
                          ? `@${watermarkText.replace(/^@/, '')}`
                          : 'Texte'}
                  </span>
                </li>
              </ul>

              <div className="watermark-box">
                <p className="field-label">Watermark</p>
                <div className="wm-tabs">
                  {(
                    [
                      ['none', 'Aucun'],
                      ['logo', 'Logo'],
                      ['text', 'Pseudo'],
                    ] as const
                  ).map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      className={`bg-tab ${watermarkMode === id ? 'active' : ''}`}
                      onClick={() => setWatermarkMode(id)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {watermarkMode === 'text' && (
                  <label className="field">
                    Pseudo TikTok
                    <input
                      type="text"
                      placeholder="@toncompte"
                      value={watermarkText}
                      onChange={(e) => setWatermarkText(e.target.value)}
                      maxLength={40}
                    />
                  </label>
                )}
              </div>

              <div className="nav-row">
                <button type="button" className="btn btn-ghost" onClick={() => setStep(2)}>
                  Retour
                </button>
                <button
                  type="button"
                  className="btn btn-gold"
                  disabled={busy || job?.status === 'running' || job?.status === 'queued'}
                  onClick={startGeneration}
                >
                  {busy ? 'Lancement…' : 'Générer'}
                </button>
              </div>
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

          {step === 4 && (
            <section className="panel step-panel">
              <h2>Éditer</h2>

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
                <button type="button" className="btn btn-ghost" onClick={() => setStep(3)}>
                  Retour
                </button>
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
        </div>

        <aside className="col-right">
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
                  {!job && (
                    <>
                      {watermarkMode === 'logo' && (
                        <img
                          src="/nur-logo.png"
                          alt=""
                          className="phone-wm-logo"
                        />
                      )}
                      {watermarkMode === 'text' && watermarkText.trim() && (
                        <span className="phone-wm-text">
                          @{watermarkText.replace(/^@/, '')}
                        </span>
                      )}
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
                      <p className="phone-hint">
                        {step + 1}/{STEPS.length} · {bgLabel}
                      </p>
                    </>
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
                    setStep(4)
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
      </div>
    </div>
  )
}
