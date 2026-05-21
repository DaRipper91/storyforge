/**
 * Konva-based 10x8 grid renderer with HiDPI awareness.
 */
import { getRaceFrames, RACE_ACCENT_COLORS, renderSprite, flipH } from './sprites.js';

// Moves longer than this many cells trigger the 8-bit walk sprite.
const LONG_WALK_CELLS = 3;
// Walk speed in cells per second during sprite animation.
const WALK_SPEED_CELLS = 2.5;
// Sprite animation frames per second.
const SPRITE_FPS = 8;

const TERRAIN_COLORS = {
  floor:     "rgba(244, 234, 212, 0.0)",
  wall:      "rgba(40, 24, 12, 0.92)",
  door:      "rgba(120, 70, 30, 0.85)",
  difficult: "rgba(140, 100, 60, 0.35)",
  hazard:    "rgba(180, 50, 30, 0.55)",
};

const CHARACTER_COLORS = {
  cody: "#5a1622",
  dee:  "#4a1a6b",
  nate: "#1e5a3a",
  bray: "#1a1428",
};

export class GridCanvas {
  constructor({ mountEl, onCellConfirmed, onCellInspected, onZoomChanged }) {
    this.mountEl = mountEl;
    this.onCellConfirmed = onCellConfirmed;
    this.onCellInspected = onCellInspected;
    this.onZoomChanged = onZoomChanged;

    this.state = null;
    this.cursor = { x: 0, y: 0 };
    this.cellSize = 64;
    this.zoomLevel = 0.7; // <1.0 = zoomed out from fit, 1.0 = fit to screen, >1.0 = zoomed in

    this._initStage();
    this._observeResize();
  }

  _initStage() {
    Konva.pixelRatio = window.devicePixelRatio || 1;

    this.stage = new Konva.Stage({
      container: this.mountEl,
      width: this.mountEl.clientWidth,
      height: this.mountEl.clientHeight,
    });

    this.gridLayer   = new Konva.Layer({ listening: true });
    this.tokenLayer  = new Konva.Layer({ listening: false });
    this.lightLayer  = new Konva.Layer({ listening: false }); // Fog of War
    this.fxLayer     = new Konva.Layer({ listening: false }); // Particles & floating text
    this.cursorLayer = new Konva.Layer({ listening: false });

    this.stage.add(this.gridLayer);
    this.stage.add(this.tokenLayer);
    this.stage.add(this.lightLayer);
    this.stage.add(this.fxLayer);
    this.stage.add(this.cursorLayer);

    // Keep track of token nodes for tweening
    this._tokenNodes  = new Map();
    this._lightCircles = new Map(); // id -> Circle
    this._walkingChars = new Set(); // ids currently doing sprite walk

    // Mouse/Touch Interaction
    this.stage.on("mousedown touchstart", (e) => {
      const pos = this.stage.getPointerPosition();
      if (!pos) return;

      const coord = this._pixelToGrid(pos.x, pos.y);
      if (coord) {
        this.setCursor(coord);
      }
    });

    this.stage.on("click tap", (e) => {
      const pos = this.stage.getPointerPosition();
      if (!pos) return;
      const coord = this._pixelToGrid(pos.x, pos.y);
      if (coord) {
        if (e.evt.button === 2) {
          this.inspectCursor();
        } else {
          this.onCellConfirmed?.(coord);
        }
      }
    });

    this.stage.container().addEventListener("contextmenu", (e) => e.preventDefault());

    // Wheel Zoom
    this.stage.container().addEventListener("wheel", (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      this.adjustZoom(delta);
    });

    this.stage.on("mousemove", (e) => {
      const pos = this.stage.getPointerPosition();
      if (!pos) return;
      const coord = this._pixelToGrid(pos.x, pos.y);
      if (coord && (coord.x !== this.cursor.x || coord.y !== this.cursor.y)) {
        this.setCursor(coord);
      }
    });

    this._startAmbientParticles();
    this._startLightingAnimation();
  }

