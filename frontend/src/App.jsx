import * as d3 from 'd3'
import { useEffect, useMemo, useRef, useState } from 'react'
import { visibility, visibleGraph } from './lore.js'
import Stories from './Stories.jsx'

const WIKI = 'https://arknights.wiki.gg/wiki/'
// Map-legend shapes: what a node is. Colour is kept for which faction it belongs to.
const TYPES = [
  ['Operator', d3.symbolCircle],
  ['Character', d3.symbolDiamond],
  ['Faction', d3.symbolSquare],
  ['Location', d3.symbolTriangle],
  ['Event', d3.symbolStar],
  ['Other', d3.symbolCross],
]
const SHAPES = Object.fromEntries(TYPES)
// Only three hues stay apart when any two nodes can sit side by side, so the three largest factions get one each and
// the rest share the neutral. The node labels and the detail panel name every faction.
const FACTION_COLORS = 3

// A value this browser kept, or the fallback when there is none or storage is blocked.
function useStored(key, fallback) {
  const [value, setValue] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(key)) ?? fallback
    } catch {
      return fallback
    }
  })
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // private window or blocked storage: progress lasts until the tab closes
    }
  }, [key, value])
  return [value, setValue]
}

const wikiUrl = (title) => WIKI + encodeURIComponent(title.replaceAll(' ', '_'))

