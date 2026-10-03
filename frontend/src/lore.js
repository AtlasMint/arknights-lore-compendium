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
const GAP = 8 // least space between two nodes in a row
const ROW = 26 // row pitch; a node is ROW - 4 tall
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
    const step = widest + 3 * GAP
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
    .map((e) => {
      const [a, b] = [at.get(e.source), at.get(e.target)].sort((p, q) => p.x - q.x)
      if (a.x + a.w <= b.x) {
        // side by side: from the right end of one to the left end of the other
        const [x1, y1, x2, y2] = [a.x + a.w, a.y + ROW / 2 - 2, b.x, b.y + ROW / 2 - 2]
        return { ...e, d: `M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}` }
      }
      // stacked in one column: from the bottom of the upper to the top of the lower
      const [p, q] = [a, b].sort((m, n) => m.y - n.y)
      const [x1, y1, x2, y2] = [p.x + p.w / 2, p.y + ROW - 4, q.x + q.w / 2, q.y]
      return { ...e, d: `M${x1},${y1} C${x1},${(y1 + y2) / 2} ${x2},${(y1 + y2) / 2} ${x2},${y2}` }
    })
  const width = d3.max(items, (s) => s.x + s.w) + PAD
  return { width: Math.max(width, ...ticks.map((t) => t.x + 60)), height: y, items, bands, ticks, acts, edges, row: ROW }
}
