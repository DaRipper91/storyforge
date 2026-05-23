/**
 * REST + WebSocket wrappers for the StoryForge backend.
 */

const API_BASE = "";  // same-origin

async function jsonOrThrow(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }
  return res.json();
}

export async function fetchState() {
  const res = await fetch(`${API_BASE}/api/state`);
  return jsonOrThrow(res);
}

export async function fetchRevision() {
  const res = await fetch(`${API_BASE}/api/revision`);
  return jsonOrThrow(res);
}

export async function postGridAction({ actorId, type, target }) {
  const res = await fetch(`${API_BASE}/api/action/grid`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor_id: actorId, type, target }),
  });
  return jsonOrThrow(res);
}

export async function postFreeformAction({ actorId, text }) {
  const res = await fetch(`${API_BASE}/api/action/freeform`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor_id: actorId, text }),
  });
  return jsonOrThrow(res);
}

export async function fetchCatalog() {
  const res = await fetch(`${API_BASE}/api/lobby/catalog`);
  return jsonOrThrow(res);
}

export async function joinLobby(controllerId) {
  const res = await fetch(`${API_BASE}/api/lobby/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ controller_id: controllerId }),
  });
  return jsonOrThrow(res);
}

export async function leaveLobby(controllerId) {
  const res = await fetch(`${API_BASE}/api/lobby/leave`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ controller_id: controllerId }),
  });
  return jsonOrThrow(res);
}

export async function updateLobbyName({ slotIndex, name, controllerId }) {
  const res = await fetch(`${API_BASE}/api/lobby/update_name`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slot_index: slotIndex, name, controller_id: controllerId }),
  });
  return jsonOrThrow(res);
}

export async function setPhase(phase) {
  const res = await fetch(`${API_BASE}/api/lobby/set_phase`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phase }),
  });
  return jsonOrThrow(res);
}

export async function createCharacter({ slotIndex, name, race, evolutionState, predatorRole, abilities, startingEra }) {
  const res = await fetch(`${API_BASE}/api/character/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      slot_index: slotIndex,
      name,
      race,
      evolution_state: evolutionState,
      predator_role: predatorRole,
      abilities,
      starting_era: startingEra,
    }),
  });
  return jsonOrThrow(res);
}

export async function startGame() {
  const res = await fetch(`${API_BASE}/api/lobby/start`, {
    method: "POST",
  });
  return jsonOrThrow(res);
}

export async function triggerParadox() {
  const res = await fetch(`${API_BASE}/api/state/trigger_paradox`, {
    method: "POST",
  });
  return jsonOrThrow(res);
}

export async function fetchCampaigns() {
  const res = await fetch(`${API_BASE}/api/campaigns`);
  return jsonOrThrow(res);
}

export async function newCampaign() {
  const res = await fetch(`${API_BASE}/api/campaigns/new`, { method: "POST" });
  return jsonOrThrow(res);
}

export async function loadCampaign(campaignId) {
  const res = await fetch(`${API_BASE}/api/campaigns/load`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ campaign_id: campaignId }),
  });
  return jsonOrThrow(res);
}

// ── Authentication ───────────────────────────────────────────────

export async function loginGoogle(idToken) {
  const res = await fetch(`${API_BASE}/api/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: idToken }),
  });
  return jsonOrThrow(res);
}

export async function fetchAuthConfig() {
  const res = await fetch(`${API_BASE}/api/auth/config`);
  return jsonOrThrow(res);
}

export async function fetchMe() {
  const res = await fetch(`${API_BASE}/api/auth/me`);
  return jsonOrThrow(res);
}

export async function logout() {
  const res = await fetch(`${API_BASE}/api/auth/logout`, { method: "POST" });
  return jsonOrThrow(res);
}

// ── Jon / NPC encounter API ──────────────────────────────────────

export async function jonGetInventory(genre = "fantasy") {
  const res = await fetch(`${API_BASE}/api/npc/jon/inventory?genre=${genre}`);
  return jsonOrThrow(res);
}

export async function jonBuy({ actorId, itemId, genre = "fantasy" }) {
  const res = await fetch(`${API_BASE}/api/npc/jon/buy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor_id: actorId, item_id: itemId, genre }),
  });
  return jsonOrThrow(res);
}