export default function App() {
  // Keywords to seed the graph with. Only chips that are on are sent; `shot` is the screenshot that introduced one.
  const [chips, setChips] = useState([
    { title: 'Amiya', on: true },
    { title: 'Reunion', on: true },
  ])
  const [shots, setShots] = useState([]) // this session's screenshots: {n, preview, reading}
  const [draft, setDraft] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [depth, setDepth] = useState(1)
  const [graph, setGraph] = useState(null)
  const [status, setStatus] = useState('')
  const [view, setView] = useState('map')
  const [stories, setStories] = useState(null)
  const [tickedList, setTickedList] = useStored('ticked', [])
  const [overrides, setOverrides] = useStored('overrides', {}) // term -> "hide" | "show", correcting the tags
  const [types, setTypes] = useState(new Set(TYPES.map(([type]) => type)))
  const [selected, setSelected] = useState(null)

  // JSON from the backend, or null after putting the reason in the status line.
  async function api(url, options) {
    const response = await fetch(url, options).catch(() => null)
    const body = await response?.json().catch(() => null)
    if (response?.ok && body) return body
    setStatus(body?.error ?? `Backend unreachable or failed (${response?.status ?? 'no response'}).`)
    return null
  }

  useEffect(() => {
    fetch('/stories')
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error(response.status))))
      .then(setStories)
      .catch(() => setStatus('Could not load the stories, so only your keywords show on the map.'))
  }, [])

  const ticked = useMemo(() => new Set(tickedList), [tickedList])
  const everything = !!stories && stories.stories.every((s) => ticked.has(s.id))
  const seeds = useMemo(() => new Set(graph?.nodes.filter((n) => n.seed).map((n) => n.id)), [graph])
  const isVisible = useMemo(
    () => visibility({ tags: graph?.tags ?? {}, ticked, everything, overrides, seeds }),
    [graph, ticked, everything, overrides, seeds],
  )
  const visible = useMemo(() => graph && visibleGraph(graph, isVisible, types), [graph, isVisible, types])
  const hidden = graph?.nodes.filter((n) => !isVisible(n.id)) ?? []
  // Faction colours follow the faction, ranked once per graph, so ticking a story never repaints the survivors.
  const factionColors = useMemo(() => {
    const score = d3.rollup(graph?.nodes.filter((n) => n.faction) ?? [], (ns) => d3.sum(ns, (n) => n.score), (n) => n.faction)
    const top = [...score].sort((a, b) => b[1] - a[1]).slice(0, FACTION_COLORS)
    return new Map(top.map(([faction], i) => [faction, `var(--series-${i + 1})`]))
  }, [graph])

  // The reader's time grows with pixels: a 2340×1080 phone screenshot took 19 s, at 1280 px wide 6 s,
  // and the dialog text is still legible. Anything that isn't an image is sent as is, for the server's 415.
  async function shrink(file, maxSide = 1280) {
    const bitmap = await createImageBitmap(file).catch(() => null)
    if (!bitmap || Math.max(bitmap.width, bitmap.height) <= maxSide) return file
    const scale = maxSide / Math.max(bitmap.width, bitmap.height)
    const canvas = new OffscreenCanvas(Math.round(bitmap.width * scale), Math.round(bitmap.height * scale))
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    return canvas.convertToBlob({ type: 'image/png' })
  }

  // Each screenshot adds its keywords to the session's; a keyword already there keeps the screenshot that brought it.
  async function analyze(file) {
    if (!file) return
    const n = (shots.at(-1)?.n ?? 0) + 1
    const preview = URL.createObjectURL(file)
    setShots((old) => [...old, { n, preview, reading: null }])
    setStatus(`Reading screenshot ${n}…`)
    const form = new FormData()
    form.append('image', await shrink(file), 'screenshot.png')
    const body = await api('/analyze', { method: 'POST', body: form })
    if (!body) {
      URL.revokeObjectURL(preview)
      setShots((old) => old.filter((s) => s.n !== n))
      return
    }
    setShots((old) => old.map((s) => (s.n === n ? { ...s, reading: body } : s)))
    setChips((old) => {
      const fresh = (title) => !old.some((c) => c.title === title)
      return [
        ...old,
        ...body.keywords.filter(fresh).map((title) => ({ title, on: true, guess: body.guesses[title], shot: n })),
        ...body.needs_context.filter(fresh).map((title) => ({ title, on: false, shot: n })),
      ]
    })
    setStatus(
      body.keywords.length || body.needs_context.length
        ? 'Click a keyword to include or leave it out (dashed ones are left out; dotted ones are inferred, hover to see the word), then build the graph.'
        : `No wiki terms found in screenshot ${n}. Add keywords by hand.`,
    )
  }

  function restart() {
    shots.forEach((s) => URL.revokeObjectURL(s.preview))
    setShots([])
    setChips([])
    setGraph(null)
    setSelected(null)
    setStatus('New session: drop a screenshot or add keywords.')
  }

  async function suggest(value) {
    setDraft(value)
    if (value.trim().length < 2) return
    const response = await fetch(`/terms?${new URLSearchParams({ prefix: value.trim() })}`).catch(() => null)
    setSuggestions((await response?.json().catch(() => null)) ?? [])
  }

  function add(event) {
    event.preventDefault()
    const titles = draft.split(',').map((t) => t.trim()).filter(Boolean)
    setChips([...chips.filter((c) => !titles.includes(c.title)), ...titles.map((title) => ({ title, on: true }))])
    setDraft('')
  }

  async function build(event) {
    event.preventDefault()
    const seeds = chips.filter((c) => c.on).map((c) => c.title).join(',')
    const speaker = shots.map((s) => s.reading?.speaker).filter(Boolean).join(',')
    setStatus('Building… a cold cache takes several seconds.')
    const body = await api(`/graph?${new URLSearchParams({ seeds, depth, speaker })}`)
    if (!body) return
    setGraph(body)
    setSelected(null)
    setView('map')
    setStatus(`${body.nodes.length} nodes, ${body.links.length} links`)
  }

  const shotOf = (title) => chips.find((c) => c.title === title)?.shot
  const node = visible?.nodes.find((n) => n.id === selected)

  return (
    <>
      <header>
        <div>
          <label
            className="drop"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              analyze(e.dataTransfer.files[0])
            }}
          >
            Drop a story screenshot here, or{' '}
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => analyze(e.target.files[0])} />
          </label>
          {shots.map((s) => (
            <figure key={s.n} className="shot">
              <img src={s.preview} alt={`Screenshot ${s.n}`} />
              <figcaption>{s.n}</figcaption>
            </figure>
          ))}
          {shots.at(-1)?.reading && (
            <p className="reading">
              <b>{shots.at(-1).reading.speaker || 'No speaker'}:</b> {shots.at(-1).reading.text}
            </p>
          )}
        </div>
        <form onSubmit={add} aria-label="Keywords">
          {chips.map((chip, i) => (
            <button
              key={chip.title}
              type="button"
              className={chip.guess ? 'chip guess' : 'chip'}
              title={[chip.guess && `Read as “${chip.guess}”`, chip.shot && `From screenshot ${chip.shot}`].filter(Boolean).join('. ') || undefined}
              aria-pressed={chip.on}
              onClick={() => setChips(chips.map((c, j) => (i === j ? { ...c, on: !c.on } : c)))}
            >
              {chip.title}
              {chip.shot && <sup aria-label={`from screenshot ${chip.shot}`}>{chip.shot}</sup>}
            </button>
          ))}
          <input
            list="terms"
            value={draft}
            onChange={(e) => suggest(e.target.value)}
            placeholder="Add a keyword"
            aria-label="Add a keyword"
          />
          <datalist id="terms">
            {suggestions.map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
          <button>Add</button>
        </form>
        <form onSubmit={build}>
          <label>
            Depth{' '}
            <select value={depth} onChange={(e) => setDepth(Number(e.target.value))}>
              {[1, 2, 3].map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>
          <button>Build graph</button>
          <button type="button" onClick={restart}>
            New session
          </button>
          <nav role="tablist" aria-label="View">
            <button type="button" role="tab" aria-selected={view === 'map'} onClick={() => setView('map')}>
              Lore map
            </button>
            <button type="button" role="tab" aria-selected={view === 'stories'} onClick={() => setView('stories')}>
              Stories read {stories ? `(${stories.stories.filter((s) => ticked.has(s.id)).length}/${stories.stories.length})` : ''}
            </button>
          </nav>
          <output>{status}</output>
        </form>
      </header>
      {view === 'stories' && stories && (
        <Stories data={stories} ticked={ticked} onTicked={(next) => setTickedList([...next])} />
      )}
      {view === 'map' && visible && (
        <main className="map">
          <Graph data={visible} colors={factionColors} selected={selected} onSelect={setSelected} />
          <aside className="legend" aria-label="Legend">
            <fieldset>
              <legend>Show</legend>
              {TYPES.map(([type, shape]) => (
                <label key={type}>
                  <input
                    type="checkbox"
                    checked={types.has(type)}
                    onChange={() => setTypes(new Set(types.has(type) ? [...types].filter((t) => t !== type) : [...types, type]))}
                  />
                  <svg width="14" height="14" viewBox="-7 -7 14 14" aria-hidden="true">
                    <path d={d3.symbol(shape, 60)()} />
                  </svg>
                  {type}
                </label>
              ))}
            </fieldset>
            <ul>
              {[...factionColors].filter(([faction]) => visible.nodes.some((n) => n.faction === faction)).map(([faction, color]) => (
                <li key={faction}>
                  <span className="swatch" style={{ background: color }} />
                  {faction}
                </li>
              ))}
              <li>
                <span className="swatch" style={{ background: 'var(--node)' }} />
                Other faction, or none
              </li>
            </ul>
            {!!hidden.length && (
              <details>
                <summary>{hidden.length} hidden: show names (spoilers)</summary>
                <ul>
                  {hidden.map((n) => (
                    <li key={n.id}>
                      {n.id}{' '}
                      <button type="button" onClick={() => setOverrides({ ...overrides, [n.id]: 'show' })}>
                        Show anyway
                      </button>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </aside>
          {node && (
            <Detail
              node={node}
              links={visible.links.filter((l) => l.source === node.id || l.target === node.id)}
              {...{ isVisible, overrides, setOverrides }}
              shot={shotOf(node.id)}
              onSelect={setSelected}
            />
          )}
        </main>
      )}
    </>
  )
}

// What the player may know about one node: its summary without sentences that name a hidden term, and its links.
function Detail({ node, links, isVisible, overrides, setOverrides, shot, onSelect }) {
  const sentences = node.summary.filter((s) => s.terms.every(isVisible))
  const withheld = node.summary.length - sentences.length
  return (
    <aside className="detail" aria-label={`About ${node.id}`}>
      <button type="button" className="close" aria-label="Close" onClick={() => onSelect(null)}>
        ×
      </button>
      <h2>
        <a href={wikiUrl(node.id)} target="_blank" rel="noreferrer">
          {node.id}
        </a>
      </h2>
      <p className="meta">
        {[node.type, node.faction !== node.id && node.faction, node.seed && (shot ? `from screenshot ${shot}` : 'your keyword')]
          .filter(Boolean)
          .join(' · ')}
      </p>
      <p>{sentences.map((s) => s.text).join(' ') || 'Nothing you have read yet.'}</p>
      {withheld > 0 && <p className="meta">{withheld} more sentence{withheld > 1 ? 's' : ''} once you read further.</p>}
      <h3>Connections</h3>
      <ul>
        {[...links]
          .sort((a, b) => b.weight - a.weight)
          .map((l) => {
            const other = l.source === node.id ? l.target : l.source
            return (
              <li key={other}>
                <button type="button" className="link" onClick={() => onSelect(other)}>
                  {other}
                </button>
              </li>
            )
          })}
      </ul>
      {!node.seed && (
        <button type="button" onClick={() => setOverrides({ ...overrides, [node.id]: 'hide' })}>
          Hide this
        </button>
      )}
      {overrides[node.id] && (
        <button
          type="button"
          onClick={() => setOverrides(Object.fromEntries(Object.entries(overrides).filter(([term]) => term !== node.id)))}
        >
          Undo “{overrides[node.id] === 'show' ? 'show anyway' : 'hide'}”
        </button>
      )}
    </aside>
  )
}

function Graph({ data, colors, selected, onSelect }) {
  const svgRef = useRef(null)
  const positions = useRef(new Map()) // where each node was, so ticking a story doesn't scatter the map

  useEffect(() => {
    const svg = d3.select(svgRef.current)
    const { width, height } = svgRef.current.getBoundingClientRect()
    const nodes = data.nodes.map((d) => ({ ...d, ...positions.current.get(d.id) })) // the simulation mutates these
    const links = data.links.map((d) => ({ ...d }))
    const radius = d3.scaleSqrt().domain(d3.extent(nodes, (d) => d.score)).range([4, 18])

    const root = svg.append('g')
    svg.call(d3.zoom().scaleExtent([0.2, 8]).on('zoom', (event) => root.attr('transform', event.transform)))
    svg.on('click', (event) => event.target === svgRef.current && onSelect(null))

    const link = root
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke-width', (d) => Math.sqrt(d.weight))
    const node = root
      .append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', (d) => (d.seed ? 'node seed' : 'node'))
      .attr('tabindex', 0)
      .attr('role', 'button')
      .attr('aria-label', (d) => `${d.id}, ${d.type}${d.faction && d.faction !== d.id ? ` of ${d.faction}` : ''}`)
      .on('click', (event, d) => onSelect(d.id))
      .on('keydown', (event, d) => (event.key === 'Enter' || event.key === ' ') && onSelect(d.id))
    node
      .append('path')
      .attr('d', (d) => d3.symbol(SHAPES[d.type] ?? d3.symbolCross, Math.PI * radius(d.score) ** 2)())
      .style('fill', (d) => colors.get(d.faction) ?? null)
    node
      .append('text')
      .text((d) => d.id)
      .attr('x', (d) => radius(d.score) + 3)
      .attr('dy', '0.35em')
    node.filter((d) => d.seed).raise()

    const simulation = d3
      .forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(70))
      .force('charge', d3.forceManyBody().strength(-160))
      .force('collide', d3.forceCollide((d) => radius(d.score) + 2))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .on('tick', () => {
        link
          .attr('x1', (d) => d.source.x)
          .attr('y1', (d) => d.source.y)
          .attr('x2', (d) => d.target.x)
          .attr('y2', (d) => d.target.y)
        node.attr('transform', (d) => `translate(${d.x},${d.y})`)
        nodes.forEach((d) => positions.current.set(d.id, { x: d.x, y: d.y }))
      })
    if (nodes.every((d) => d.x !== undefined)) simulation.alpha(0.1) // only hidden nodes left: settle, don't re-shuffle

    node.call(
      d3
        .drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        }),
    )

    return () => {
      simulation.stop()
      svg.on('.zoom', null).on('click', null)
      root.remove()
    }
  }, [data, colors, onSelect])

  // Selecting a node lights it and its neighbours and dims the rest, without restarting the layout.
  useEffect(() => {
    const svg = d3.select(svgRef.current)
    const near = new Set(
      selected ? [selected, ...data.links.flatMap((l) => (l.source === selected ? [l.target] : l.target === selected ? [l.source] : []))] : [],
    )
    const touches = (d) => !!selected && (d.source.id === selected || d.target.id === selected)
    svg.selectAll('.node').classed('selected', (d) => d.id === selected).classed('dim', (d) => !!selected && !near.has(d.id))
    svg.selectAll('.links line').classed('lit', touches)
  }, [data, selected])

  return <svg ref={svgRef} role="group" aria-label={`Lore graph of ${data.nodes.length} wiki pages`} />
}
