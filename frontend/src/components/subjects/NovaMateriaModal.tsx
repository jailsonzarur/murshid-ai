import { useRef, useState, type ChangeEvent, type FormEvent } from 'react'

import { ApiError, createSubject } from '../../lib/api'
import { Card, CardContent } from '../ui/card'
import { Icon } from '../ui/icon'
import { Input } from '../ui/input'

const MAX_FILES = 10
const MAX_FILE_BYTES = 50 * 1024 * 1024
const ACCEPT_TYPES = '.pdf,.txt,.md,application/pdf,text/plain,text/markdown'

type NovaMateriaModalProps = {
  onClose: () => void
  onCreated: () => void
}

type Entry = {
  id: string
  file: File
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function NovaMateriaModal({ onClose, onCreated }: NovaMateriaModalProps) {
  const [name, setName] = useState('')
  const [entries, setEntries] = useState<Entry[]>([])
  const [nameError, setNameError] = useState<string | undefined>()
  const [filesError, setFilesError] = useState<string | undefined>()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const entryCounterRef = useRef(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function appendFiles(filesToAdd: FileList | File[]) {
    const accepted: Entry[] = []
    const errors: string[] = []

    for (const file of Array.from(filesToAdd)) {
      if (file.size > MAX_FILE_BYTES) {
        errors.push(`${file.name} excede o limite de 50 MB.`)
        continue
      }
      accepted.push({ id: `e${++entryCounterRef.current}`, file })
    }

    setEntries((prev) => {
      const next = [...prev, ...accepted]
      if (next.length > MAX_FILES) {
        errors.push(`Máximo de ${MAX_FILES} documentos por matéria.`)
        return next.slice(0, MAX_FILES)
      }
      return next
    })

    setFilesError(errors.length ? errors.join(' ') : undefined)
  }

  function handleFilesPicked(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files && event.target.files.length > 0) {
      appendFiles(event.target.files)
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function removeEntry(id: string) {
    setEntries((prev) => prev.filter((entry) => entry.id !== id))
    setFilesError(undefined)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedName = name.trim()
    if (!trimmedName) {
      setNameError('Informe o nome da matéria.')
      return
    }
    setNameError(undefined)

    setIsSubmitting(true)
    try {
      await createSubject(
        trimmedName,
        entries.map((entry) => entry.file),
      )
      onCreated()
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
              <Icon name="tag" size={18} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Nova matéria</h2>
              <p style={{ margin: '4px 0 0', fontSize: 12.5, color: 'var(--ink-4)' }}>
                Anexe a bibliografia da matéria para enriquecer os resumos das aulas. Limite de 50 MB por
                arquivo.
              </p>
            </div>
          </div>
          <button aria-label="Fechar modal" className="icon-btn" onClick={onClose} type="button">
            <Icon name="x" size={16} />
          </button>
        </div>

        <CardContent style={{ overflowY: 'auto', flex: 1, padding: '8px 22px 18px' }}>
          <form
            onSubmit={handleSubmit}
            id="nova-materia-form"
            style={{ display: 'flex', flexDirection: 'column', gap: 14 }}
          >
            <Input
              autoFocus
              error={nameError}
              icon="tag"
              label="Nome da matéria"
              onChange={(event) => {
                setName(event.target.value)
                setNameError(undefined)
              }}
              placeholder="Ex.: Cálculo Diferencial"
              value={name}
            />

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
                  Documentos ({entries.length}/{MAX_FILES}) · opcional
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
                  <p style={{ margin: '6px 0 0' }}>Clique para selecionar livros e artigos</p>
                  <p style={{ margin: '4px 0 0', fontSize: 11.5 }}>pdf, txt, md · até 50 MB cada</p>
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
                          flexShrink: 0,
                        }}
                      >
                        <Icon name="fileText" size={14} />
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
                          {formatBytes(entry.file.size)}
                        </div>
                      </div>
                      <button
                        aria-label="Remover"
                        className="icon-btn danger"
                        onClick={() => removeEntry(entry.id)}
                        type="button"
                      >
                        <Icon name="trash" size={13} />
                      </button>
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
            disabled={isSubmitting || !name.trim()}
            form="nova-materia-form"
            type="submit"
          >
            <Icon name="plus" size={14} />
            <span>{isSubmitting ? 'Criando...' : 'Criar matéria'}</span>
          </button>
        </div>
      </Card>
    </div>
  )
}
