// E-Ink Display Panel
// Single-file custom panel — no build step required.

const GRID_ROWS = 3;
const GRID_COLS = 4;
const WIDGET_TYPES = ["weather", "calendar", "image"];

const WIDGET_FIELDS = {
  weather:  [{ key: "entity_id", label: "Weather entity", placeholder: "weather.forecast_home", domain: "weather" }],
  calendar: [
    { key: "entity_id",       label: "Calendar entity",        placeholder: "calendar.home", domain: "calendar" },
    { key: "forecast_entity", label: "Weather forecast (opt)", placeholder: "",              domain: "weather" },
    { key: "start_hour",      label: "Start hour (0–24)",      placeholder: "0" },
    { key: "end_hour",        label: "End hour (0–24)",        placeholder: "24" },
  ],
  image: [], // handled separately via media browser
};

const css = `
  :host { display: block; padding: 16px; font-family: var(--primary-font-family, sans-serif); }
  h1 { font-size: 1.4em; margin: 0 0 16px; }
  .toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
  .toolbar select, .toolbar input { padding: 6px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 0.9em; }
  button { padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em; background: var(--primary-color, #03a9f4); color: white; }
  button.secondary { background: #eee; color: #333; }
  button.danger { background: #e53935; }
  .main { display: flex; gap: 24px; flex-wrap: wrap; align-items: flex-start; }
  .left { display: flex; flex-direction: column; gap: 8px; }
  .grid { display: grid; grid-template-columns: repeat(${GRID_COLS}, 80px); grid-template-rows: repeat(${GRID_ROWS}, 80px); gap: 2px; background: #ddd; border: 2px solid #ddd; border-radius: 4px; }
  .cell { background: #f5f5f5; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 0.7em; text-align: center; padding: 4px; border-radius: 2px; transition: background 0.1s; overflow: hidden; }
  .cell:hover { background: #e3f2fd; }
  .cell.occupied { background: #1565c0; color: white; }
  .cell.selected { outline: 3px solid #f57c00; outline-offset: -3px; }
  .preview img { width: ${GRID_COLS * 80 + (GRID_COLS - 1) * 2}px; border: 2px solid #ddd; border-radius: 4px; display: block; }
  .sidebar { flex: 1; min-width: 220px; }
  .sidebar h3 { margin: 0 0 12px; font-size: 1em; }
  .field { margin-bottom: 10px; }
  .field label { display: block; font-size: 0.8em; color: #555; margin-bottom: 3px; }
  .field input, .field select { width: 100%; box-sizing: border-box; padding: 6px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 0.9em; }
  .span-row { display: flex; gap: 8px; }
  .span-row .field { flex: 1; }
  .empty-hint { color: #999; font-size: 0.85em; padding: 8px; }
`;

class EinkPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._entries = [];
    this._selectedEntry = null;
    this._layouts = {};
    this._activeLayout = "default";
    this._selectedCell = null; // {row, col}
    this._editingWidget = null; // widget object being edited
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._entries.length) this._loadEntries();
  }

  _updateUrl() {
    const hash = `#entry=${this._selectedEntry?.entry_id || ""}&layout=${encodeURIComponent(this._activeLayout)}`;
    history.replaceState(null, "", hash);
  }

  _readUrl() {
    const params = new URLSearchParams(location.hash.slice(1));
    return { entryId: params.get("entry"), layout: params.get("layout") };
  }

  async _loadEntries() {
    const resp = await this._hass.callWS({ type: "config_entries/get", domain: "eink" });
    this._entries = resp || [];
    if (this._entries.length && !this._selectedEntry) {
      const { entryId, layout } = this._readUrl();
      const target = this._entries.find(e => e.entry_id === entryId) || this._entries[0];
      await this._selectEntry(target.entry_id);
      if (layout && this._layouts[layout]) this._activeLayout = layout;
    }
    this._render();
  }

  async _selectEntry(entryId) {
    this._selectedEntry = this._entries.find(e => e.entry_id === entryId);
    // Load options from storage via WS
    const result = await this._hass.callWS({
      type: "config_entries/get",
      domain: "eink",
    });
    const entry = (result || []).find(e => e.entry_id === entryId);
    // Options aren't in the WS response — fetch from our own API endpoint
    const r = await fetch(`/api/eink_options/${entryId}`, {
      headers: { Authorization: `Bearer ${this._hass.auth.data.access_token}` },
    });
    if (r.ok) {
      const data = await r.json();
      this._layouts = data.layouts || { default: [] };
      this._activeLayout = data.active_layout || Object.keys(this._layouts)[0] || "default";
      this._token = data.token || "";
      this._dither = data.dither || "atkinson";
    } else {
      this._layouts = { default: [] };
      this._activeLayout = "default";
      this._token = "";
    }
    this._selectedCell = null;
    this._editingWidget = null;
  }

  _currentWidgets() {
    return this._layouts[this._activeLayout] || [];
  }

  // Returns the widget occupying (row, col), or null
  _widgetAt(row, col) {
    return this._currentWidgets().find(w =>
      row >= w.row && row < w.row + (w.row_span || 1) &&
      col >= w.col && col < w.col + (w.col_span || 1)
    ) || null;
  }

  _cellLabel(widget) {
    if (!widget) return "";
    const cfg = widget.config || {};
    const id = cfg.entity_id || cfg.url || "";
    return `${widget.type}\n${id.split(".").pop() || id.split("/").pop() || ""}`;
  }

  async _openMediaBrowser() {
    // Use HA's built-in media picker dialog
    const picker = document.createElement("ha-media-player-browse");
    picker.hass = this._hass;
    picker.entityId = "";
    picker.action = "play";

    // Fallback: use a simple WS-based tree picker
    await this._browseMediaTree("media-source://");
  }

  async _browseMediaTree(contentId) {
    let result;
    try {
      result = await this._hass.callWS({
        type: "media_source/browse_media",
        media_content_id: contentId,
      });
    } catch (e) {
      alert(`Media browse error: ${e.message}`);
      return;
    }

    const children = result.children || [];
    const folders = children.filter(c => c.can_expand);
    const images = children.filter(c => !c.can_expand && (c.media_content_type || "").startsWith("image/"));

    if (folders.length === 0 && images.length === 0) {
      alert("No folders or images found here.");
      return;
    }

    const items = [
      ...folders.map(f => `📁 ${f.title} [${f.media_content_id}]`),
    ];

    const msg = `Select a folder to use as image source:\n\n${items.join("\n")}\n\nEnter the number (1-${folders.length}) or 0 to use current folder "${result.title}":`;
    const choice = prompt(msg);
    if (choice === null) return;

    const num = parseInt(choice);
    if (num === 0) {
      this._editingWidget.config = this._editingWidget.config || {};
      this._editingWidget.config.media_content_id = contentId;
      this._render();
    } else if (num >= 1 && num <= folders.length) {
      await this._browseMediaTree(folders[num - 1].media_content_id);
    }
  }

  _availableSpan(row, col) {
    let maxRows = 0, maxCols = 0;
    for (let rs = 1; rs <= GRID_ROWS - row; rs++) {
      for (let cs = 1; cs <= GRID_COLS - col; cs++) {
        // Check if the entire rectangle is free
        let free = true;
        for (let r = row; r < row + rs && free; r++)
          for (let c = col; c < col + cs && free; c++)
            if (this._widgetAt(r, c)) free = false;
        if (free) { maxRows = rs; maxCols = cs; }
      }
    }
    return { row_span: maxRows || 1, col_span: maxCols || 1 };
  }

  _onCellClick(row, col) {
    const widget = this._widgetAt(row, col);
    if (widget) {
      this._selectedCell = { row: widget.row, col: widget.col };
      this._editingWidget = JSON.parse(JSON.stringify(widget));
    } else {
      this._selectedCell = { row, col };
      const { row_span, col_span } = this._availableSpan(row, col);
      this._editingWidget = {
        type: "weather", row, col, row_span, col_span, config: {},
      };
    }
    this._render();
  }

  async _applyEdit() {
    const root = this.shadowRoot;
    const w = this._editingWidget;
    const rowSpan = root.querySelector("#w-row-span");
    const colSpan = root.querySelector("#w-col-span");
    if (rowSpan) w.row_span = parseInt(rowSpan.value) || 1;
    if (colSpan) w.col_span = parseInt(colSpan.value) || 1;
    (WIDGET_FIELDS[w.type] || []).forEach(f => {
      const el = root.querySelector(`#cfg-${f.key}`);
      if (el) {
        w.config = w.config || {};
        if (el.value !== "") w.config[f.key] = el.value;
        else delete w.config[f.key];
      }
    });

    const widgets = this._currentWidgets().filter(
      w => !(w.row === this._selectedCell.row && w.col === this._selectedCell.col)
    );
    widgets.push(JSON.parse(JSON.stringify(this._editingWidget)));
    this._layouts[this._activeLayout] = widgets;
    this._editingWidget = null;
    this._selectedCell = null;
    await this._persist();
    this._render();
    this._refreshPreview();
  }

  async _deleteWidget() {
    this._layouts[this._activeLayout] = this._currentWidgets().filter(
      w => !(w.row === this._selectedCell.row && w.col === this._selectedCell.col)
    );
    this._editingWidget = null;
    this._selectedCell = null;
    await this._persist();
    this._render();
    this._refreshPreview();
  }

  async _persist() {
    try {
      await this._hass.callService("eink", "set_options", {
        entry_id: this._selectedEntry.entry_id,
        layouts: this._layouts,
        active_layout: this._activeLayout,
        dither: this._dither,
      });
    } catch (e) {
      console.error("Failed to save eink options", e);
    }
  }

  _addLayout() {
    const name = prompt("New layout name:");
    if (!name) return;
    this._layouts[name] = [];
    this._activeLayout = name;
    this._render();
  }

  _deleteLayout() {
    if (Object.keys(this._layouts).length <= 1) return;
    if (!confirm(`Delete layout "${this._activeLayout}"?`)) return;
    delete this._layouts[this._activeLayout];
    this._activeLayout = Object.keys(this._layouts)[0];
    this._render();
  }

  _refreshPreview() {
    const img = this.shadowRoot.querySelector(".preview-img");
    if (!img || !this._token) return;
    img.src = `/api/eink/${this._token}.png?layout=${encodeURIComponent(this._activeLayout)}&t=${Date.now()}`;
  }

  _render() {
    const root = this.shadowRoot;
    root.innerHTML = `<style>${css}</style>`;

    if (!this._entries.length) {
      root.innerHTML += `<p>No E-Ink displays configured. Add one via Settings → Integrations.</p>`;
      return;
    }

    this._updateUrl();

    const token = this._token || "";
    const layoutNames = Object.keys(this._layouts);

    // Toolbar
    const toolbar = document.createElement("div");
    toolbar.className = "toolbar";
    toolbar.innerHTML = `
      <h1 style="margin:0">E-Ink Display</h1>
      ${this._entries.length > 1 ? `
        <select id="entry-select">
          ${this._entries.map(e => `<option value="${e.entry_id}" ${e.entry_id === this._selectedEntry?.entry_id ? "selected" : ""}>${e.title}</option>`).join("")}
        </select>` : `<strong>${this._selectedEntry?.title}</strong>`}
      <select id="layout-select">
        ${layoutNames.map(n => `<option value="${n}" ${n === this._activeLayout ? "selected" : ""}>${n}</option>`).join("")}
      </select>
      <button id="add-layout" class="secondary">+ Layout</button>
      <button id="del-layout" class="secondary danger">Delete layout</button>
      <label style="font-size:0.9em">Dither:
        <select id="dither-select">
          ${["none","floyd-steinberg","atkinson","jarvis"].map(v =>
            `<option value="${v}" ${v === this._dither ? "selected" : ""}>${v}</option>`
          ).join("")}
        </select>
      </label>
      <label style="display:flex;align-items:center;gap:4px;font-size:0.9em">
        <input type="checkbox" id="dither-toggle" ${this._dither ? "checked" : ""}> Dither images
      </label>
    `;
    root.appendChild(toolbar);

    // Main layout area
    const main = document.createElement("div");
    main.className = "main";

    // Left column: grid + preview
    const left = document.createElement("div");
    left.className = "left";

    // Grid
    const grid = document.createElement("div");
    grid.className = "grid";

    for (let r = 0; r < GRID_ROWS; r++) {
      for (let c = 0; c < GRID_COLS; c++) {
        const widget = this._widgetAt(r, c);
        const isOrigin = widget && widget.row === r && widget.col === c;
        const isSelected = this._selectedCell &&
          this._selectedCell.row === (widget?.row ?? r) &&
          this._selectedCell.col === (widget?.col ?? c);

        // Only render origin cell; skip non-origin occupied cells
        if (widget && !isOrigin) {
          const phantom = document.createElement("div");
          phantom.style.display = "none";
          grid.appendChild(phantom);
          continue;
        }

        const cell = document.createElement("div");
        cell.className = `cell${widget ? " occupied" : ""}${isSelected ? " selected" : ""}`;
        if (widget) {
          cell.style.gridRow = `${r + 1} / span ${widget.row_span || 1}`;
          cell.style.gridColumn = `${c + 1} / span ${widget.col_span || 1}`;
          cell.style.whiteSpace = "pre-line";
          cell.textContent = this._cellLabel(widget);
        }
        cell.dataset.row = r;
        cell.dataset.col = c;
        cell.addEventListener("click", () => this._onCellClick(r, c));
        grid.appendChild(cell);
      }
    }
    left.appendChild(grid);

    // Preview under grid
    const preview = document.createElement("div");
    preview.className = "preview";
    preview.innerHTML = `<img class="preview-img" src="/api/eink/${token}.png?layout=${encodeURIComponent(this._activeLayout)}&t=${Date.now()}" alt="Display preview">`;
    left.appendChild(preview);

    main.appendChild(left);

    // Sidebar
    const sidebar = document.createElement("div");
    sidebar.className = "sidebar";

    if (this._editingWidget) {
      const w = this._editingWidget;
      const fields = WIDGET_FIELDS[w.type] || [];
      sidebar.innerHTML = `
        <h3>${this._widgetAt(this._selectedCell.row, this._selectedCell.col) ? "Edit" : "Add"} widget at (${w.row},${w.col})</h3>
        <div class="field">
          <label>Type</label>
          <select id="w-type">
            ${WIDGET_TYPES.map(t => `<option value="${t}" ${t === w.type ? "selected" : ""}>${t}</option>`).join("")}
          </select>
        </div>
        <div class="span-row">
          <div class="field"><label>Row span</label><input id="w-row-span" type="number" min="1" max="${GRID_ROWS}" value="${w.row_span || 1}"></div>
          <div class="field"><label>Col span</label><input id="w-col-span" type="number" min="1" max="${GRID_COLS}" value="${w.col_span || 1}"></div>
        </div>
        ${fields.map(f => {
          const entities = f.domain
            ? Object.keys(this._hass.states).filter(id => id.startsWith(f.domain + "."))
            : [];
          const currentVal = w.config?.[f.key] || "";
          if (entities.length) {
            // Auto-default to first entity if nothing set — but only for required fields
            const isOptional = f.placeholder === "";
            if (!currentVal && !isOptional) {
              w.config = w.config || {};
              w.config[f.key] = entities[0];
            }
            const selected = w.config?.[f.key] || "";
            return `
              <div class="field">
                <label>${f.label}</label>
                <select id="cfg-${f.key}">
                  ${isOptional ? `<option value="">— none —</option>` : ""}
                  ${entities.map(e => `<option value="${e}" ${e === selected ? "selected" : ""}>${e}</option>`).join("")}
                </select>
              </div>`;
          }
          return `
            <div class="field">
              <label>${f.label}</label>
              <input id="cfg-${f.key}" type="${f.key === 'password' ? 'password' : 'text'}"
                placeholder="${f.placeholder}" value="${currentVal}">
            </div>`;
        }).join("")}
        ${w.type === "image" ? `
        <div class="field">
          <label>Media folder</label>
          <div style="display:flex;gap:6px;align-items:center">
            <span id="media-label" style="font-size:0.85em;color:#555;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              ${w.config?.media_content_id || "None selected"}
            </span>
            <button id="browse-media" class="secondary" style="white-space:nowrap">Browse…</button>
          </div>
        </div>` : ""}
        <div style="display:flex;gap:8px;margin-top:12px">
          <button id="apply-widget">Apply</button>
          <button id="cancel-widget" class="secondary">Close</button>
          ${this._widgetAt(this._selectedCell.row, this._selectedCell.col)
            ? `<button id="delete-widget" class="danger">Delete</button>` : ""}
        </div>
      `;
    } else {
      sidebar.innerHTML = `<p class="empty-hint">Click a cell to add or edit a widget.</p>`;
    }

    main.appendChild(sidebar);
    root.appendChild(main);

    // Event listeners
    root.querySelector("#add-layout")?.addEventListener("click", () => this._addLayout());
    root.querySelector("#del-layout")?.addEventListener("click", () => this._deleteLayout());
    root.querySelector("#dither-select")?.addEventListener("change", async e => {
      this._dither = e.target.value;
      await this._persist();
      this._refreshPreview();
    });

    root.querySelector("#entry-select")?.addEventListener("change", async e => {
      await this._selectEntry(e.target.value);
      this._updateUrl();
      this._render();
    });
    root.querySelector("#layout-select")?.addEventListener("change", e => {
      this._activeLayout = e.target.value;
      this._selectedCell = null;
      this._editingWidget = null;
      this._updateUrl();
      this._render();
    });

    if (this._editingWidget) {
      const w = this._editingWidget;
      root.querySelector("#w-type")?.addEventListener("change", e => {
        w.type = e.target.value;
        w.config = {};
        this._render();
      });
      root.querySelector("#w-row-span")?.addEventListener("input", e => { w.row_span = parseInt(e.target.value) || 1; });
      root.querySelector("#w-col-span")?.addEventListener("input", e => { w.col_span = parseInt(e.target.value) || 1; });
      (WIDGET_FIELDS[w.type] || []).forEach(f => {
        const el = root.querySelector(`#cfg-${f.key}`);
        if (el) el.addEventListener("change", e => {
          w.config = w.config || {};
          w.config[f.key] = e.target.value;
        });
        if (el) el.addEventListener("input", e => {
          w.config = w.config || {};
          w.config[f.key] = e.target.value;
        });
      });
      root.querySelector("#apply-widget")?.addEventListener("click", () => this._applyEdit());
      root.querySelector("#browse-media")?.addEventListener("click", () => this._openMediaBrowser());
      root.querySelector("#cancel-widget")?.addEventListener("click", () => {
        this._editingWidget = null;
        this._selectedCell = null;
        this._render();
      });
      root.querySelector("#delete-widget")?.addEventListener("click", () => this._deleteWidget());
    }
  }
}

customElements.define("eink-panel", EinkPanel);
