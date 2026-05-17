import { useEffect, useMemo, useState, type ChangeEvent, type DragEvent } from 'react'
import { createPortal } from 'react-dom'

import type { OrderedExamUploadFile } from '../../types/exam-upload'
import { Icon } from './icon'

type FileDropzoneProps = {
  error?: string | null
  files: OrderedExamUploadFile[]
  onFilesChange: (files: OrderedExamUploadFile[]) => void
}

const acceptedMimeTypes = ['image/jpeg', 'image/png', 'application/pdf']

function createUploadFileId() {
  if ('randomUUID' in crypto) {
    return crypto.randomUUID()
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function formatFileSize(size: number) {
  if (size < 1024 * 1024) {
    return `${Math.max(1, Math.round(size / 1024))} KB`
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

export function FileDropzone({ error, files, onFilesChange }: FileDropzoneProps) {
  const [localError, setLocalError] = useState<string | null>(null)
  const [draggedFileId, setDraggedFileId] = useState<string | null>(null)
  const [previewFileId, setPreviewFileId] = useState<string | null>(null)
  const visibleError = error ?? localError
  const filePreviews = useMemo(
    () =>
      files.map((item) => ({
        ...item,
        previewUrl:
          item.file.type.startsWith('image/') || item.file.type === 'application/pdf'
            ? URL.createObjectURL(item.file)
            : null,
      })),
    [files],
  )
  const previewFile = filePreviews.find((item) => item.id === previewFileId)

  useEffect(() => {
    return () => {
      filePreviews.forEach((item) => {
        if (item.previewUrl) {
          URL.revokeObjectURL(item.previewUrl)
        }
      })
    }
  }, [filePreviews])

  function appendFiles(fileList: FileList | null) {
    if (!fileList) {
      return
    }

    const acceptedFiles = Array.from(fileList).filter((file) =>
      acceptedMimeTypes.includes(file.type),
    )
    const rejectedCount = fileList.length - acceptedFiles.length

    if (rejectedCount > 0) {
      setLocalError('Alguns arquivos foram ignorados. Use apenas PDF, JPG ou PNG.')
    } else {
      setLocalError(null)
    }

    if (acceptedFiles.length) {
      onFilesChange([
        ...files,
        ...acceptedFiles.map((file) => ({
          file,
          id: createUploadFileId(),
        })),
      ])
    }
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    appendFiles(event.target.files)
    event.target.value = ''
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    appendFiles(event.dataTransfer.files)
  }

  function removeFile(indexToRemove: number) {
    setLocalError(null)
    onFilesChange(files.filter((_, index) => index !== indexToRemove))
  }

  function moveFile(fromIndex: number, toIndex: number) {
    if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) {
      return
    }

    const nextFiles = [...files]
    const [movedFile] = nextFiles.splice(fromIndex, 1)
    nextFiles.splice(toIndex, 0, movedFile)
    onFilesChange(nextFiles)
  }

  function handleFileDrop(targetFileId: string) {
    if (!draggedFileId || draggedFileId === targetFileId) {
      setDraggedFileId(null)
      return
    }

    moveFile(
      files.findIndex((item) => item.id === draggedFileId),
      files.findIndex((item) => item.id === targetFileId),
    )
    setDraggedFileId(null)
  }

  return (
    <div className="file-dropzone">
      <label
        className={`file-dropzone__target${visibleError ? ' file-dropzone__target--error' : ''}`}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <input
          accept={acceptedMimeTypes.join(',')}
          multiple
          onChange={handleInputChange}
          type="file"
        />
        <span className="file-dropzone__icon">
          <Icon name="upload" size={20} />
        </span>
        <strong>Anexar arquivos</strong>
        <span>PDF, JPG ou PNG</span>
      </label>

      {visibleError ? (
        <span className="file-dropzone__error" role="alert">
          {visibleError}
        </span>
      ) : null}

      {files.length ? (
        <div className="file-dropzone__list">
          {filePreviews.map((item, index) => (
            <div
              className={`file-dropzone__item${item.id === draggedFileId ? ' is-dragging' : ''}`}
              draggable
              key={item.id}
              onDragEnd={() => setDraggedFileId(null)}
              onDragOver={(event) => event.preventDefault()}
              onDragStart={() => setDraggedFileId(item.id)}
              onDrop={() => handleFileDrop(item.id)}
            >
              <button
                aria-label={`Visualizar ${item.file.name}`}
                className="file-dropzone__preview"
                onClick={() => setPreviewFileId(item.id)}
                type="button"
              >
                {item.file.type.startsWith('image/') && item.previewUrl ? (
                  <img alt="" src={item.previewUrl} />
                ) : (
                  <Icon name="fileText" size={20} />
                )}
              </button>
              <span className="file-dropzone__order">{index + 1}</span>
              <div className="file-dropzone__item-text">
                <strong>{item.file.name}</strong>
                <span>{formatFileSize(item.file.size)}</span>
              </div>
              <button
                aria-label={`Mover ${item.file.name} para cima`}
                disabled={index === 0}
                onClick={() => moveFile(index, index - 1)}
                type="button"
              >
                <Icon name="arrowUp" size={14} />
              </button>
              <button
                aria-label={`Mover ${item.file.name} para baixo`}
                disabled={index === files.length - 1}
                onClick={() => moveFile(index, index + 1)}
                type="button"
              >
                <Icon name="arrowDown" size={14} />
              </button>
              <button
                aria-label={`Remover ${item.file.name}`}
                onClick={() => removeFile(index)}
                type="button"
              >
                <Icon name="x" size={14} />
              </button>
            </div>
          ))}
        </div>
      ) : null}

      {previewFile?.previewUrl
        ? createPortal(
            <div
              className="file-preview-backdrop"
              onMouseDown={(event) => {
                if (event.target === event.currentTarget) {
                  setPreviewFileId(null)
                }
              }}
              role="presentation"
            >
              <div className="file-preview-modal">
                <div className="file-preview-modal__heading">
                  <div>
                    <strong>{previewFile.file.name}</strong>
                    <span>
                      Página {filePreviews.findIndex((item) => item.id === previewFile.id) + 1}
                    </span>
                  </div>
                  <button
                    aria-label="Fechar visualização"
                    onClick={() => setPreviewFileId(null)}
                    type="button"
                  >
                    <Icon name="x" size={16} />
                  </button>
                </div>
                <div className="file-preview-modal__body">
                  {previewFile.file.type.startsWith('image/') ? (
                    <img alt={previewFile.file.name} src={previewFile.previewUrl} />
                  ) : (
                    <iframe src={previewFile.previewUrl} title={previewFile.file.name} />
                  )}
                </div>
              </div>
            </div>,
            document.body,
          )
        : null}
    </div>
  )
}