export async function jonCactus(isLewdOrMocking = false) {
  const res = await fetch(`${API_BASE}/api/npc/jon/cactus`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_lewd_or_mocking: isLewdOrMocking }),
  });
  return jsonOrThrow(res);
}

export async function jonEscape({ actorId, method = "smooth_talk", advantage = false, disadvantage = false }) {
  const res = await fetch(`${API_BASE}/api/npc/jon/escape`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor_id: actorId, method, advantage, disadvantage }),
  });
  return jsonOrThrow(res);
}

export async function jonGetState() {
  const res = await fetch(`${API_BASE}/api/npc/jon/state`);
  return jsonOrThrow(res);
}

export async function jonTick() {
  const res = await fetch(`${API_BASE}/api/npc/jon/tick`, { method: "POST" });
  return jsonOrThrow(res);
}

// ── Samael the Ascended ───────────────────────────────────────────

export async function samaelConsult(category = "general_lore") {
  const res = await fetch(`${API_BASE}/api/npc/samael/consult`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category }),
  });
  return jsonOrThrow(res);
}

export async function samaelGetState() {
  const res = await fetch(`${API_BASE}/api/npc/samael/state`);
  return jsonOrThrow(res);
}

// ── Madame Haylie ─────────────────────────────────────────────────

export async function hailieBailout(genre = "fantasy") {
  const res = await fetch(`${API_BASE}/api/npc/haylie/bailout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ genre }),
  });
  return jsonOrThrow(res);
}

export async function hailieGetState() {
  const res = await fetch(`${API_BASE}/api/npc/haylie/state`);
  return jsonOrThrow(res);
}

// ── Queen D.Anna ──────────────────────────────────────────────────

export async function dannaAddress(form = "proper") {
  const res = await fetch(`${API_BASE}/api/npc/danna/address`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ form }),
  });
  return jsonOrThrow(res);
}

export async function dannaPetition(petitionType = "blessing") {
  const res = await fetch(`${API_BASE}/api/npc/danna/petition`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ petition_type: petitionType }),
  });
  return jsonOrThrow(res);
}

export async function dannaGetState() {
  const res = await fetch(`${API_BASE}/api/npc/danna/state`);
  return jsonOrThrow(res);
}

// ── Firey RedVelvet ───────────────────────────────────────────────

export async function rvPerform() {
  const res = await fetch(`${API_BASE}/api/npc/redvelvet/perform`, { method: "POST" });
  return jsonOrThrow(res);
}

export async function rvTip(silver = 5) {
  const res = await fetch(`${API_BASE}/api/npc/redvelvet/tip`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ silver }),
  });
  return jsonOrThrow(res);
}

export async function rvHeckle() {
  const res = await fetch(`${API_BASE}/api/npc/redvelvet/heckle`, { method: "POST" });
  return jsonOrThrow(res);
}

export async function rvRequestSong(songType = "mystery") {
  const res = await fetch(`${API_BASE}/api/npc/redvelvet/request-song`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ song_type: songType }),
  });
  return jsonOrThrow(res);
}

export async function rvGetState() {
  const res = await fetch(`${API_BASE}/api/npc/redvelvet/state`);
  return jsonOrThrow(res);
}

/**
 * Open a WebSocket and call onMessage for every state_diff event.
 */
export function openSession({ roomId, onMessage, onConnect, onDisconnect }) {
  let ws = null;
  let backoff = 500;
  const MAX_BACKOFF = 8000;
  let alive = true;

  function connect() {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${window.location.host}/ws/session/${roomId}`);
    ws.addEventListener("open", () => {
      backoff = 500;
      onConnect?.();
    });
    ws.addEventListener("message", (e) => {
      try {
        onMessage(JSON.parse(e.data));
      } catch (err) {
        console.error("[ws] bad message", err, e.data);
      }
    });
    ws.addEventListener("close", () => {
      onDisconnect?.();
      if (!alive) return;
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, MAX_BACKOFF);
    });
    ws.addEventListener("error", () => ws?.close());
  }

  connect();
  return {
    close() { alive = false; ws?.close(); },
  };
}