  adjustZoom(delta) {
    const oldZoom = this.zoomLevel;
    this.zoomLevel = Math.max(0.4, Math.min(2.5, this.zoomLevel + delta));
    if (this.zoomLevel !== oldZoom) {
      this._fitAndRedraw();
      this.onZoomChanged?.(this.zoomLevel);
    }
  }

  _startLightingAnimation() {
    this._lightingAnim = new Konva.Animation((frame) => {
      if (!this.state) return;
      const cs = this.cellSize;
      
      for (const [id, circle] of this._lightCircles.entries()) {
        const tokenNode = this._tokenNodes.get(id);
        if (tokenNode) {
          circle.x(tokenNode.x());
          circle.y(tokenNode.y());
          
          // Subtle flicker
          const baseRadius = cs * 4.5;
          const flicker = Math.sin(frame.time / 100) * 5 + (Math.random() * 4 - 2);
          circle.radius(baseRadius + flicker);
        } else {
          circle.destroy();
          this._lightCircles.delete(id);
        }
      }
    }, this.lightLayer);
    this._lightingAnim.start();
  }

  _startAmbientParticles() {
    this._particleAnim = new Konva.Animation((frame) => {
      // Spawn new particle occasionally
      if (Math.random() < 0.05) {
        const sx = this.stage.x();
        const sy = this.stage.y();
        const sw = this.stage.width();
        const sh = this.stage.height();

        const p = new Konva.Circle({
          x: (Math.random() * sw) - sx,
          y: (sh + 10) - sy,
          radius: Math.random() * 2 + 1,
          fill: '#ffaa00',
          opacity: 0.6,
          shadowColor: '#ff0000',
          shadowBlur: 5,
        });
        
        // Custom properties for drift
        p.driftX = (Math.random() - 0.5) * 1.5;
        p.speedY = Math.random() * 0.5 + 0.5;
        p.life = 0;
        
        this.fxLayer.add(p);
      }

      // Update existing particles
      for (const node of this.fxLayer.getChildren()) {
        if (node.getClassName() === 'Circle') {
          node.y(node.y() - node.speedY);
          node.x(node.x() + node.driftX + Math.sin(node.life / 20) * 0.5);
          node.life++;
          node.opacity(node.opacity() - 0.002);
          
          if (node.opacity() <= 0 || node.y() < -10) {
            node.destroy();
          }
        }
      }
    }, this.fxLayer);
    this._particleAnim.start();
  }

  spawnFloatingText(coord, text, color = "#ff4444") {
    const cs = this.cellSize;
    const ox = this.offsetX, oy = this.offsetY;
    const cx = ox + coord.x * cs + cs / 2;
    const cy = oy + coord.y * cs;

    const t = new Konva.Text({
      x: cx - 100,
      y: cy - 20,
      width: 200,
      text: text,
      fontSize: 24,
      fontFamily: "Cardo, serif",
      fontWeight: "bold",
      fill: color,
      align: "center",
      shadowColor: "black",
      shadowBlur: 4,
      opacity: 1
    });

    this.fxLayer.add(t);

    new Konva.Tween({
      node: t,
      duration: 1.5,
      y: cy - 60,
      opacity: 0,
      easing: Konva.Easings.EaseOut,
      onFinish: () => t.destroy()
    }).play();
  }

  _pixelToGrid(px, py) {
    if (!this.state) return null;
    const room = this._currentRoom();
    
    // Account for stage panning
    const internalX = px - this.stage.x();
    const internalY = py - this.stage.y();

    const x = Math.floor((internalX - this.offsetX) / this.cellSize);
    const y = Math.floor((internalY - this.offsetY) / this.cellSize);
    
    if (x >= 0 && x < room.width && y >= 0 && y < room.height) {
      return { x, y };
    }
    return null;
  }

  _observeResize() {
    const ro = new ResizeObserver(() => this._fitAndRedraw());
    ro.observe(this.mountEl);
  }

