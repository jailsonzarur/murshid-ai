import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Background,
  Controls,
  Handle,
  NodeResizer,
  Position,
  getNodesBounds,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type Node as RFNode,
  type NodeProps,
} from '@xyflow/react'
import dagre from 'dagre'

import '@xyflow/react/dist/style.css'

import type { LectureNode } from '../../types/lecture'
import { Icon } from '../ui/icon'

const NODE_WIDTH = 260
const NODE_HEIGHT = 96
const NODE_PADDING_Y = 12
const NODE_PADDING_X = 14
const TITLE_SIZE = 13.5
const TITLE_LINE_HEIGHT = 1.3
const SUMMARY_SIZE = 11.5
const SUMMARY_LINE_HEIGHT = 1.4
const TITLE_CSS =
  `font-size:${TITLE_SIZE}px;font-weight:700;line-height:${TITLE_LINE_HEIGHT};letter-spacing:-0.01em`
const SUMMARY_CSS = `font-size:${SUMMARY_SIZE}px;line-height:${SUMMARY_LINE_HEIGHT}`
const PRINT_STAGE_ID = 'tree-print-stage'
const PULSE_DURATION_MS = 1200
const FADE_DURATION_MS = 400

const heightCache = new Map<string, number>()

function measureNodeHeight(label: string, summary: string | null): number {
  const key = `${label}\u0000${summary ?? ''}`
  const cached = heightCache.get(key)
  if (cached !== undefined) return cached

  const probe = document.createElement('div')
  probe.style.cssText =
    `position:absolute;left:-9999px;top:0;visibility:hidden;width:${NODE_WIDTH}px;` +
    `box-sizing:border-box;padding:${NODE_PADDING_Y}px ${NODE_PADDING_X}px;` +
    'border:1px solid transparent;font-family:var(--sans)'

  const title = document.createElement('div')
  title.textContent = label
  title.style.cssText = `${TITLE_CSS};margin-bottom:${summary ? 4 : 0}px`
  probe.appendChild(title)

  if (summary) {
    const body = document.createElement('div')
    body.textContent = summary
    body.style.cssText = SUMMARY_CSS
    probe.appendChild(body)
  }

  document.body.appendChild(probe)
  const height = Math.max(NODE_HEIGHT, Math.ceil(probe.getBoundingClientRect().height))
  probe.remove()

  heightCache.set(key, height)
  return height
}

type NodeData = {
  label: string
  summary: string | null
  isFresh: boolean
  isFading: boolean
  isRoot: boolean
  [key: string]: unknown
}

type TopicRFNode = RFNode<NodeData>

function buildLayout(
  lectureNodes: LectureNode[],
  freshIds: Set<string>,
  fadingIds: Set<string>,
) {
  if (lectureNodes.length === 0) {
    return { nodes: [] as TopicRFNode[], edges: [] as Edge[] }
  }

  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 70, marginx: 24, marginy: 24 })

  const validIds = new Set(lectureNodes.map((node) => node.id))

  const heights = new Map<string, number>()
  lectureNodes.forEach((node) => {
    const height = measureNodeHeight(node.label, node.summary)
    heights.set(node.id, height)
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height })
  })

  const edges: Edge[] = []
  lectureNodes.forEach((node) => {
    if (node.parent_id && validIds.has(node.parent_id)) {
      dagreGraph.setEdge(node.parent_id, node.id)
      const fading = fadingIds.has(node.id) || fadingIds.has(node.parent_id)
      edges.push({
        id: `e-${node.parent_id}-${node.id}`,
        source: node.parent_id,
        target: node.id,
        type: 'smoothstep',
        animated: false,
        style: {
          stroke: 'oklch(72% 0.04 270)',
          strokeWidth: 1.4,
          opacity: fading ? 0 : 1,
          transition: `opacity ${FADE_DURATION_MS}ms ease-out`,
        },
      })
    }
  })

  dagre.layout(dagreGraph)

  const nodes: TopicRFNode[] = lectureNodes.map((node) => {
    const pos = dagreGraph.node(node.id)
    const height = heights.get(node.id) ?? NODE_HEIGHT
    return {
      id: node.id,
      type: 'topic',
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - height / 2 },
      width: NODE_WIDTH,
      height,
      data: {
        label: node.label,
        summary: node.summary,
        isFresh: freshIds.has(node.id),
        isFading: fadingIds.has(node.id),
        isRoot: node.parent_id === null,
      },
    }
  })

  return { nodes, edges }
}

