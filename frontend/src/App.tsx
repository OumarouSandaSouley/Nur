import { useEffect, useMemo, useState } from 'react'
import {
  api,
  type Background,
  type Job,
  type PexelsVideo,
  type Reciter,
  type SubtitleStyle,
  type Surah,
  type VideoStyle,
} from './api'

const STEPS = ['Contenu', 'Sous-titres', 'Vidéo', 'Générer'] as const
const SAMPLE_AR = 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ'

export default function App() {
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [step, setStep] = useState(0)

  const [reciters, setReciters] = useState<Reciter[]>([])
  const [surahs, setSurahs] = useState<Surah[]>([])
  const [subStyles, setSubStyles] = useState<SubtitleStyle[]>([])
  const [videoStyles, setVideoStyles] = useState<VideoStyle[]>([])
  const [backgrounds, setBackgrounds] = useState<Background[]>([])

  const [reciterId, setReciterId] = useState(3)
  const [surah, setSurah] = useState(1)
  const [ayahFrom, setAyahFrom] = useState(1)
  const [ayahTo, setAyahTo] = useState(7)
  const [includeBasmala, setIncludeBasmala] = useState(true)
  const [translation, setTranslation] = useState<'none' | 'fr' | 'en'>('none')
  const [subtitleStyle, setSubtitleStyle] = useState('classic')
  const [videoStyle, setVideoStyle] = useState('clean')

  const [bgMode, setBgMode] = useState<'url' | 'search' | 'upload' | 'library'>('search')
  const [backgroundUrl, setBackgroundUrl] = useState('')
  const [backgroundId, setBackgroundId] = useState('')
  const [bgFile, setBgFile] = useState<File | null>(null)
  const [pexelsQuery, setPexelsQuery] = useState('nature')
  const [pexelsVideos, setPexelsVideos] = useState<PexelsVideo[]>([])
  const [pexelsMsg, setPexelsMsg] = useState('')
  const [pexelsBusy, setPexelsBusy] = useState(false)
  const [selectedPexelsUrl, setSelectedPexelsUrl] = useState('')

  const [job, setJob] = useState<Job | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [estimate, setEstimate] = useState<string | null>(null)
  const [estimatePrecise, setEstimatePrecise] = useState(false)

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

  async function refreshBackgrounds() {
    setBackgrounds(await api.backgrounds())
  }

  useEffect(() => {
    Promise.all([api.reciters(), api.surahs(), api.styles(), api.backgrounds()])
      .then(([r, s, st, b]) => {
        setReciters(r)
        setSurahs(s)
        setSubStyles(st.subtitles)
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
    if (!job || job.status === 'done' || job.status === 'failed') return
    const t = setInterval(() => {
      api.job(job.id).then(setJob).catch(() => undefined)
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

  async function onUpload(file: File | null) {
    if (!file) return
    setError(null)
    try {
      const saved = await api.upload(file)
      await refreshBackgrounds()
      setBackgroundId(saved.id)
      setBgMode('library')
      setBgFile(null)
      setBackgroundUrl('')
      setSelectedPexelsUrl('')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload échoué')
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
      form.append('video_style', videoStyle)
      form.append('include_basmala', String(includeBasmala))
      form.append('translation', translation)

      if (bgMode === 'url' && backgroundUrl.trim()) {
        form.append('background_url', backgroundUrl.trim())
      } else if (bgMode === 'search' && selectedPexelsUrl) {
        form.append('background_url', selectedPexelsUrl)
      } else if (bgFile) {
        form.append('background', bgFile)
      } else if (backgroundId) {
        form.append('background_id', backgroundId)
      }

      const created = await api.createJob(form)
      setJob(created)
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
    bgMode === 'url' && backgroundUrl
      ? 'URL personnalisée'
      : bgMode === 'search' && selectedPexelsUrl
        ? 'Pexels sélectionné'
        : bgFile?.name ||
          backgrounds.find((b) => b.id === backgroundId)?.name ||
          'Fond uni auto'

  return (
    <div className="app shell">
      <header className="hero compact">
        <div className="brand-row">
          <img src="/nur-logo.png" alt="" className="brand-logo" width={40} height={40} />
          <h1 className="brand">
            Nur<span>.</span>
          </h1>
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
              <p className="hint">Récitateur, sourate et intervalle de versets.</p>
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
                <label className="field">
                  Sourate
                  <select value={surah} onChange={(e) => setSurah(Number(e.target.value))}>
                    {surahs.map((s) => (
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
              <p className="hint">Style du texte arabe (versets longs auto-adaptés).</p>
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
              <p className="hint">Style de rendu, puis source du fond.</p>

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
                      onChange={(e) => onUpload(e.target.files?.[0] ?? null)}
                    />
                  </div>
                )}

                {bgMode === 'library' && (
                  <>
                    <label className="field">
                      Uploads
                      <select
                        value={backgroundId.startsWith('upload:') ? backgroundId : ''}
                        onChange={(e) => {
                          setBackgroundId(e.target.value)
                          setBgFile(null)
                          setBackgroundUrl('')
                          setSelectedPexelsUrl('')
                        }}
                      >
                        <option value="">— Aucun —</option>
                        {uploads.map((b) => (
                          <option key={b.id} value={b.id}>
                            {b.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      assets/fonds
                      <select
                        value={backgroundId.startsWith('asset:') ? backgroundId : ''}
                        onChange={(e) => {
                          setBackgroundId(e.target.value)
                          setBgFile(null)
                          setBackgroundUrl('')
                          setSelectedPexelsUrl('')
                        }}
                      >
                        <option value="">— Aucun —</option>
                        {library.map((b) => (
                          <option key={b.id} value={b.id}>
                            {b.name}
                          </option>
                        ))}
                      </select>
                    </label>
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
              <p className="hint">Vérifie puis lance — l’aperçu s’affiche à droite.</p>
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
                  <span>{selectedSub?.name}</span>
                </li>
                <li>
                  <span>Style</span>
                  <span>{selectedVid?.name}</span>
                </li>
                <li>
                  <span>Fond</span>
                  <span>{bgLabel}</span>
                </li>
              </ul>
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
            </section>
          )}
        </div>

        <aside className="col-right">
          <div className="preview-sticky">
            <h2 className="preview-title">Aperçu</h2>
            <div className="phone">
              {job?.status === 'done' ? (
                <video
                  key={job.id}
                  className="phone-video"
                  src={api.previewUrl(job.id)}
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
                      <p className="phone-brand">Nur</p>
                      <p
                        className="phone-sample"
                        style={{
                          color: selectedSub?.preview.color ?? '#fff',
                          textShadow: `0 1px 3px ${selectedSub?.preview.outline ?? '#000'}`,
                        }}
                      >
                        {SAMPLE_AR}
                      </p>
                      <p className="phone-hint">Étape {step + 1}/4</p>
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
                  className="btn btn-ghost"
                  onClick={() => {
                    setJob(null)
                    setStep(0)
                  }}
                >
                  Nouvelle vidéo
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
