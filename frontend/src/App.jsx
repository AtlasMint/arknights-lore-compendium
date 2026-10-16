import * as d3 from 'd3'
import { useEffect, useMemo, useRef, useState } from 'react'
import { GAP, forceBoxes, learnedIn, measure, readable, visibility, visibleGraph } from './lore.js'
import Stories from './Stories.jsx'

const WIKI = 'https://arknights.wiki.gg/wiki/'
const LABEL_BATCH = 10 // links per /labels call; about twenty seconds of the model's time when none is cached
const LINK = 70 // a link's length at rest
const SPREAD = 2 * LINK // the length of the selected node's links, so their labels have room to be read
const RUN = 700 // ms the map takes to run into place when it is built, or back when a node is deselected
const STRETCH = 3000 // ms a selection takes to stretch into place: a slow, even drift, not a run
const NAME_FONT = '10px system-ui, sans-serif' // .node text in index.css
const UNSURE = 'is related to' // the label when the wiki doesn't say, backend/graph/labels.py
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

const EMPTY = { ticked: [], overrides: {}, fog: false }

// The progress an earlier version kept in this browser, carried over the first time the API has no file.
function local() {
  try {
    return Object.fromEntries(Object.entries(EMPTY).map(([key, fallback]) => [key, JSON.parse(localStorage.getItem(key)) ?? fallback]))
  } catch {
    return EMPTY
  }
}