  _fitAndRedraw() {
    if (!this.state) return;
    const w = this.mountEl.clientWidth;
    const h = this.mountEl.clientHeight;
    this.stage.size({ width: w, height: h });

    const room = this._currentRoom();
    const padding = 32;
    const baseCellW = (w - padding * 2) / room.width;
    const baseCellH = (h - padding * 2) / room.height;
    
    // cellSize is the "fit to screen" size multiplied by current zoomLevel
    const baseCellSize = Math.floor(Math.min(baseCellW, baseCellH));
    this.cellSize = Math.floor(baseCellSize * this.zoomLevel);

    // Initial offsets (unpanned)
    this.offsetX = Math.floor((w - this.cellSize * room.width) / 2);
    this.offsetY = Math.floor((h - this.cellSize * room.height) / 2);

    this.renderAll();
    this._followCursor(true);
  }

  setState(state) {
    const firstTime = !this.state;
    this.state = state;
    this._fitAndRedraw();
    if (firstTime) {
      this._followCursor(true);
    }
  }

  _currentRoom() {
    return this.state.rooms[this.state.current_room_id];
  }

  renderAll() {
    if (!this.state) return;
    this._renderGrid();
    this._renderTokens();
    this._renderNpcs();
    this._renderLighting();
    this._renderCursor();
  }

  _renderLighting() {
    // Re-create the darkness layer if it doesn't exist or sizing changed
    let lightGroup = this.lightLayer.findOne('.light-group');
    if (!lightGroup) {
      this.lightLayer.destroyChildren();
      lightGroup = new Konva.Group({ name: 'light-group' });
      
      // Make the darkness rect large enough to cover the room plus plenty of padding for panning
      const darkness = new Konva.Rect({
        x: -2000, y: -2000,
        width: 10000,
        height: 10000,
        fill: 'rgba(10, 5, 10, 0.85)',
        listening: false
      });
      lightGroup.add(darkness);
      this.lightLayer.add(lightGroup);
    }

    const cs = this.cellSize;
    const ox = this.offsetX, oy = this.offsetY;

    // Sync light circles with characters
    for (const char of Object.values(this.state.characters)) {
      let light = this._lightCircles.get(char.id);
      if (!light) {
        const { x, y } = char.position;
        const cx = ox + x * cs + cs / 2;
        const cy = oy + y * cs + cs / 2;
        
        light = new Konva.Circle({
          x: cx,
          y: cy,
          radius: cs * 4.5,
          fillRadialGradientStartPoint: { x: 0, y: 0 },
          fillRadialGradientStartRadius: cs,
          fillRadialGradientEndPoint: { x: 0, y: 0 },
          fillRadialGradientEndRadius: cs * 4.5,
          fillRadialGradientColorStops: [
            0, 'rgba(0,0,0,1)',
            0.6, 'rgba(0,0,0,0.8)',
            1, 'rgba(0,0,0,0)'
          ],
          globalCompositeOperation: 'destination-out'
        });
        lightGroup.add(light);
        this._lightCircles.set(char.id, light);
      }
    }

    this.lightLayer.batchDraw();
  }

  _renderGrid() {
    this.gridLayer.destroyChildren();
    const room = this._currentRoom();
    const cs = this.cellSize;
    const ox = this.offsetX, oy = this.offsetY;

    for (let y = 0; y < room.height; y++) {
      for (let x = 0; x < room.width; x++) {
        const cell = room.cells[y * room.width + x];
        const fill = TERRAIN_COLORS[cell.terrain] ?? TERRAIN_COLORS.floor;

        const rect = new Konva.Rect({
          x: ox + x * cs,
          y: oy + y * cs,
          width: cs,
          height: cs,
          fill: fill,
          stroke: "rgba(40, 24, 12, 0.75)",
          strokeWidth: 2,
          perfectDrawEnabled: false,
        });
        this.gridLayer.add(rect);
      }
    }

    for (let i = 0; i <= room.width; i += 5) {
      this.gridLayer.add(new Konva.Line({
        points: [ox + i * cs, oy, ox + i * cs, oy + room.height * cs],
        stroke: "rgba(40, 24, 12, 0.95)",
        strokeWidth: 3,
      }));
    }
    for (let j = 0; j <= room.height; j += 5) {
      this.gridLayer.add(new Konva.Line({
        points: [ox, oy + j * cs, ox + room.width * cs, oy + j * cs],
        stroke: "rgba(40, 24, 12, 0.95)",
        strokeWidth: 3,
      }));
    }
    this.gridLayer.batchDraw();
  }

