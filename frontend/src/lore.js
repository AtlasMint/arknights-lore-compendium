import * as d3 from 'd3'

// Spoiler control. A term is visible when it is a seed (the player picked it, or just saw it in a screenshot), when an
// override says so, when every story is ticked, or when any story it appears in is ticked. Untagged terms stay hidden
// until everything is ticked.
export function visibility({ tags, ticked, everything, overrides, seeds }) {
  return (term) => {
    if (seeds.has(term)) return true
    if (overrides[term]) return overrides[term] === 'show'
    return everything || (tags[term] ?? []).some((story) => ticked.has(story))
  }
}

// The summary sentences the player may read: one told by a story they have ticked, or one with no story that names
// only visible terms. With every story ticked, all of them.
export function readable(summary, { ticked, everything, isVisible }) {
  return summary.filter((s) => (s.story ? everything || ticked.has(s.story) : s.terms.every(isVisible)))
}

let context
// A label's width in pixels, in the given font.
export function measure(text, font = '12px system-ui, sans-serif') {
  context ??= document.createElement('canvas').getContext('2d')
  context.font = font
  return context.measureText(text).width
}

// Keeps the nodes' boxes (the shape and its name) from overlapping: d3's collide force, for boxes instead of circles.
// `box(node)` gives the box's edges relative to the node's centre. Each tick, every overlapping pair is pushed apart
// along the axis that needs the smaller move, like forceCollide's strength on the overlap.
// ponytail: every pair is checked, O(n²); fine for the 150 nodes a map holds, a quadtree if that ever grows
export function forceBoxes(box, strength = 0.5) {
  let nodes
  const force = () => {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const [a, b] = [nodes[i], nodes[j]]
        const [A, B] = [box(a), box(b)]
        const dx = Math.min(a.x + A.x1 - (b.x + B.x0), b.x + B.x1 - (a.x + A.x0)) // how far the boxes overlap along x
        const dy = Math.min(a.y + A.y1 - (b.y + B.y0), b.y + B.y1 - (a.y + A.y0))
        if (dx <= 0 || dy <= 0) continue
        const axis = dx < dy ? 'x' : 'y'
        const centre = (n, box) => (axis === 'x' ? n.x + (box.x0 + box.x1) / 2 : n.y + (box.y0 + box.y1) / 2)
        const push = (((axis === 'x' ? dx : dy) * strength) / 2) * (centre(a, A) < centre(b, B) ? -1 : 1)
        a[`v${axis}`] += push
        b[`v${axis}`] -= push
      }
    }
  }
  force.initialize = (n) => (nodes = n)
  return force
}

// The graph as the player may see it: hidden terms and unshown types are removed with their links, and a node left
// without links goes too, unless it is a seed.
export function visibleGraph(graph, isVisible, types) {
  const kept = new Set(graph.nodes.filter((n) => isVisible(n.id) && types.has(n.type)).map((n) => n.id))
  const links = graph.links.filter((l) => kept.has(l.source) && kept.has(l.target))
  const linked = new Set(links.flatMap((l) => [l.source, l.target]))
  return { nodes: graph.nodes.filter((n) => kept.has(n.id) && (n.seed || linked.has(n.id))), links }
}

// Where a link's label was learned: the first ticked story both ends share. null hides the label. With every story
// ticked a label always shows, naming the first shared story if there is one.
export function learnedIn(link, ticked, everything) {
  const story = link.stories.find((s) => ticked.has(s))
  if (story) return { story }
  return everything ? { story: link.stories[0] ?? null } : null
}

// Fog of the Future. Only the stories read, the ones where a storyline starts (nothing to read before them) and the
// immediate neighbours of either are on the canvas, so the player sees one step ahead and no further. The stories left
// uncovered, as a set of ids.
export function uncovered(data, ticked) {
  const starts = new Set(data.stories.map((s) => s.id))
  data.edges.forEach((e) => starts.delete(e.target)) // edges run in reading order, so a target has something before it
  const known = new Set([...ticked, ...starts])
  const shown = new Set(known)
  for (const e of data.edges) {
    if (known.has(e.source)) shown.add(e.target)
    if (known.has(e.target)) shown.add(e.source)
  }
  return shown
}

// Clicking an Episode ticks it and every Episode before it; clicking a ticked one unticks it and every one after.
// Any other story ticks on its own.
export function toggleStory(stories, ticked, id) {
  const next = new Set(ticked)
  const story = stories.find((s) => s.id === id)
  if (story.band !== 'main') {
    if (next.has(id)) next.delete(id)
    else next.add(id)
    return next
  }
  const chain = stories.filter((s) => s.band === 'main').sort((a, b) => a.order - b.order).map((s) => s.id)
  const i = chain.indexOf(id)
  if (ticked.has(id)) chain.slice(i).forEach((s) => next.delete(s))
  else chain.slice(0, i + 1).forEach((s) => next.add(s))
  return next
}

export const BANDS = [
  ['main', 'Main Theme'],
  ['intermezzo', 'Intermezzi'],
  ['side', 'Side Stories'],
  ['collection', 'Story Collections'],
  ['crossover', 'Crossovers'],
]
const PAD = 12 // canvas margin
export const GAP = 20 // least space between two nodes, along a row and between rows
const NODE = 22 // a node's height
const ROW = NODE + GAP // row pitch
const HEAD = 22 // band title
const ACTS = 16 // the Act labels above the Episode chain
const AXIS = 24 // year ticks or column headers
const PER_YEAR = 320 // release tab: pixels per year

