/**
 * Konva-based 10x8 grid renderer with HiDPI awareness.
 */

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
  constructor({ mountEl, onCellConfirmed, onCellInspected }) {
    this.mountEl = mountEl;
    this.onCellConfirmed = onCellConfirmed;
    this.onCellInspected = onCellInspected;

    this.state = null;
    this.cursor = { x: 0, y: 0 };
    this.cellSize = 64;

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
    this._tokenNodes = new Map();
    this._lightCircles = new Map(); // id -> Circle

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
    const cellW = (w - padding * 2) / room.width;
    const cellH = (h - padding * 2) / room.height;
    
    // Use a minimum cell size to ensure the grid is large enough to "feel" like a game board
    const minCellSize = 100;
    this.cellSize = Math.max(minCellSize, Math.floor(Math.min(cellW, cellH)));

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
          // Calculate distance for bounce effect
          const dx = targetCx - group.x();
          const dy = targetCy - group.y();
          const dist = Math.sqrt(dx*dx + dy*dy);
          
          if (dist > 5) {
            // Animate
            new Konva.Tween({
              node: group,
              duration: 0.3,
              x: targetCx,
              y: targetCy,
              easing: Konva.Easings.EaseInOut,
            }).play();
            
            // Add a small squash/stretch on movement
            const ring = group.getChildren()[0];
            new Konva.Tween({
              node: ring,
              duration: 0.15,
              scaleX: 1.1,
              scaleY: 0.9,
              yoyo: true,
              easing: Konva.Easings.EaseInOut,
            }).play();
          } else {
            // Resize edge case or tiny shift, jump directly
            group.x(targetCx);
            group.y(targetCy);
            // Also need to resize the children if cellSize changed
            const ring = group.getChildren()[0];
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
    const cs = this.cellSize;
    const { x, y } = this.cursor;

    // Target position for the stage to center the cursor
    // Center of cursor in stage coordinates (relative to stage origin):
    const cursorCx = this.offsetX + x * cs + cs / 2;
    const cursorCy = this.offsetY + y * cs + cs / 2;

    const targetX = this.stage.width() / 2 - cursorCx;
    const targetY = this.stage.height() / 2 - cursorCy;

    if (instant) {
      this.stage.position({ x: targetX, y: targetY });
    } else {
      // Smooth follow
      if (this._cameraTween) this._cameraTween.stop();
      this._cameraTween = new Konva.Tween({
        node: this.stage,
        duration: 0.3,
        x: targetX,
        y: targetY,
        easing: Konva.Easings.EaseOut
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
