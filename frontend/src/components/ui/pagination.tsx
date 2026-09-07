import type { PaginationMeta } from '../../types/lecture'
import { Icon } from './icon'

type PaginationProps = {
  isBusy?: boolean
  meta: PaginationMeta
  onPageChange: (page: number) => void
}

const GAP = '…'

/** Janela de páginas em torno da atual, com as pontas sempre visíveis. */
function pageWindow(page: number, totalPages: number): (number | typeof GAP)[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1)
  }

  const pages = new Set([1, totalPages, page, page - 1, page + 1])
  const sorted = [...pages].filter((value) => value >= 1 && value <= totalPages).sort((a, b) => a - b)

  const output: (number | typeof GAP)[] = []
  let previous = 0
  for (const value of sorted) {
    if (previous && value - previous > 1) output.push(GAP)
    output.push(value)
    previous = value
  }
  return output
}

export function Pagination({ isBusy = false, meta, onPageChange }: PaginationProps) {
  const { page, items_per_page: itemsPerPage, total_items: totalItems, total_pages: totalPages } = meta

  if (totalItems === 0) return null

  const first = (page - 1) * itemsPerPage + 1
  const last = Math.min(page * itemsPerPage, totalItems)

  return (
    <nav aria-label="Paginação" className="pagination">
      <p className="pagination__summary">
        {first}–{last} de {totalItems}
      </p>

      <div className="pagination__pages">
        <button
          aria-label="Página anterior"
          className="pagination__step"
          disabled={isBusy || page <= 1}
          onClick={() => onPageChange(page - 1)}
          type="button"
        >
          <Icon name="arrowLeft" size={14} />
        </button>

        {pageWindow(page, totalPages).map((value, index) =>
          value === GAP ? (
            <span aria-hidden="true" className="pagination__gap" key={`gap-${index}`}>
              {GAP}
            </span>
          ) : (
            <button
              aria-current={value === page ? 'page' : undefined}
              className="pagination__page"
              data-active={value === page}
              disabled={isBusy}
              key={value}
              onClick={() => onPageChange(value)}
              type="button"
            >
              {value}
            </button>
          ),
        )}

        <button
          aria-label="Próxima página"
          className="pagination__step"
          disabled={isBusy || page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          type="button"
        >
          <Icon name="arrowRight" size={14} />
        </button>
      </div>
    </nav>
  )
}
