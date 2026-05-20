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

export async function createCharacter({ slotIndex, name, race, evolutionState, predatorRole, abilities }) {
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
