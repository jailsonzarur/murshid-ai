import { useEffect, useRef } from 'react'

import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'

const transformer = new Transformer()

type MindmapProps = {
  markdown: string
  className?: string
  style?: React.CSSProperties
}

export function Mindmap({ className, markdown, style }: MindmapProps) {
  const svgRef = useRef<SVGSVGElement | null>(null)
  const markmapRef = useRef<Markmap | null>(null)

  useEffect(() => {
    if (!svgRef.current) return

    if (!markmapRef.current) {
      markmapRef.current = Markmap.create(svgRef.current)
    }

    const { root } = transformer.transform(markdown || '# (mapa vazio)')
    markmapRef.current.setData(root)
    void markmapRef.current.fit()
  }, [markdown])

  useEffect(() => {
    return () => {
      markmapRef.current?.destroy()
      markmapRef.current = null
    }
  }, [])

  function handleZoomIn() {
    markmapRef.current?.rescale(1.25)
  }

  function handleZoomOut() {
    markmapRef.current?.rescale(0.8)
  }

  function handleFit() {
    void markmapRef.current?.fit()
  }

  return (
    <div className={className} style={{ position: 'relative', width: '100%', height: 420, ...style }}>
      <div
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          zIndex: 2,
          display: 'flex',
          gap: 4,
          background: 'var(--card-bg, #fff)',
          padding: 4,
          borderRadius: 8,
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        }}
      >
        <button
          aria-label="Aproximar"
          className="icon-btn"
          onClick={handleZoomIn}
          title="Aproximar"
          type="button"
        >
          +
        </button>
        <button
          aria-label="Afastar"
          className="icon-btn"
          onClick={handleZoomOut}
          title="Afastar"
          type="button"
        >
          −
        </button>
        <button
          aria-label="Ajustar"
          className="icon-btn"
          onClick={handleFit}
          title="Ajustar"
          type="button"
          style={{ fontSize: 12 }}
        >
          ⤢
        </button>
      </div>
      <svg ref={svgRef} style={{ width: '100%', height: '100%', display: 'block' }} />
    </div>
  )
}
