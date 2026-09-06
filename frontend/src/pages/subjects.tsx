import { useEffect, useState, type FormEvent } from 'react'

import { AppShell } from '../components/layout/app-shell'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { Icon } from '../components/ui/icon'
import { Input } from '../components/ui/input'
import { getAccessToken } from '../lib/auth'
import {
  ApiError,
  createCategory,
  deleteCategory,
  listCategories,
  updateCategory,
} from '../lib/api'
import { navigateTo } from '../lib/navigation'
import type { Category } from '../types/lecture'

export function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [newName, setNewName] = useState('')
  const [createError, setCreateError] = useState<string | undefined>()
  const [isCreating, setIsCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editError, setEditError] = useState<string | undefined>()
  const [isSaving, setIsSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<Category | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    if (!getAccessToken()) {
      navigateTo('/login', { replace: true })
      return
    }

    void loadCategories()
  }, [])

  async function loadCategories() {
    setIsLoading(true)
    try {
      const data = await listCategories()
      setCategories(data)
    } catch {
      setCategories([])
    } finally {
      setIsLoading(false)
    }
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = newName.trim()
    if (!trimmed) {
      setCreateError('Informe o nome da matéria.')
      return
    }
    setIsCreating(true)
    setCreateError(undefined)
    try {
      await createCategory(trimmed)
      setNewName('')
      await loadCategories()
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'validation') {
        setCreateError(error.message)
      }
    } finally {
      setIsCreating(false)
    }
  }

  function startEdit(category: Category) {
    setEditingId(category.id)
    setEditName(category.name)
    setEditError(undefined)
  }

  function cancelEdit() {
    setEditingId(null)
    setEditName('')
    setEditError(undefined)
  }

  async function handleSaveEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingId) return
    const trimmed = editName.trim()
    if (!trimmed) {
      setEditError('Informe o nome da matéria.')
      return
    }
    setIsSaving(true)
    setEditError(undefined)
    try {
      await updateCategory(editingId, trimmed)
      cancelEdit()
      await loadCategories()
    } catch (error) {
      if (error instanceof ApiError && error.kind === 'validation') {
        setEditError(error.message)
      }
    } finally {
      setIsSaving(false)
    }
  }

  async function handleConfirmDelete() {
    if (!confirmDelete) return
    setIsDeleting(true)
    try {
      await deleteCategory(confirmDelete.id)
      setConfirmDelete(null)
      await loadCategories()
    } catch {
      return
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <AppShell
      activeItem="categories"
      description="Cadastre as matérias que organizarão suas aulas e provas."
      title="Matérias"
    >
      <Card style={{ marginBottom: 20 }}>
        <CardHeader>
          <CardTitle>Nova matéria</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <Input
                error={createError}
                onChange={(event) => {
                  setNewName(event.target.value)
                  setCreateError(undefined)
                }}
                placeholder="Ex.: Cálculo Diferencial"
                value={newName}
              />
            </div>
            <button
              className="btn btn-primary"
              disabled={isCreating || !newName.trim()}
              type="submit"
              style={{ marginTop: 26 }}
            >
              <Icon name="plus" size={14} />
              <span>{isCreating ? 'Salvando...' : 'Adicionar'}</span>
            </button>
          </form>
        </CardContent>
      </Card>

      <section aria-label="Lista de matérias">
        {isLoading ? (
          <EmptyState description="Buscando matérias cadastradas." title="Carregando..." />
        ) : categories.length === 0 ? (
          <EmptyState
            description="Cadastre a primeira matéria usando o formulário acima."
            title="Nenhuma matéria cadastrada."
          />
        ) : (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              background: 'var(--card-bg, #fff)',
              border: '1px solid var(--line)',
              borderRadius: 12,
              overflow: 'hidden',
            }}
          >
            {categories.map((category, index) => {
              const isEditing = editingId === category.id
              return (
                <div
                  key={category.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 14,
                    padding: '14px 20px',
                    borderBottom: index === categories.length - 1 ? 'none' : '1px solid var(--line)',
                  }}
                >
                  <div
                    aria-hidden="true"
                    className="avatar avatar-blue"
                    style={{ width: 40, height: 40, borderRadius: 10, flexShrink: 0 }}
                  >
                    <Icon name="tag" size={18} />
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    {isEditing ? (
                      <form
                        onSubmit={handleSaveEdit}
                        style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}
                      >
                        <div style={{ flex: 1 }}>
                          <Input
                            autoFocus
                            error={editError}
                            label=""
                            onChange={(event) => {
                              setEditName(event.target.value)
                              setEditError(undefined)
                            }}
                            value={editName}
                          />
                        </div>
                        <button
                          className="btn btn-primary btn-sm"
                          disabled={isSaving || !editName.trim()}
                          type="submit"
                        >
                          <Icon name="check" size={12} />
                          <span>{isSaving ? '...' : 'Salvar'}</span>
                        </button>
                        <button
                          className="btn btn-ghost btn-sm"
                          disabled={isSaving}
                          onClick={cancelEdit}
                          type="button"
                        >
                          <Icon name="x" size={12} />
                          <span>Cancelar</span>
                        </button>
                      </form>
                    ) : (
                      <div
                        style={{
                          fontSize: 14.5,
                          fontWeight: 600,
                          letterSpacing: '-0.01em',
                          color: 'var(--ink)',
                        }}
                      >
                        {category.name}
                      </div>
                    )}
                  </div>
                  {!isEditing && (
                    <div className="row-actions" style={{ flexShrink: 0 }}>
                      <button
                        aria-label={`Editar ${category.name}`}
                        className="icon-btn"
                        onClick={() => startEdit(category)}
                        title="Editar"
                        type="button"
                      >
                        <Icon name="settings" size={14} />
                      </button>
                      <button
                        aria-label={`Excluir ${category.name}`}
                        className="icon-btn danger"
                        onClick={() => setConfirmDelete(category)}
                        title="Excluir"
                        type="button"
                      >
                        <Icon name="trash" size={14} />
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </section>

      {confirmDelete ? (
        <div className="modal-backdrop" role="presentation">
          <Card style={{ maxWidth: 440, width: '100%' }}>
            <CardHeader>
              <CardTitle>Excluir matéria</CardTitle>
            </CardHeader>
            <CardContent>
              <p style={{ fontSize: 14, color: 'var(--ink-2)', lineHeight: 1.5 }}>
                Tem certeza que deseja excluir <strong>{confirmDelete.name}</strong>? Aulas
                vinculadas a essa matéria continuarão existindo, mas perderão o vínculo.
              </p>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 18 }}>
                <button
                  className="btn btn-ghost"
                  disabled={isDeleting}
                  onClick={() => setConfirmDelete(null)}
                  type="button"
                >
                  Cancelar
                </button>
                <button
                  className="btn btn-danger"
                  disabled={isDeleting}
                  onClick={handleConfirmDelete}
                  type="button"
                >
                  <Icon name="trash" size={14} />
                  <span>{isDeleting ? 'Excluindo...' : 'Excluir'}</span>
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </AppShell>
  )
}
