import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'

import { ApiError, importLecture, listCategories } from '../../lib/api'
import { navigateTo } from '../../lib/navigation'
import type { Category } from '../../types/lecture'
import { Card, CardContent } from '../ui/card'
import { Icon } from '../ui/icon'
import { Input } from '../ui/input'

const MAX_FILES = 10
const MAX_FILE_BYTES = 200 * 1024 * 1024
const ACCEPT_TYPES = '.mp3,.m4a,.wav,.webm,.ogg,.opus,audio/mpeg,audio/mp4,audio/wav,audio/webm,audio/ogg'

type ImportAudioModalProps = {
  onClose: () => void
}

type Entry = {
  id: string
  file: File
  duration: number | null
  durationError: string | null
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(seconds: number | null) {
  if (seconds === null) return '—'
  const total = Math.round(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, '0')}min`
  }
  return `${minutes}min ${String(secs).padStart(2, '0')}s`
}

async function detectDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const audio = document.createElement('audio')
    audio.preload = 'metadata'
    audio.src = url
    audio.addEventListener('loadedmetadata', () => {
      URL.revokeObjectURL(url)
      if (Number.isFinite(audio.duration) && audio.duration > 0) {
        resolve(audio.duration)
      } else {
        reject(new Error('invalid duration'))
      }
    })
    audio.addEventListener('error', () => {
      URL.revokeObjectURL(url)
      reject(new Error('failed to read audio'))
    })
  })
}

export function ImportAudioModal({ onClose }: ImportAudioModalProps) {
  const [categories, setCategories] = useState<Category[]>([])
  const [isLoadingCategories, setIsLoadingCategories] = useState(true)
  const [title, setTitle] = useState('')
  const [categoryId, setCategoryId] = useState<string | null>(null)
  const [entries, setEntries] = useState<Entry[]>([])
  const [titleError, setTitleError] = useState<string | undefined>()
  const [categoryError, setCategoryError] = useState<string | undefined>()
  const [filesError, setFilesError] = useState<string | undefined>()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const entryCounterRef = useRef(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    async function load() {
      try {
        const data = await listCategories()
        setCategories(data)
      } catch {
        setCategories([])
      } finally {
        setIsLoadingCategories(false)
      }
    }
    void load()
  }, [])

  async function appendFiles(filesToAdd: FileList | File[]) {
    const list = Array.from(filesToAdd)
    const accepted: Entry[] = []
    const errors: string[] = []
    for (const file of list) {
      if (file.size > MAX_FILE_BYTES) {
        errors.push(`${file.name} excede o limite de 200 MB.`)
        continue
      }
      const entry: Entry = {
        id: `e${++entryCounterRef.current}`,
        file,
        duration: null,
        durationError: null,
      }
      accepted.push(entry)
    }

    setEntries((prev) => {
      const next = [...prev, ...accepted]
      if (next.length > MAX_FILES) {
        errors.push(`Máximo de ${MAX_FILES} arquivos por aula.`)
        return next.slice(0, MAX_FILES)
      }
      return next
    })

    if (errors.length) setFilesError(errors.join(' '))
    else setFilesError(undefined)

    // detecta duração em paralelo
    for (const entry of accepted) {
      detectDuration(entry.file)
        .then((duration) => {
          setEntries((prev) => prev.map((e) => (e.id === entry.id ? { ...e, duration } : e)))
        })
        .catch(() => {
          setEntries((prev) =>
            prev.map((e) =>
              e.id === entry.id
                ? { ...e, durationError: 'Não foi possível ler a duração do arquivo.' }
                : e,
            ),
          )
        })
    }
  }

  function handleFilesPicked(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files && event.target.files.length > 0) {
      void appendFiles(event.target.files)
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function removeEntry(id: string) {
    setEntries((prev) => prev.filter((e) => e.id !== id))
  }

  function move(id: string, direction: -1 | 1) {
    setEntries((prev) => {
      const idx = prev.findIndex((e) => e.id === id)
      if (idx === -1) return prev
      const newIdx = idx + direction
      if (newIdx < 0 || newIdx >= prev.length) return prev
      const next = [...prev]
      const [item] = next.splice(idx, 1)
      next.splice(newIdx, 0, item)
      return next
    })
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedTitle = title.trim()
    let hasError = false
    if (!trimmedTitle) {
      setTitleError('Informe um título para a aula.')
      hasError = true
    } else {
      setTitleError(undefined)
    }
    if (!categoryId) {
      setCategoryError('Selecione uma matéria.')
      hasError = true
    } else {
      setCategoryError(undefined)
    }
    if (entries.length === 0) {
      setFilesError('Selecione pelo menos um arquivo de áudio.')
      hasError = true
    }
    if (entries.some((e) => e.duration === null || e.durationError)) {
      setFilesError('Aguarde a leitura das durações ou remova arquivos com erro.')
      hasError = true
    }
    if (hasError) return

    setIsSubmitting(true)
    try {
      const lecture = await importLecture(
        trimmedTitle,
        categoryId,
        entries.map((e) => ({ file: e.file, duration: e.duration as number })),
      )
      navigateTo(`/lectures/${lecture.id}`)
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'validation') {
        setFilesError(error.message)
      }
      setIsSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <Card style={{ maxWidth: 640, width: '100%', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 12,
            padding: '20px 22px 8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              aria-hidden="true"
              className="avatar avatar-blue"
              style={{ width: 40, height: 40, borderRadius: 10 }}
            >
              <Icon name="upload" size={18} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Importar áudio</h2>
              <p style={{ margin: '4px 0 0', fontSize: 12.5, color: 'var(--ink-4)' }}>
                Suba até {MAX_FILES} áudios da aula em ordem. Limite de 200 MB por arquivo.
              </p>
            </div>
          </div>
          <button aria-label="Fechar modal" className="icon-btn" onClick={onClose} type="button">
            <Icon name="x" size={16} />
          </button>
        </div>

        <CardContent style={{ overflowY: 'auto', flex: 1, padding: '8px 22px 0' }}>
          <form onSubmit={handleSubmit} id="import-audio-form" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Input
              autoFocus
              error={titleError}
              icon="fileText"
              label="Título da aula"
              onChange={(event) => {
                setTitle(event.target.value)
                setTitleError(undefined)
              }}
              placeholder="Ex.: Aula 03 — Derivadas"
              value={title}
            />

            <div>
              <span style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: 'var(--ink-2)', marginBottom: 6 }}>
                Matéria
              </span>
              {isLoadingCategories ? (
                <p style={{ fontSize: 13, color: 'var(--ink-4)' }}>Buscando matérias...</p>
              ) : categories.length === 0 ? (
                <p style={{ fontSize: 13, color: 'var(--ink-4)' }}>
                  Nenhuma matéria cadastrada. Crie uma em <strong>Matérias</strong> antes de importar.
                </p>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {categories.map((category) => {
                    const selected = category.id === categoryId
                    return (
                      <button
                        className={selected ? 'tab active' : 'tab'}
                        key={category.id}
                        onClick={() => {
                          setCategoryId(category.id)
                          setCategoryError(undefined)
                        }}
                        style={{ flexShrink: 0 }}
                        type="button"
                      >
                        {category.name}
                      </button>
                    )
                  })}
                </div>
              )}
              {categoryError ? (
                <span style={{ display: 'block', marginTop: 6, fontSize: 12, color: 'var(--danger)' }}>
                  {categoryError}
                </span>
              ) : null}
            </div>

            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: 6,
                }}
              >
                <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink-2)' }}>
                  Arquivos de áudio ({entries.length}/{MAX_FILES})
                </span>
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={entries.length >= MAX_FILES}
                  onClick={() => fileInputRef.current?.click()}
                  type="button"
                >
                  <Icon name="plus" size={12} />
                  <span>Adicionar arquivos</span>
                </button>
                <input
                  accept={ACCEPT_TYPES}
                  multiple
                  onChange={handleFilesPicked}
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  type="file"
                />
              </div>

              {entries.length === 0 ? (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    border: '1.5px dashed var(--line)',
                    borderRadius: 12,
                    padding: '22px 18px',
                    textAlign: 'center',
                    fontSize: 13,
                    color: 'var(--ink-4)',
                    cursor: 'pointer',
                  }}
                >
                  <Icon name="upload" size={18} />
                  <p style={{ margin: '6px 0 0' }}>Clique para selecionar áudios da aula</p>
                  <p style={{ margin: '4px 0 0', fontSize: 11.5 }}>
                    mp3, m4a, wav, webm, ogg, opus · até 200 MB cada
                  </p>
                </div>
              ) : (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    border: '1px solid var(--line)',
                    borderRadius: 12,
                    overflow: 'hidden',
                  }}
                >
                  {entries.map((entry, index) => (
                    <div
                      key={entry.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        padding: '12px 14px',
                        borderBottom: index === entries.length - 1 ? 'none' : '1px solid var(--line)',
                      }}
                    >
                      <div
                        aria-hidden="true"
                        style={{
                          width: 28,
                          height: 28,
                          borderRadius: 8,
                          background: 'var(--accent-softer)',
                          color: 'var(--accent)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 12,
                          fontWeight: 700,
                          flexShrink: 0,
                        }}
                      >
                        {index + 1}
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div
                          style={{
                            fontSize: 13.5,
                            fontWeight: 600,
                            color: 'var(--ink)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                          title={entry.file.name}
                        >
                          {entry.file.name}
                        </div>
                        <div style={{ fontSize: 11.5, color: 'var(--ink-4)', marginTop: 2 }}>
                          {entry.durationError ?? `${formatBytes(entry.file.size)} · ${formatDuration(entry.duration)}`}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
                        <button
                          aria-label="Mover para cima"
                          className="icon-btn"
                          disabled={index === 0}
                          onClick={() => move(entry.id, -1)}
                          type="button"
                        >
                          <Icon name="arrowUp" size={13} />
                        </button>
                        <button
                          aria-label="Mover para baixo"
                          className="icon-btn"
                          disabled={index === entries.length - 1}
                          onClick={() => move(entry.id, 1)}
                          type="button"
                        >
                          <Icon name="arrowDown" size={13} />
                        </button>
                        <button
                          aria-label="Remover"
                          className="icon-btn danger"
                          onClick={() => removeEntry(entry.id)}
                          type="button"
                        >
                          <Icon name="trash" size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {filesError ? (
                <span style={{ display: 'block', marginTop: 6, fontSize: 12, color: 'var(--danger)' }}>
                  {filesError}
                </span>
              ) : null}
            </div>
          </form>
        </CardContent>

        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 8,
            padding: '14px 22px 18px',
            borderTop: '1px solid var(--line)',
          }}
        >
          <button className="btn btn-ghost" disabled={isSubmitting} onClick={onClose} type="button">
            Cancelar
          </button>
          <button
            className="btn btn-primary"
            disabled={isSubmitting || isLoadingCategories || categories.length === 0 || entries.length === 0}
            form="import-audio-form"
            type="submit"
          >
            <Icon name="upload" size={14} />
            <span>{isSubmitting ? 'Enviando...' : 'Importar e processar'}</span>
          </button>
        </div>
      </Card>
    </div>
  )
}