// The in-game column a story falls in when all Movements show: up to 1096, its year, or undated.
export function yearColumn(story) {
  const year = story.year && Number.parseInt(story.year.replace('ca. ', ''), 10)
  if (!year) return 'Undated'
  return year <= 1096 ? 'to 1096' : String(year)
}

// Greedy row packing: in x order, each node takes the first row whose last node ends GAP before it starts, so no two
// nodes overlap by construction.
export function pack(items) {
  const ends = []
  for (const item of [...items].sort((a, b) => a.x - b.x || a.order - b.order)) {
    let row = ends.findIndex((end) => end + GAP <= item.x)
    if (row === -1) row = ends.push(0) - 1
    item.row = row
    ends[row] = item.x + item.w
  }
  return ends.length
}

// Positions for the stories canvas. `tab` is "release" (time axis from the Global start dates) or "ingame" (Score order
// for one Movement, else ordinal year columns with Score order inside each). With a Movement picked, stories of other
// Movements linked to it come along `faded`, at their date on the release tab and after the Movement's own on in-game.
// `measure(text)` is the label's width in pixels.
export function layoutStories(data, { tab, movement, measure }) {
  let shown = data.stories
  const faded = new Set()
  if (movement) {
    const own = new Set(data.stories.filter((s) => s.movement === movement).map((s) => s.id))
    for (const e of data.edges) {
      if (own.has(e.source) !== own.has(e.target)) faded.add(own.has(e.source) ? e.target : e.source)
    }
    shown = data.stories.filter((s) => own.has(s.id) || faded.has(s.id))
  }
  const items = shown.map((s) => ({ ...s, w: measure(`✓ ${s.name}`) + (s.movement ? 30 : 12), faded: faded.has(s.id) }))
  const widest = d3.max(items, (s) => s.w) ?? 0
  let ticks = []
  if (tab === 'release') {
    const dates = items.map((s) => new Date(s.start))
    const [from, to] = [d3.utcYear.floor(d3.min(dates)), d3.utcYear.offset(d3.utcYear.floor(d3.max(dates)), 1)]
    const x = d3.scaleUtc([from, to], [PAD, PAD + d3.utcYear.count(from, to) * PER_YEAR])
    items.forEach((s) => (s.x = x(new Date(s.start))))
    ticks = d3.utcYear.range(from, to).map((d) => ({ x: x(d), label: String(d.getUTCFullYear()) }))
  } else if (movement) {
    const ordered = [...items].sort((a, b) => a.faded - b.faded || a.order - b.order)
    ordered.forEach((s, i) => (s.x = PAD + i * (widest + GAP)))
  } else {
    const rank = (column) => (column === 'to 1096' ? 0 : column === 'Undated' ? 2 : 1)
    const names = [...new Set(items.map(yearColumn))].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b))
    const step = widest + 2 * GAP
    items.forEach((s) => (s.x = PAD + names.indexOf(yearColumn(s)) * step))
    ticks = names.map((label, i) => ({ x: PAD + i * step, label }))
  }

  // The Act labels get their own rows above the Episode chain, packed like the nodes so two never collide.
  const at = new Map(items.map((s) => [s.id, s]))
  const acts = data.acts.filter((a) => at.has(a.first)).map((a, order) => ({ ...a, x: at.get(a.first).x, w: measure(a.name), order }))
  const actRows = pack(acts)
  const bands = []
  let y = AXIS
  for (const [key, label] of BANDS) {
    const members = items.filter((s) => s.band === key)
    if (!members.length) continue // a band with nothing in it under this filter is hidden
    const top = y + HEAD + (key === 'main' ? actRows * ACTS : 0)
    if (key === 'main') acts.forEach((a) => (a.y = y + HEAD + a.row * ACTS + 10))
    const rows = pack(members)
    members.forEach((s) => (s.y = top + s.row * ROW))
    bands.push({ key, label, y, h: top - y + rows * ROW + GAP })
    y += bands.at(-1).h
  }
  const edges = data.edges
    .filter((e) => at.has(e.source) && at.has(e.target))
    .map((e) => ({ ...e, ...route(...[at.get(e.source), at.get(e.target)].sort((p, q) => p.x - q.x)) }))
  const width = d3.max(items, (s) => s.x + s.w) + PAD
  return { width: Math.max(width, ...ticks.map((t) => t.x + 60)), height: y, items, bands, ticks, acts, edges, node: NODE }
}

// The path of an edge between two placed nodes, `a` the left one. Side by side, it runs from the right end of `a` to the
// left end of `b`; stacked in one column, from the bottom of the upper to the top of the lower. `ends` says whose node
// each end of the path is, so a fade can run from one towards the other.
function route(a, b) {
  const side = a.x + a.w <= b.x
  const [p, q] = side ? [a, b] : [a, b].sort((m, n) => m.y - n.y)
  const [x1, y1, x2, y2] = side
    ? [p.x + p.w, p.y + NODE / 2, q.x, q.y + NODE / 2]
    : [p.x + p.w / 2, p.y + NODE, q.x + q.w / 2, q.y]
  const d = side
    ? `M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}`
    : `M${x1},${y1} C${x1},${(y1 + y2) / 2} ${x2},${(y1 + y2) / 2} ${x2},${y2}`
  return { d, ends: [{ id: p.id, x: x1, y: y1 }, { id: q.id, x: x2, y: y2 }] }
}