function TopicNode({ data, selected }: NodeProps<TopicRFNode>) {
  const { label, summary, isFresh, isFading, isRoot } = data

  return (
    <>
      <div
      style={{
        width: '100%',
        height: '100%',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        padding: `${NODE_PADDING_Y}px ${NODE_PADDING_X}px`,
        borderRadius: 12,
        background: isRoot ? 'oklch(58% 0.18 285)' : '#fff',
        color: isRoot ? '#fff' : 'var(--ink)',
        border: isRoot ? 'none' : '1px solid var(--line)',
        boxShadow: isFresh
          ? '0 0 0 3px oklch(82% 0.16 140 / 0.6), 0 4px 12px rgba(0,0,0,0.08)'
          : '0 1px 3px rgba(0,0,0,0.05)',
        transition: `box-shadow 0.3s ease, opacity ${FADE_DURATION_MS}ms ease-out, transform ${FADE_DURATION_MS}ms ease-out`,
        animation: isFresh ? 'tree-node-pulse 1.2s ease-out' : undefined,
        opacity: isFading ? 0 : 1,
        transform: isFading ? 'scale(0.9)' : 'scale(1)',
        pointerEvents: isFading ? 'none' : 'auto',
        fontFamily: 'var(--sans)',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: 'none' }} />
      <div
        style={{
          fontSize: TITLE_SIZE,
          fontWeight: 700,
          letterSpacing: '-0.01em',
          lineHeight: TITLE_LINE_HEIGHT,
          marginBottom: summary ? 4 : 0,
          flexShrink: 0,
        }}
      >
        {label}
      </div>
      {summary ? (
        <div
          style={{
            fontSize: SUMMARY_SIZE,
            color: isRoot ? 'rgba(255,255,255,0.85)' : 'var(--ink-3)',
            lineHeight: SUMMARY_LINE_HEIGHT,
            flex: 1,
            minHeight: 0,
            overflow: 'hidden',
          }}
          title={summary}
        >
          {summary}
        </div>
      ) : null}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
      </div>
      <NodeResizer
        isVisible={selected && !isFading}
        minWidth={160}
        minHeight={64}
        color="oklch(58% 0.18 285)"
      />
    </>
  )
}

const nodeTypes = { topic: TopicNode }

type TreeViewerInnerProps = {
  lectureNodes: LectureNode[]
  isProcessing: boolean
  isFullscreen: boolean
  onToggleFullscreen: () => void
}