const linkKey = (link) => `${link.source}\n${link.target}`
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
  const [progress, setProgress] = useState(null) // {ticked, overrides: term -> "hide" | "show", fog}, from the API's file
  const saved = useRef() // the progress as last loaded or saved, so only a change is written
  const [types, setTypes] = useState(new Set(TYPES.map(([type]) => type)))
  const [labels, setLabels] = useState({}) // "source\ntarget" -> {from, relation, to}
  const [labelError, setLabelError] = useState('')
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

  // Progress is a file the API keeps (data/progress.json), so it follows the backend, not the browser. It is loaded
  // once and saved on every change after that. Until it has loaded nothing is saved, so a broken file is never
  // overwritten; with no file yet, whatever this browser kept before there was one is carried over.
  useEffect(() => {
    fetch('/progress')
      .then(async (response) => {
        if (response.status === 404) return local() // the first save makes the file
        const body = await response.json()
        if (!response.ok) throw new Error(body.error)
        saved.current = JSON.stringify(body)
        return body
      })
      .then(setProgress)
      .catch((error) => setStatus(`Couldn't load your progress, so nothing will be saved: ${error.message}`))
  }, [])
  useEffect(() => {
    const body = progress && JSON.stringify(progress)
    if (!body || body === saved.current) return
    // ponytail: no queue, so two saves in flight could land out of order; fine at the speed of clicks
    fetch('/progress', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body })
      .then(async (response) => {
        if (!response.ok) throw new Error((await response.json().catch(() => null))?.error ?? `status ${response.status}`)
        saved.current = body
      })
      .catch((error) => setStatus(`Progress not saved: ${error.message}`))
  }, [progress])

  const ticked = useMemo(() => new Set(progress?.ticked), [progress])
  const { overrides, fog } = progress ?? EMPTY
  const update = (patch) => setProgress((p) => p && { ...p, ...patch }) // nothing to change until it has loaded
  const setOverrides = (next) => update({ overrides: next })
  const everything = !!stories && stories.stories.every((s) => ticked.has(s.id))
  const seeds = useMemo(() => new Set(graph?.nodes.filter((n) => n.seed).map((n) => n.id)), [graph])
  const isVisible = useMemo(
    () => visibility({ tags: graph?.tags ?? {}, ticked, everything, overrides, seeds }),
    [graph, ticked, everything, overrides, seeds],
  )
  const visible = useMemo(() => graph && visibleGraph(graph, isVisible, types), [graph, isVisible, types])
  const hidden = graph?.nodes.filter((n) => !isVisible(n.id)) ?? []
  const storyNames = useMemo(() => Object.fromEntries((stories?.stories ?? []).map((s) => [s.id, s.name])), [stories])
  // Faction colours follow the faction, ranked once per graph, so ticking a story never repaints the survivors.
  const factionColors = useMemo(() => {
    const score = d3.rollup(graph?.nodes.filter((n) => n.faction) ?? [], (ns) => d3.sum(ns, (n) => n.score), (n) => n.faction)
    const top = [...score].sort((a, b) => b[1] - a[1]).slice(0, FACTION_COLORS)
    return new Map(top.map(([faction], i) => [faction, `var(--series-${i + 1})`]))
  }, [graph])

  // Label the visible links a batch at a time. Each finished batch starts the next, which puts the links of whatever is
  // selected then first. Selecting doesn't restart the batch in flight: the model would label the same pairs twice.
  useEffect(() => {
    if (!visible || labelError) return
    const touches = (l) => l.source === selected || l.target === selected
    const pending = visible.links.filter((l) => !(linkKey(l) in labels)).sort((a, b) => touches(b) - touches(a))
    if (!pending.length) return
    let cancelled = false
    const batch = pending.slice(0, LABEL_BATCH)
    fetch('/labels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pairs: batch.map((l) => [l.source, l.target]) }),
    })
      .then((response) => response.json().then((body) => (response.ok ? body : Promise.reject(new Error(body.error)))))
      .then((body) => {
        if (!cancelled) setLabels((old) => ({ ...old, ...Object.fromEntries(batch.map((l, i) => [linkKey(l), body.labels[i]])) }))
      })
      .catch((error) => !cancelled && setLabelError(error.message || 'Labels unavailable.'))
    return () => {
      cancelled = true
    }
  }, [visible, labels, labelError]) // eslint-disable-line react-hooks/exhaustive-deps -- selected: see above

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

  function clear() {
    setGraph(null)
    setSelected(null)
    setStatus('Graph cleared. Your keywords are kept.')
  }

  function restart() {
    shots.forEach((s) => URL.revokeObjectURL(s.preview))
    setShots([])
    setChips([])
    clear()
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
    setLabelError('')
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
          <button type="button" onClick={clear} disabled={!graph}>
            Clear graph
          </button>
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
        <Stories data={stories} ticked={ticked} onTicked={(next) => update({ ticked: [...next] })} fog={fog} onFog={(on) => update({ fog: on })} />
      )}
      {view === 'map' && visible && (
        <main className="map">
          <Graph
            data={visible}
            colors={factionColors}
            selected={selected}
            onSelect={setSelected}
            label={(link) => {
              // On the map a label goes on the selected node's links, read from whichever end the wiki speaks of.
              const known = learnedIn(link, ticked, everything) && labels[linkKey(link)]
              if (!known || known.relation === UNSURE) return null
              return known.from === selected ? known.relation : `${known.from} ${known.relation}`
            }}
          />
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
            <p>
              {visible.links.filter((l) => linkKey(l) in labels).length} of {visible.links.length} links labelled
            </p>
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
            {labelError && <p>Labels: {labelError}</p>}
          </aside>
          {node && (
            <Detail
              node={node}
              links={visible.links.filter((l) => l.source === node.id || l.target === node.id)}
              {...{ labels, ticked, everything, isVisible, storyNames, overrides, setOverrides }}
              shot={shotOf(node.id)}
              onSelect={setSelected}
            />
          )}
        </main>
      )}
    </>
  )
}

