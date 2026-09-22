const canvas = document.querySelector('#graph');
const ctx = canvas.getContext('2d');
const search = document.querySelector('#search');
const inspector = document.querySelector('#inspector');
const status = document.querySelector('#status');
const state = { nodes: [], edges: [], allNodes: [], allEdges: [], filters: { nodes: false, relationships: false }, scale: 1, panX: 0, panY: 0, selected: null, dragging: null, last: null };
const colors = { class: '#f26e5b', function: '#8173d6', method: '#1e8c83', file: '#a7b4a9', module: '#a7b4a9', reference: '#72807b' };

function resize() { const dpr = window.devicePixelRatio || 1; canvas.width = canvas.clientWidth * dpr; canvas.height = canvas.clientHeight * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); draw(); }
function layout(nodes) {
  const width = canvas.clientWidth, height = canvas.clientHeight;
  nodes.forEach((node, index) => { const angle = index * 2.399; const radius = Math.min(width, height) * .18 + (index % 5) * 28; node.x = width / 2 + Math.cos(angle) * radius; node.y = height / 2 + Math.sin(angle) * radius; node.vx = 0; node.vy = 0; });
}
function refresh() {
  const term = search.value.trim().toLowerCase();
  const nodeMatches = new Set(state.allNodes.filter(node => !term || `${node.name} ${node.qualified_name} ${node.file}`.toLowerCase().includes(term)).map(node => node.id));
  const relationshipMatches = state.allEdges.filter(edge => !term || `${edge.type} ${edge.target_ref || ''}`.toLowerCase().includes(term));
  let edges = state.allEdges;
  if (state.filters.relationships) edges = relationshipMatches;
  if (state.filters.nodes) edges = edges.filter(edge => nodeMatches.has(edge.source) || nodeMatches.has(edge.target));
  const ids = new Set();
  edges.forEach(edge => { ids.add(edge.source); if (edge.target) ids.add(edge.target); });
  let nodes = state.allNodes;
  if (state.filters.nodes && state.filters.relationships) nodes = state.allNodes.filter(node => ids.has(node.id) && nodeMatches.has(node.id));
  else if (state.filters.nodes) nodes = state.allNodes.filter(node => nodeMatches.has(node.id));
  else if (state.filters.relationships) nodes = state.allNodes.filter(node => ids.has(node.id));
  else nodes = state.allNodes;
  const visibleIds = new Set(nodes.map(node => node.id));
  state.nodes = nodes;
  state.edges = edges.filter(edge => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  status.textContent = `${state.nodes.length} nodes · ${state.edges.length} relationships`;
  draw();
}
function screen(node) { return { x: node.x * state.scale + state.panX, y: node.y * state.scale + state.panY }; }
function draw() {
  const width = canvas.clientWidth, height = canvas.clientHeight; ctx.clearRect(0, 0, width, height); ctx.save();
  state.edges.forEach(edge => { const source = state.nodes.find(n => n.id === edge.source), target = state.nodes.find(n => n.id === edge.target); if (!source || !target) return; const a = screen(source), b = screen(target); const active = state.selected && (edge.source === state.selected.id || edge.target === state.selected.id); ctx.strokeStyle = active ? '#f26e5b' : '#bcc8bf'; ctx.lineWidth = active ? 2.2 : 1; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); const angle = Math.atan2(b.y - a.y, b.x - a.x); ctx.fillStyle = ctx.strokeStyle; ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x - 8 * Math.cos(angle - .45), b.y - 8 * Math.sin(angle - .45)); ctx.lineTo(b.x - 8 * Math.cos(angle + .45), b.y - 8 * Math.sin(angle + .45)); ctx.fill(); if (active) { ctx.font = '10px DM Mono'; ctx.fillText(edge.type.toUpperCase(), (a.x + b.x) / 2, (a.y + b.y) / 2); } });
  state.nodes.forEach(node => { const p = screen(node); const active = state.selected && (node.id === state.selected.id || state.edges.some(e => e.source === state.selected.id && e.target === node.id || e.target === state.selected.id && e.source === node.id)); ctx.globalAlpha = state.selected && !active ? .28 : 1; ctx.fillStyle = colors[node.kind] || '#1e8c83'; ctx.setLineDash(node.unresolved ? [3, 3] : []); ctx.beginPath(); ctx.arc(p.x, p.y, node.id === state.selected?.id ? 9 : 7, 0, Math.PI * 2); ctx.fill(); ctx.setLineDash([]); ctx.fillStyle = '#17211f'; ctx.font = '12px Space Grotesk'; ctx.fillText(node.name, p.x + 12, p.y + 4); ctx.globalAlpha = 1; }); ctx.restore();
}
function hit(x, y) {
  return state.nodes.slice().reverse().find(node => {
    const point = screen(node);
    const labelWidth = ctx.measureText(node.name).width;
    const withinPoint = Math.hypot(point.x - x, point.y - y) < 20;
    const withinLabel = x >= point.x + 8 && x <= point.x + 16 + labelWidth
      && Math.abs(y - point.y) < 12;
    return withinPoint || withinLabel;
  });
}
function show(node) { state.selected = node; const data = state.nodeDetails?.[node.id]; if (!data) return; inspector.classList.add('open'); const relationships = (title, edges, incoming) => `<div class="detail-section"><h3>${title}</h3>${edges.length ? edges.map(e => `<span class="relationship"><b>${e.type.toUpperCase()}</b> ${incoming ? '←' : '→'} ${e.target_ref || e.target || 'unresolved'}</span>`).join('') : '<span class="detail-file">None</span>'}</div>`; const loc = data.node.location; inspector.innerHTML = `<span class="kind">${data.node.kind}</span><h2 class="detail-title">${data.node.qualified_name}</h2><div class="detail-file">${data.node.file}</div><div class="detail-location">${loc ? `${loc.start_line}:${loc.start_column} → ${loc.end_line}:${loc.end_column}` : 'Location unavailable'}</div><div class="detail-location">Hash: ${data.node.hash || 'unavailable'}</div>${data.node.docstring ? `<div class="detail-section"><h3>Docstring</h3><pre>${data.node.docstring}</pre></div>` : ''}${relationships('Outgoing', data.outgoing, false)}${relationships('Incoming', data.incoming, true)}<div class="detail-section"><h3>Metadata</h3><pre>${JSON.stringify(data.node.metadata, null, 2)}</pre></div>`; draw(); }
async function load() { const response = await fetch('/api/graph'); const payload = await response.json(); state.allNodes = payload.nodes; state.allEdges = payload.edges; layout(state.allNodes); const details = await Promise.all(state.allNodes.map(async n => [n.id, (await fetch(`/api/node/${n.id}`)).json()])); state.nodeDetails = Object.fromEntries(details); refresh(); }
canvas.addEventListener('pointerdown', event => {
  const node = hit(event.offsetX, event.offsetY);
  state.dragging = node || 'pan';
  state.last = { x: event.clientX, y: event.clientY };
  canvas.setPointerCapture(event.pointerId);
  if (node) show(node);
});
canvas.addEventListener('pointermove', event => {
  if (!state.dragging) return;
  const dx = event.clientX - state.last.x;
  const dy = event.clientY - state.last.y;
  state.last = { x: event.clientX, y: event.clientY };
  if (state.dragging === 'pan') {
    state.panX += dx;
    state.panY += dy;
  } else {
    state.dragging.x += dx / state.scale;
    state.dragging.y += dy / state.scale;
  }
  draw();
});
canvas.addEventListener('pointerup', event => {
  state.dragging = null;
  canvas.releasePointerCapture(event.pointerId);
});
canvas.addEventListener('wheel', event => { event.preventDefault(); const factor = event.deltaY < 0 ? 1.1 : .9; state.scale = Math.max(.35, Math.min(3, state.scale * factor)); draw(); }, { passive: false });
search.addEventListener('input', refresh);
document.querySelectorAll('.filter-toggle').forEach(button => button.addEventListener('click', () => { const filter = button.dataset.filter; state.filters[filter] = !state.filters[filter]; button.setAttribute('aria-pressed', state.filters[filter]); refresh(); }));
document.querySelector('#reset').addEventListener('click', () => { state.scale = 1; state.panX = 0; state.panY = 0; state.selected = null; state.filters.nodes = false; state.filters.relationships = false; document.querySelectorAll('.filter-toggle').forEach(button => button.setAttribute('aria-pressed', 'false')); inspector.classList.remove('open'); refresh(); });
document.querySelector('#focus').addEventListener('click', () => { if (!state.selected) return; const ids = new Set([state.selected.id]); state.allEdges.forEach(e => { if (e.source === state.selected.id) ids.add(e.target); if (e.target === state.selected.id) ids.add(e.source); }); state.nodes = state.allNodes.filter(n => ids.has(n.id)); state.edges = state.allEdges.filter(e => ids.has(e.source) && ids.has(e.target)); layout(state.nodes); status.textContent = `${state.nodes.length} node local neighborhood`; draw(); });
window.addEventListener('resize', resize); resize(); load().catch(error => { status.textContent = `Unable to load graph: ${error.message}`; });