function TreeViewerInner({
  lectureNodes,
  isProcessing,
  isFullscreen,
  onToggleFullscreen,
}: TreeViewerInnerProps) {
  const [displayedNodes, setDisplayedNodes] = useState<LectureNode[]>(lectureNodes)
  const [freshIds, setFreshIds] = useState<Set<string>>(new Set())
  const [fadingIds, setFadingIds] = useState<Set<string>>(new Set())
  const lastSnapshotsRef = useRef<Map<string, LectureNode>>(
    new Map(lectureNodes.map((node) => [node.id, node])),
  )
  const { fitView } = useReactFlow()
  const [isExporting, setIsExporting] = useState(false)
  const [fontsReady, setFontsReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    void document.fonts.ready.then(() => {
      if (cancelled) return
      heightCache.clear()
      setFontsReady(true)
    })
    return () => {
      cancelled = true
    }
  }, [])

  // sync displayedNodes from prop, detect additions/removals/updates
  useEffect(() => {
    const incomingIds = new Set(lectureNodes.map((node) => node.id))
    const previousIds = new Set(lastSnapshotsRef.current.keys())

    const justAdded: string[] = []
    incomingIds.forEach((id) => {
      if (!previousIds.has(id)) justAdded.push(id)
    })

    const justRemoved: string[] = []
    previousIds.forEach((id) => {
      if (!incomingIds.has(id)) justRemoved.push(id)
    })

    // snapshots for nodes that disappeared (so we can keep them visible while fading)
    const removedSnapshots = justRemoved
      .map((id) => lastSnapshotsRef.current.get(id))
      .filter((node): node is LectureNode => node !== undefined)

    // updated snapshot map for next diff
    lastSnapshotsRef.current = new Map(lectureNodes.map((node) => [node.id, node]))

    // pulse animation on new nodes
    if (justAdded.length > 0) {
      setFreshIds((prev) => {
        const next = new Set(prev)
        justAdded.forEach((id) => next.add(id))
        return next
      })
      window.setTimeout(() => {
        setFreshIds((prev) => {
          const next = new Set(prev)
          justAdded.forEach((id) => next.delete(id))
          return next
        })
      }, PULSE_DURATION_MS)
    }

    // start fade on removed nodes — keep them in displayedNodes until fade completes
    if (justRemoved.length > 0) {
      setFadingIds((prev) => {
        const next = new Set(prev)
        justRemoved.forEach((id) => next.add(id))
        return next
      })

      // merged display: incoming nodes (with fresh data) + soon-to-fade snapshots
      setDisplayedNodes([...lectureNodes, ...removedSnapshots])

      window.setTimeout(() => {
        setFadingIds((prev) => {
          const next = new Set(prev)
          justRemoved.forEach((id) => next.delete(id))
          return next
        })
        setDisplayedNodes((current) => current.filter((node) => !justRemoved.includes(node.id)))
      }, FADE_DURATION_MS)
    } else {
      setDisplayedNodes(lectureNodes)
    }
  }, [lectureNodes])

  const layout = useMemo(
    () => buildLayout(displayedNodes, freshIds, fadingIds),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [displayedNodes, freshIds, fadingIds, fontsReady],
  )

  const [nodes, setNodes, onNodesChange] = useNodesState<TopicRFNode>(layout.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(layout.edges)

  const laidOutIdsRef = useRef('')

  useEffect(() => {
    setNodes((current) => {
      const previous = new Map(current.map((node) => [node.id, node]))
      return layout.nodes.map((node) => {
        const existing = previous.get(node.id)
        if (!existing) return node
        const sameText =
          existing.data.label === node.data.label && existing.data.summary === node.data.summary
        if (!sameText) return { ...node, selected: existing.selected }
        return { ...node, selected: existing.selected, width: existing.width, height: existing.height }
      })
    })
    setEdges(layout.edges)

    const ids = layout.nodes.map((node) => node.id).join('|')
    if (ids === laidOutIdsRef.current) return
    laidOutIdsRef.current = ids

    // refit on structure change
    const id = window.setTimeout(() => {
      void fitView({ padding: 0.2, duration: 300 })
    }, 50)
    return () => window.clearTimeout(id)
  }, [layout, setNodes, setEdges, fitView])

  if (lectureNodes.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          color: 'var(--ink-4)',
          gap: 12,
          padding: 24,
          textAlign: 'center',
        }}
      >
        <div
          aria-hidden="true"
          style={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            background: 'var(--bg-sunken)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon name="listChecks" size={28} />
        </div>
        <div>
          <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: 'var(--ink)' }}>
            Ouvindo a aula...
          </h4>
          <p style={{ margin: '6px 0 0', fontSize: 12.5 }}>
            Os tópicos da sua aula aparecerão aqui conforme o professor avança.
          </p>
        </div>
        {isProcessing ? <UpdatingChip /> : null}
      </div>
    )
  }

  const handleExportPdf = () => {
    const viewportEl = document.querySelector('.react-flow__viewport')
    if (!(viewportEl instanceof HTMLElement) || nodes.length === 0) return

    const bounds = getNodesBounds(nodes)
    const padding = 48
    const width = Math.ceil(bounds.width + padding * 2)
    const height = Math.ceil(bounds.height + padding * 2)

    const clone = viewportEl.cloneNode(true) as HTMLElement
    clone.style.transform = `translate(${padding - bounds.x}px, ${padding - bounds.y}px) scale(1)`
    clone.style.transformOrigin = '0 0'
    clone.querySelectorAll('.react-flow__resize-control').forEach((element) => element.remove())

    const stage = document.createElement('div')
    stage.id = PRINT_STAGE_ID
    stage.className = 'react-flow'
    stage.style.cssText =
      `position:relative;width:${width}px;height:${height}px;background:#fff;overflow:hidden`
    stage.appendChild(clone)

    const style = document.createElement('style')
    style.textContent = `
      @media screen { #${PRINT_STAGE_ID} { display: none } }
      @media print {
        @page { size: ${width}px ${height}px; margin: 0 }
        html, body { margin: 0 !important; padding: 0 !important; background: #fff !important }
        body > *:not(#${PRINT_STAGE_ID}) { display: none !important }
        #${PRINT_STAGE_ID} { position: absolute; left: 0; top: 0 }
        #${PRINT_STAGE_ID}, #${PRINT_STAGE_ID} * {
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }
      }
    `

    const cleanup = () => {
      stage.remove()
      style.remove()
      window.removeEventListener('afterprint', cleanup)
    }

    document.body.appendChild(style)
    document.body.appendChild(stage)
    window.addEventListener('afterprint', cleanup)
    window.setTimeout(cleanup, 60000)
    window.print()
  }

  const handleExport = async () => {
    const viewportEl = document.querySelector('.react-flow__viewport')
    if (!(viewportEl instanceof HTMLElement) || nodes.length === 0) return

    setIsExporting(true)
    setNodes((current) => current.map((node) => (node.selected ? { ...node, selected: false } : node)))

    try {
      await new Promise((resolve) => window.setTimeout(resolve, 32))

      const bounds = getNodesBounds(nodes)
      const padding = 48
      const width = Math.ceil(bounds.width + padding * 2)
      const height = Math.ceil(bounds.height + padding * 2)

      const { toPng } = await import('html-to-image')
      const dataUrl = await toPng(viewportEl, {
        backgroundColor: '#fff',
        width,
        height,
        pixelRatio: 2,
        style: {
          width: `${width}px`,
          height: `${height}px`,
          transform: `translate(${padding - bounds.x}px, ${padding - bounds.y}px) scale(1)`,
        },
      })

      const root = displayedNodes.find((node) => node.parent_id === null)
      const slug = (root?.label ?? 'mapa-da-aula')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-zA-Z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
        .toLowerCase()

      const anchor = document.createElement('a')
      anchor.href = dataUrl
      anchor.download = `${slug || 'mapa-da-aula'}.png`
      anchor.click()
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      proOptions={{ hideAttribution: true }}
      minZoom={0.2}
      maxZoom={2}
    >
      <Background gap={20} size={1} color="oklch(92% 0.005 270)" />
      <Controls showInteractive={false} />
      <div
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          display: 'flex',
          gap: 6,
          alignItems: 'center',
          zIndex: 5,
        }}
      >
        {isProcessing ? <UpdatingChip /> : null}
        <button
          aria-label="Baixar o mapa em PDF"
          className="icon-btn"
          onClick={handleExportPdf}
          style={{
            background: '#fff',
            border: '1px solid var(--line)',
            width: 30,
            height: 30,
            borderRadius: 8,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
          title="Baixar como PDF"
          type="button"
        >
          <Icon name="fileText" size={14} />
        </button>
        <button
          aria-label="Baixar o mapa como imagem"
          className="icon-btn"
          disabled={isExporting}
          onClick={() => void handleExport()}
          style={{
            background: '#fff',
            border: '1px solid var(--line)',
            width: 30,
            height: 30,
            borderRadius: 8,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            opacity: isExporting ? 0.5 : 1,
          }}
          title={isExporting ? 'Gerando imagem...' : 'Baixar como imagem'}
          type="button"
        >
          <Icon name="arrowDown" size={14} />
        </button>
        <button
          aria-label={isFullscreen ? 'Sair da tela cheia' : 'Entrar em tela cheia'}
          className="icon-btn"
          onClick={onToggleFullscreen}
          style={{
            background: '#fff',
            border: '1px solid var(--line)',
            width: 30,
            height: 30,
            borderRadius: 8,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
          title={isFullscreen ? 'Sair da tela cheia' : 'Tela cheia'}
          type="button"
        >
          <Icon name={isFullscreen ? 'x' : 'arrowUpRight'} size={14} />
        </button>
      </div>
    </ReactFlow>
  )
}

function UpdatingChip() {
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '5px 10px',
        borderRadius: 999,
        background: 'var(--warn-soft)',
        color: 'var(--warn)',
        fontSize: 11,
        fontWeight: 600,
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 9,
          height: 9,
          borderRadius: '50%',
          border: '2px solid currentColor',
          borderTopColor: 'transparent',
          animation: 'tree-spin 0.9s linear infinite',
          display: 'inline-block',
        }}
      />
      Atualizando...
    </div>
  )
}