// What the player may know about one node: the summary sentences the stories read have told, grouped by story after the
// ones from no story in particular, and its links with the labels learned in a ticked story.
function Detail({ node, links, labels, ticked, everything, isVisible, storyNames, overrides, setOverrides, shot, onSelect }) {
  const sentences = readable(node.summary, { ticked, everything, isVisible })
  const withheld = node.summary.length - sentences.length
  const lead = sentences.filter((s) => !s.story)
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
      {(lead.length > 0 || sentences.length === 0) && <p>{lead.map((s) => s.text).join(' ') || 'Nothing you have read yet.'}</p>}
      {d3.groups(
        sentences.filter((s) => s.story),
        (s) => s.story,
      ).map(([story, said]) => (
        <p key={story}>
          {said.map((s) => s.text).join(' ')}
          <span className="meta"> · learned in {storyNames[story] ?? story}</span>
        </p>
      ))}
      {withheld > 0 && <p className="meta">{withheld} more sentence{withheld > 1 ? 's' : ''} once you read further.</p>}
      <h3>Connections</h3>
      {links.some((l) => !learnedIn(l, ticked, everything)) && (
        <p className="meta">A connection is labelled once you have read a story both ends appear in.</p>
      )}
      <ul>
        {[...links]
          .sort((a, b) => b.weight - a.weight)
          .map((l) => {
            const other = l.source === node.id ? l.target : l.source
            const learned = learnedIn(l, ticked, everything)
            const known = labels[linkKey(l)]
            const name = (title) =>
              title === node.id ? (
                title
              ) : (
                <button type="button" className="link" onClick={() => onSelect(title)}>
                  {title}
                </button>
              )
            return (
              <li key={other}>
                {learned ? (
                  <>
                    {known ? (
                      <>
                        {name(known.from)} {known.relation} {name(known.to)}
                      </>
                    ) : (
                      <>
                        {name(l.source)} … {name(l.target)}
                      </>
                    )}
                    {learned.story && <span className="meta"> · learned in {storyNames[learned.story] ?? learned.story}</span>}
                  </>
                ) : (
                  name(other)
                )}
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

// Runs a stopped simulation to its end at once: as many ticks as it would take live to cool from its alpha to alphaMin.
function settle(sim) {
  sim.tick(Math.ceil(Math.log(sim.alphaMin() / sim.alpha()) / Math.log(1 - sim.alphaDecay())))
}

function Graph({ data, colors, selected, onSelect, label }) {
  const svgRef = useRef(null)
  const positions = useRef(new Map()) // where each node was, so ticking a story doesn't scatter the map
  const painted = useRef(false) // a frame has shown the map; before that, saved positions are a dev re-run's, not the player's
  const placed = useRef([]) // the simulation's links, which carry their ends' positions
  const simulation = useRef()
  const render = useRef(() => {}) // draws the simulation's current positions: at once, or over `duration` ms with `ease`
  const zoom = useRef() // the zoom behaviour, so a selection can pan the view
  const chosen = useRef(selected) // what the link force reads, so a rebuild keeps the selected node spread out
  const length = (l) => (l.source.id === chosen.current || l.target.id === chosen.current ? SPREAD : LINK)

  useEffect(() => {
    const svg = d3.select(svgRef.current)
    const { width, height } = svgRef.current.getBoundingClientRect()
    const kept = (d) => (painted.current ? positions.current.get(d.id) : undefined)
    const nodes = data.nodes.map((d) => ({ ...d, ...kept(d) })) // the simulation mutates these
    const links = data.links.map((d) => ({ ...d }))
    const radius = d3.scaleSqrt().domain(d3.extent(nodes, (d) => d.score)).range([4, 18])
    // Each node's box for the layout: its shape (a star or diamond of area πr² reaches 1.7r from its centre), its name
    // to the right, and half the gap all round.
    nodes.forEach((d) => {
      const reach = Math.max(1.7 * radius(d.score), 7)
      d.box = { x0: -reach - GAP / 2, x1: radius(d.score) + 3 + measure(d.id, NAME_FONT) + GAP / 2, y0: -reach - GAP / 2, y1: reach + GAP / 2 }
    })

    const root = svg.append('g')
    zoom.current = d3.zoom().scaleExtent([0.2, 8]).on('zoom', (event) => root.attr('transform', event.transform))
    svg.call(zoom.current)
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
    const labelGroup = root.append('g').attr('class', 'link-labels') // over the nodes, so a label stays readable
    placed.current = links

    const sim = d3
      .forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(length))
      .force('charge', d3.forceManyBody().strength(-160))
      .force('collide', forceBoxes((d) => d.box, 0.5, 0.3)) // sideways moves count a third, so the map spreads wide first
      .force('center', d3.forceCenter(width / 2, height / 2))
      // The canvas is wide, so the map settles wide: a pull towards the middle row much stronger than towards the
      // middle column, and the box collision then spreads the nodes sideways.
      .force('x', d3.forceX(width / 2).strength(0.005))
      .force('y', d3.forceY(height / 2).strength(0.2))
      .stop() // never left running: the layout is settled in one go, and the map runs into it over a set time
    nodes.forEach((d) => {
      if (!kept(d)) [d.x, d.y] = [d.x + width / 2, d.y + height / 2] // new nodes start from the middle
    })
    const draw = (duration = 0, ease = d3.easeCubicOut) => {
      const t = d3.transition().duration(duration).ease(ease)
      const moving = (selection) => (duration ? selection.transition(t) : selection)
      moving(link)
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y)
      moving(node).attr('transform', (d) => `translate(${d.x},${d.y})`)
      moving(labelGroup.selectAll('text'))
        .attr('x', (d) => (d.source.x + d.target.x) / 2)
        .attr('y', (d) => (d.source.y + d.target.y) / 2)
      nodes.forEach((d) => positions.current.set(d.id, { x: d.x, y: d.y }))
    }
    sim.on('tick', () => draw()) // only a drag runs it live
    if (nodes.every(kept)) sim.alpha(0.1) // only hidden nodes left: settle, don't re-shuffle
    draw() // where everything starts
    settle(sim)
    draw(RUN)
    requestAnimationFrame(() => (painted.current = true))
    simulation.current = sim
    render.current = draw

    // A drag runs the simulation live. It starts on the first move, not on mousedown, since every click is a mousedown
    // too and a live run would overwrite the selection's transition.
    let dragging = false
    node.call(
      d3
        .drag()
        .on('start', (event, d) => {
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          if (!dragging) sim.alphaTarget(0.3).restart()
          dragging = true
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (dragging) sim.alphaTarget(0)
          dragging = false
          d.fx = null
          d.fy = null
        }),
    )

    return () => {
      sim.stop()
      svg.on('.zoom', null).on('click', null)
      root.remove()
    }
  }, [data, colors, onSelect])

  // Selecting a node stretches its links to twice their length, so the labels on them can be read. Deselecting puts
  // every node back where it was before the selection, since a link to a hub pulls too weakly to shrink back on its
  // own. The layout is only nudged, never reshuffled.
  const before = useRef(null) // positions when the selection began, by node
  useEffect(() => {
    const sim = simulation.current
    if (!sim) return
    if (selected && !before.current) before.current = new Map(sim.nodes().map((d) => [d.id, [d.x, d.y]]))
    if (!selected && before.current) {
      sim.nodes().forEach((d) => {
        const was = before.current.get(d.id)
        if (was) [d.x, d.y, d.vx, d.vy] = [...was, 0, 0]
      })
      before.current = null
    }
    chosen.current = selected
    sim.stop() // a live run left from a drag would draw over the transition
    sim.force('link').distance(length)
    if (selected) {
      sim.alpha(0.3)
      settle(sim)
      render.current(STRETCH, d3.easeSinInOut) // a gentle start and end, nothing sudden
      // The view pans so the selected node ends up in the middle, at the current zoom, in step with the stretch.
      const d = sim.nodes().find((n) => n.id === selected)
      const { width, height } = svgRef.current.getBoundingClientRect()
      const k = d3.zoomTransform(svgRef.current).k
      d3.select(svgRef.current)
        .transition()
        .duration(STRETCH)
        .ease(d3.easeSinInOut)
        .call(zoom.current.transform, d3.zoomIdentity.translate(width / 2 - k * d.x, height / 2 - k * d.y).scale(k))
    } else render.current(RUN) // back at the map's own pace
  }, [selected]) // eslint-disable-line react-hooks/exhaustive-deps -- length reads `chosen`, set just above

  // Selecting a node lights it and its neighbours, dims the rest and writes the labels on its links.
  useEffect(() => {
    const svg = d3.select(svgRef.current)
    const near = new Set(
      selected ? [selected, ...data.links.flatMap((l) => (l.source === selected ? [l.target] : l.target === selected ? [l.source] : []))] : [],
    )
    const touches = (d) => !!selected && (d.source.id === selected || d.target.id === selected)
    svg.selectAll('.node').classed('selected', (d) => d.id === selected).classed('dim', (d) => !!selected && !near.has(d.id))
    svg.selectAll('.links line').classed('lit', touches)
    svg
      .select('.link-labels')
      .selectAll('text')
      .data(
        placed.current.filter((d) => touches(d) && label({ ...d, source: d.source.id, target: d.target.id })),
        (d) => `${d.source.id}\n${d.target.id}`,
      )
      .join('text')
      .text((d) => label({ ...d, source: d.source.id, target: d.target.id }))
      .attr('x', (d) => (d.source.x + d.target.x) / 2)
      .attr('y', (d) => (d.source.y + d.target.y) / 2)
  }, [data, selected, label])

  return <svg ref={svgRef} role="group" aria-label={`Lore graph of ${data.nodes.length} wiki pages`} />
}
