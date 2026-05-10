import { useState, type ChangeEvent, type DragEvent } from 'react'

import { Icon } from './icon'

type FileDropzoneProps = {
  error?: string | null
  files: File[]
  onFilesChange: (files: File[]) => void
}

const acceptedMimeTypes = ['image/jpeg', 'image/png', 'application/pdf']

export function FileDropzone({ error, files, onFilesChange }: FileDropzoneProps) {
  const [localError, setLocalError] = useState<string | null>(null)
  const visibleError = error ?? localError

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
      onFilesChange([...files, ...acceptedFiles])
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
          {files.map((file, index) => (
            <div className="file-dropzone__item" key={`${file.name}-${file.lastModified}-${index}`}>
              <span>{file.name}</span>
              <button
                aria-label={`Remover ${file.name}`}
                onClick={() => removeFile(index)}
                type="button"
              >
                <Icon name="x" size={14} />
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