type TreeViewerProps = {
  lectureNodes: LectureNode[]
  isProcessing?: boolean
  className?: string
  style?: React.CSSProperties
}

export function TreeViewer({ lectureNodes, isProcessing = false, className, style }: TreeViewerProps) {
  const [isFullscreen, setIsFullscreen] = useState(false)

  useEffect(() => {
    if (!isFullscreen) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [isFullscreen])

  useEffect(() => {
    if (!isFullscreen) return
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsFullscreen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isFullscreen])

  const containerStyle: React.CSSProperties = isFullscreen
    ? {
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: '#fff',
      }
    : {
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 420,
        background: '#fff',
        borderRadius: 12,
        overflow: 'hidden',
        border: '1px solid var(--line)',
        ...style,
      }

  return (
    <div className={className} style={containerStyle}>
      <ReactFlowProvider>
        <TreeViewerInner
          lectureNodes={lectureNodes}
          isProcessing={isProcessing}
          isFullscreen={isFullscreen}
          onToggleFullscreen={() => setIsFullscreen((value) => !value)}
        />
      </ReactFlowProvider>
      <style>{`
        @keyframes tree-node-pulse {
          0% { transform: scale(1); }
          30% { transform: scale(1.04); }
          100% { transform: scale(1); }
        }
        @keyframes tree-spin {
          to { transform: rotate(360deg); }
        }
        .react-flow__resize-control.line.left,
        .react-flow__resize-control.line.right {
          width: 18px;
        }
        .react-flow__resize-control.line.top,
        .react-flow__resize-control.line.bottom {
          height: 18px;
        }
        .react-flow__resize-control.handle {
          width: 28px;
          height: 28px;
          background: transparent !important;
          border: none;
          border-radius: 0;
        }
        .react-flow__resize-control.handle::after {
          content: '';
          position: absolute;
          inset: 8px;
          border-radius: 3px;
          background: oklch(58% 0.18 285);
          box-shadow: 0 0 0 1px #fff;
        }
      `}</style>
    </div>
  )
}