  _renderTokens() {
    // We don't destroy children anymore; we update or create them.
    const cs = this.cellSize;
    const ox = this.offsetX, oy = this.offsetY;

    // Remove tokens that are no longer in state
    for (const [id, node] of this._tokenNodes.entries()) {
      if (!this.state.characters[id]) {
        node.destroy();
        this._tokenNodes.delete(id);
      }
    }

    for (const char of Object.values(this.state.characters)) {
      const { x, y } = char.position;
      const targetCx = ox + x * cs + cs / 2;
      const targetCy = oy + y * cs + cs / 2;

      let group = this._tokenNodes.get(char.id);

      if (!group) {
        // Create new token
        group = new Konva.Group({ id: `token-${char.id}`, x: targetCx, y: targetCy });
        
        const ring = new Konva.Circle({
          x: 0, y: 0,
          radius: cs * 0.4,
          fill: CHARACTER_COLORS[char.id] ?? "#444",
          stroke: "#f4ead4",
          strokeWidth: 5,
          shadowColor: "black",
          shadowBlur: 8,
          shadowOpacity: 0.45,
        });

        const initial = new Konva.Text({
          x: -cs / 2, y: -cs / 2,
          width: cs, height: cs,
          text: char.name[0],
          fontFamily: "Cardo, Georgia, serif",
          fontSize: Math.floor(cs * 0.5),
          fontStyle: "bold",
          fill: "#f4ead4",
          align: "center",
          verticalAlign: "middle",
          listening: false,
        });

        group.add(ring);
        group.add(initial);
        this.tokenLayer.add(group);
        this._tokenNodes.set(char.id, group);
      } else {
        // Tween to new position if it moved
        if (group.x() !== targetCx || group.y() !== targetCy) {
          const dx   = targetCx - group.x();
          const dy   = targetCy - group.y();
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist > 5) {
            const distCells = dist / cs;

            if (distCells >= LONG_WALK_CELLS && !this._walkingChars.has(char.id)) {
              // ── Long-distance: play 8-bit sprite walk ──────────────
              this._startSpriteWalk(char, group, group.x(), group.y(), targetCx, targetCy);
            } else if (!this._walkingChars.has(char.id)) {
              // ── Short hop: normal smooth tween ─────────────────────
              new Konva.Tween({
                node: group,
                duration: 0.3,
                x: targetCx,
                y: targetCy,
                easing: Konva.Easings.EaseInOut,
              }).play();

              const ring = group.getChildren()[0];
              new Konva.Tween({
                node: ring,
                duration: 0.15,
                scaleX: 1.1,
                scaleY: 0.9,
                yoyo: true,
                easing: Konva.Easings.EaseInOut,
              }).play();
            }
            // else: sprite walk in progress — do nothing until it finishes
          } else {
            // Resize edge case or tiny shift, jump directly
            group.x(targetCx);
            group.y(targetCy);
            const ring    = group.getChildren()[0];
            const initial = group.getChildren()[1];
            ring.radius(cs * 0.4);
            initial.width(cs);
            initial.height(cs);
            initial.x(-cs / 2);
            initial.y(-cs / 2);
            initial.fontSize(Math.floor(cs * 0.5));
          }
        }
      }
    }
    this.tokenLayer.batchDraw();
  }

  /**
   * Play an 8-bit walking sprite from (fromCx,fromCy) to (toCx,toCy).
   * The normal circular token is hidden while the sprite is in motion
   * and restored (at the new position) when the animation completes.
   */
  _startSpriteWalk(char, group, fromCx, fromCy, toCx, toCy) {
    this._walkingChars.add(char.id);

    const cs         = this.cellSize;
    const charColor  = CHARACTER_COLORS[char.id] ?? '#8B4513';
    const scale      = Math.max(3, Math.round(cs / 10));
    const spriteSize = 8 * scale;

    const dx   = toCx - fromCx;
    const dy   = toCy - fromCy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const facingLeft = dx < 0;

    // Pre-render all 4 frames (flipped if walking left)
    const raceFrames = getRaceFrames(char.race);
    const accent = RACE_ACCENT_COLORS[char.race] ?? '#f4ead4';
    const frames = raceFrames.map(f =>
      renderSprite(facingLeft ? flipH(f) : f, charColor, scale, accent)
    );

    // Sprite image node — positioned so feet land at the cell centre
    let currentFrameIdx = 0;
    const img = new Konva.Image({
      image:  frames[0],
      x:      fromCx - spriteSize / 2,
      y:      fromCy - spriteSize,
      width:  spriteSize,
      height: spriteSize,
      listening: false,
      shadowColor:   'black',
      shadowBlur:    8,
      shadowOpacity: 0.4,
    });
    this.tokenLayer.add(img);
    group.hide();

    // Duration based on travel distance and walk speed
    const totalDuration = dist / (cs * WALK_SPEED_CELLS);  // seconds
    const startMs       = Date.now();

    // Spawn a dust puff at the sprite's feet
    const _spawnDust = (x, y) => {
      for (let i = 0; i < 3; i++) {
        const puff = new Konva.Circle({
          x: x + (Math.random() - 0.5) * spriteSize * 0.6,
          y: y + 2,
          radius: Math.random() * 3 + 2,
          fill: '#c9a14a',
          opacity: 0.55,
          listening: false,
        });
        this.fxLayer.add(puff);
        new Konva.Tween({
          node: puff,
          duration: 0.4 + Math.random() * 0.3,
          y:        y - 10 - Math.random() * 8,
          opacity:  0,
          scaleX:   2,
          scaleY:   2,
          easing:   Konva.Easings.EaseOut,
          onFinish: () => puff.destroy(),
        }).play();
      }
    };

    let lastDustProgress = 0;

    const walkAnim = new Konva.Animation((frame) => {
      const elapsed  = (Date.now() - startMs) / 1000;
      const progress = Math.min(1, elapsed / totalDuration);

      // Advance sprite position
      const cx = fromCx + dx * progress;
      const cy = fromCy + dy * progress;
      img.x(cx - spriteSize / 2);
      img.y(cy - spriteSize);

      // Cycle animation frames
      const fi = Math.floor(elapsed * SPRITE_FPS) % frames.length;
      if (fi !== currentFrameIdx) {
        currentFrameIdx = fi;
        img.image(frames[fi]);
      }

      // Spawn dust every ~0.5 cells of travel
      if (progress - lastDustProgress > (cs * 0.5) / dist) {
        _spawnDust(cx, cy);
        lastDustProgress = progress;
      }

      if (progress >= 1) {
        walkAnim.stop();
        img.destroy();
        // Teleport the group to the destination before unhiding
        group.x(toCx);
        group.y(toCy);
        group.show();
        this._walkingChars.delete(char.id);
        this.tokenLayer.batchDraw();
      }
    }, this.tokenLayer);

    walkAnim.start();
  }

  _renderNpcs() {
    // NPC tokens: distinct look from player tokens (diamond shape, muted gold).
    // Non-player NPCs (Bink Bink, Teddy, Cyrus) show at their position even
    // though they don't occupy a grid cell for pathfinding.
    if (!this.state.npcs) return;

    const cs = this.cellSize;
    const ox = this.offsetX, oy = this.offsetY;

    const currentRoomId = this.state.current_room_id;

    // Remove stale NPC nodes: NPC deleted OR NPC belongs to a different room
    for (const [id, node] of this._tokenNodes.entries()) {
      if (!id.startsWith("npc_")) continue;
      const npcId = id.slice(4);
      const npc = this.state.npcs[npcId];
      if (!npc || (npc.room_id && npc.room_id !== currentRoomId)) {
        node.destroy();
        this._tokenNodes.delete(id);
      }
    }

    const NPC_COLORS = {
      npc_jon:      "#8B4513",  // saddle brown — shopkeeper warmth
      npc_cat:      "#1a1a1a",  // dark charcoal — mysterious black feline
      npc_dog:      "#D2691E",  // chocolate — loyal hound
      npc_default:  "#556B2F",
      npc_samael:   "#4B0082",
      npc_haylie:   "#8B0000",
      npc_danna:    "#4a1060",  // deep regal purple
      npc_redvelvet:"#8B1a1a",  // deep crimson-red
      npc_keeva:    "#F8F8FF",  // ghost white — angelic hound
      npc_teddy:    "#B8860B",  // dark goldenrod — heavenly protector
    };

    for (const npc of Object.values(this.state.npcs)) {
      // Skip NPCs assigned to a different room
      if (npc.room_id && npc.room_id !== currentRoomId) continue;
      const nodeKey = `npc_${npc.id}`;
      const cx = ox + npc.position.x * cs + cs / 2;
      const cy = oy + npc.position.y * cs + cs / 2;
      const color = NPC_COLORS[npc.sprite_key] ?? NPC_COLORS.npc_default;
      const r = cs * 0.35;

      let group = this._tokenNodes.get(nodeKey);
      if (!group) {
        group = new Konva.Group({ id: nodeKey, x: cx, y: cy });

        // Diamond shape for NPCs
        const diamond = new Konva.RegularPolygon({
          x: 0, y: 0,
          sides: 4,
          radius: r,
          fill: color,
          stroke: "#f4ead4",
          strokeWidth: 3,
          rotation: 45,
          shadowColor: "black",
          shadowBlur: 6,
          shadowOpacity: 0.4,
        });

        const label = new Konva.Text({
          x: -cs / 2, y: -cs / 2,
          width: cs, height: cs,
          text: npc.name[0],
          fontFamily: "Cardo, Georgia, serif",
          fontSize: Math.floor(cs * 0.4),
          fontStyle: "bold",
          fill: "#f4ead4",
          align: "center",
          verticalAlign: "middle",
          listening: false,
        });

        group.add(diamond);
        group.add(label);
        this.tokenLayer.add(group);
        this._tokenNodes.set(nodeKey, group);

        // Idle pulse animation for interactable NPCs
        if (npc.interactable) {
          const pulse = new Konva.Animation((frame) => {
            const scale = 1 + 0.06 * Math.sin(frame.time / 600);
            diamond.scaleX(scale);
            diamond.scaleY(scale);
          }, this.tokenLayer);
          pulse.start();
        }
      } else {
        group.x(cx);
        group.y(cy);
      }
    }
    this.tokenLayer.batchDraw();
  }

  _renderCursor() {
    this.cursorLayer.destroyChildren();
    if (!this.state) return;

    const cs = this.cellSize;
    const ox = this.offsetX, oy = this.offsetY;
    const { x, y } = this.cursor;

    // Outer flame glow
    const outerGlow = new Konva.Rect({
      x: ox + x * cs + 2,
      y: oy + y * cs + 2,
      width: cs - 4,
      height: cs - 4,
      stroke: "#ff4500",
      strokeWidth: 4,
      cornerRadius: 4,
      shadowColor: "#ff4500",
      shadowBlur: 20,
      shadowOpacity: 0.8,
    });

    // Inner core glow
    const innerGlow = new Konva.Rect({
      x: ox + x * cs + 6,
      y: oy + y * cs + 6,
      width: cs - 12,
      height: cs - 12,
      stroke: "#ffd700",
      strokeWidth: 2,
      cornerRadius: 4,
      shadowColor: "#ffd700",
      shadowBlur: 10,
      shadowOpacity: 0.9,
    });

    this.cursorLayer.add(outerGlow);
    this.cursorLayer.add(innerGlow);

    this._cursorAnim?.stop();
    this._cursorAnim = new Konva.Animation((frame) => {
      const flicker = Math.sin(frame.time / 50) * 0.2 + 0.8;
      const pulse = Math.sin(frame.time / 100) * 2;
      
      outerGlow.shadowBlur(20 + pulse * 4);
      outerGlow.opacity(0.6 + flicker * 0.4);
      
      innerGlow.shadowBlur(10 + pulse * 2);
      innerGlow.opacity(0.7 + flicker * 0.3);
      
      // Slightly wobble the rects
      outerGlow.x(ox + x * cs + 2 + Math.random() * 2 - 1);
      outerGlow.y(oy + y * cs + 2 + Math.random() * 2 - 1);
    }, this.cursorLayer);
    this._cursorAnim.start();
  }

  setCursor({ x, y }) {
    if (!this.state) return;
    const room = this._currentRoom();
    const oldX = this.cursor.x;
    const oldY = this.cursor.y;
    
    this.cursor.x = Math.max(0, Math.min(room.width  - 1, x));
    this.cursor.y = Math.max(0, Math.min(room.height - 1, y));
    
    if (this.cursor.x !== oldX || this.cursor.y !== oldY) {
      this._renderCursor();
      this._followCursor();
    }
  }

  _followCursor(instant = false) {
    if (!this.state) return;

    // At zoom 1.0 the whole grid fits the canvas — offsetX/Y already center it,
    // so stage stays at (0,0) and no panning is needed.
    if (this.zoomLevel <= 1.0) {
      if (instant) {
        this.stage.position({ x: 0, y: 0 });
      } else {
        if (this._cameraTween) this._cameraTween.stop();
        this._cameraTween = new Konva.Tween({
          node: this.stage, duration: 0.3, x: 0, y: 0,
          easing: Konva.Easings.EaseOut,
        });
        this._cameraTween.play();
      }
      return;
    }

    // Zoomed in — pan so the cursor cell stays centred on screen.
    const cs = this.cellSize;
    const { x, y } = this.cursor;
    const cursorCx = this.offsetX + x * cs + cs / 2;
    const cursorCy = this.offsetY + y * cs + cs / 2;
    const targetX = this.stage.width()  / 2 - cursorCx;
    const targetY = this.stage.height() / 2 - cursorCy;

    if (instant) {
      this.stage.position({ x: targetX, y: targetY });
    } else {
      if (this._cameraTween) this._cameraTween.stop();
      this._cameraTween = new Konva.Tween({
        node: this.stage,
        duration: 0.3,
        x: targetX,
        y: targetY,
        easing: Konva.Easings.EaseOut,
      });
      this._cameraTween.play();
    }
  }

  shake(intensity = 10, duration = 500) {
    const start = Date.now();
    const startX = this.stage.x();
    const startY = this.stage.y();
    
    const anim = new Konva.Animation((frame) => {
      const elapsed = Date.now() - start;
      if (elapsed > duration) {
        anim.stop();
        this.stage.x(startX);
        this.stage.y(startY);
        return;
      }
      const decay = 1 - (elapsed / duration);
      const curIntensity = intensity * decay;
      this.stage.x(startX + (Math.random() - 0.5) * curIntensity);
      this.stage.y(startY + (Math.random() - 0.5) * curIntensity);
    }, [this.gridLayer, this.tokenLayer, this.cursorLayer, this.fxLayer, this.lightLayer]);
    anim.start();
  }

  moveCursor(dx, dy) {
    this.setCursor({ x: this.cursor.x + dx, y: this.cursor.y + dy });
  }

  confirmCursor() {
    this.onCellConfirmed?.({ x: this.cursor.x, y: this.cursor.y });
  }

  inspectCursor() {
    const room = this._currentRoom();
    const cell = room.cells[this.cursor.y * room.width + this.cursor.x];
    this.onCellInspected?.({ coord: { ...this.cursor }, cell });
  }
}
