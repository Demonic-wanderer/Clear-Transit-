const shipmentsList = document.getElementById("shipments-list");
const shipmentForm = document.getElementById("shipment-form");
const formTitle = document.getElementById("form-title");
const routeIdInput = document.getElementById("route-id");
const searchInput = document.getElementById("search-input");
const refreshButton = document.getElementById("refresh-btn");
const seedButton = document.getElementById("seed-btn");
const resetFormButton = document.getElementById("reset-form-btn");
const cancelEditButton = document.getElementById("cancel-edit-btn");
const logoutButton = document.getElementById("logout-btn");
const themeToggleButton = document.getElementById("theme-toggle-btn");
const dashboardButton = document.getElementById("dashboard-btn");
const pageBanner = document.getElementById("page-banner");
const resultCount = document.getElementById("result-count");
const summaryGrid = document.getElementById("summary-grid");

const THEME_STORAGE_KEY = "clear-transit-theme";

let shipments = [];
let options = { hubs: [], statuses: [] };
let activeFilter = "all";

function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function updateThemeToggleLabel() {
  const theme = currentTheme();
  themeToggleButton.textContent = theme === "dark" ? "Dark mode" : "Light mode";
  themeToggleButton.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  updateThemeToggleLabel();
}

function showBanner(message, tone = "success") {
  pageBanner.textContent = message;
  pageBanner.className = `page-banner ${tone}`;
}

function hideBanner() {
  pageBanner.textContent = "";
  pageBanner.className = "page-banner hidden";
}

function severityClass(route) {
  if (route.status === "REROUTED" || route.risk_score >= 70) {
    return "status-high";
  }
  if (route.status === "WATCHLIST" || route.risk_score >= 50) {
    return "status-medium";
  }
  return "status-low";
}

function statusTone(status) {
  return `status-${String(status || "").toLowerCase()}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderSummary() {
  const rerouted = shipments.filter((route) => route.status === "REROUTED").length;
  const atRisk = shipments.filter((route) => route.risk_score >= 50 || route.status === "WATCHLIST").length;
  const coldChain = shipments.filter((route) => Number(route.telemetry_temperature_c) <= 8).length;

  summaryGrid.innerHTML = `
    <article class="summary-card">
      <span>Total shipments</span>
      <strong>${shipments.length}</strong>
    </article>
    <article class="summary-card">
      <span>At risk</span>
      <strong>${atRisk}</strong>
    </article>
    <article class="summary-card">
      <span>Rerouted</span>
      <strong>${rerouted}</strong>
    </article>
    <article class="summary-card">
      <span>Cold chain loads</span>
      <strong>${coldChain}</strong>
    </article>
  `;
}

function renderOptions() {
  const source = document.getElementById("source");
  const destination = document.getElementById("destination");
  const status = document.getElementById("status");
  const hubMarkup = options.hubs.map((hub) => `<option value="${escapeHtml(hub)}">${escapeHtml(hub)}</option>`).join("");
  source.innerHTML = hubMarkup;
  destination.innerHTML = hubMarkup;
  status.innerHTML = options.statuses
    .map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`)
    .join("");
}

function activeSearchTerm() {
  return searchInput.value.trim().toLowerCase();
}

function filteredShipments() {
  const term = activeSearchTerm();
  return shipments.filter((route) => {
    const matchesFilter =
      activeFilter === "all" ||
      (activeFilter === "at-risk" && (route.risk_score >= 50 || route.status === "WATCHLIST")) ||
      (activeFilter === "rerouted" && route.status === "REROUTED") ||
      (activeFilter === "stable" && route.status === "STABLE");

    if (!matchesFilter) {
      return false;
    }

    if (!term) {
      return true;
    }

    const haystack = [
      route.route_id,
      route.shipment_id,
      route.vehicle_label,
      route.source,
      route.destination,
      route.cargo_type,
      route.status,
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(term);
  });
}

function renderShipments() {
  const visible = filteredShipments();
  resultCount.textContent = `${visible.length} shipment${visible.length === 1 ? "" : "s"}`;

  if (!visible.length) {
    shipmentsList.innerHTML = `<div class="empty-state">No shipments match the current filters.</div>`;
    return;
  }

  shipmentsList.innerHTML = visible
    .map(
      (route) => `
        <article class="record-card">
          <div class="record-top">
            <div>
              <p class="eyebrow">${escapeHtml(route.route_id)} / ${escapeHtml(route.shipment_id)}</p>
              <h3>${escapeHtml(route.source)} to ${escapeHtml(route.destination)}</h3>
            </div>
            <span class="record-status ${statusTone(route.status)} ${severityClass(route)}">${escapeHtml(route.status)}</span>
          </div>
          <p class="record-meta">${escapeHtml(route.cargo_type)} on ${escapeHtml(route.vehicle_label)} | Risk ${route.risk_score} | ${route.distance_km} km corridor</p>
          <div class="record-metrics">
            <div>
              <strong>${route.eta_minutes} min</strong>
              <span>ETA</span>
            </div>
            <div>
              <strong>${route.load_tons}</strong>
              <span>Load tons</span>
            </div>
            <div>
              <strong>$${Number(route.cargo_value_usd || 0).toLocaleString()}</strong>
              <span>Cargo value</span>
            </div>
            <div>
              <strong>${route.telemetry_temperature_c ?? "--"} C</strong>
              <span>Temperature</span>
            </div>
          </div>
          ${route.last_action ? `<p class="record-copy">${escapeHtml(route.last_action)}</p>` : ""}
          <div class="record-actions">
            <button class="action-btn" type="button" data-action="edit" data-route-id="${route.route_id}">Edit</button>
            <button class="action-btn" type="button" data-action="reroute" data-route-id="${route.route_id}">Trigger reroute</button>
          </div>
        </article>
      `
    )
    .join("");
}

function renderAll() {
  renderSummary();
  renderShipments();
}

function resetForm() {
  shipmentForm.reset();
  routeIdInput.value = "";
  formTitle.textContent = "Create Shipment";
  if (options.statuses[0]) {
    document.getElementById("status").value = "MONITORING";
  }
}

function fillForm(routeId) {
  const route = shipments.find((item) => item.route_id === routeId);
  if (!route) {
    return;
  }

  routeIdInput.value = route.route_id;
  formTitle.textContent = `Edit ${route.route_id}`;
  document.getElementById("vehicle-label").value = route.vehicle_label || "";
  document.getElementById("cargo-type").value = route.cargo_type || "";
  document.getElementById("source").value = route.source || "";
  document.getElementById("destination").value = route.destination || "";
  document.getElementById("status").value = route.status || "MONITORING";
  document.getElementById("eta-minutes").value = route.eta_minutes || "";
  document.getElementById("load-tons").value = route.load_tons || "";
  document.getElementById("cargo-value").value = route.cargo_value_usd || "";
  document.getElementById("temperature").value = route.telemetry_temperature_c || "";
  document.getElementById("base-risk").value = route.base_risk_score || route.risk_score || "";
  shipmentForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadShipments(message = "") {
  const response = await fetch("/api/shipments");
  if (response.status === 401) {
    window.location.href = "/login";
    return;
  }
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not load shipments");
  }
  shipments = data.shipments || [];
  options = data.options || options;
  renderOptions();
  renderAll();
  if (message) {
    showBanner(message, "success");
  }
}

function formPayload() {
  return {
    vehicle_label: document.getElementById("vehicle-label").value,
    cargo_type: document.getElementById("cargo-type").value,
    source: document.getElementById("source").value,
    destination: document.getElementById("destination").value,
    status: document.getElementById("status").value,
    eta_minutes: document.getElementById("eta-minutes").value,
    load_tons: document.getElementById("load-tons").value,
    cargo_value_usd: document.getElementById("cargo-value").value,
    telemetry_temperature_c: document.getElementById("temperature").value,
    base_risk_score: document.getElementById("base-risk").value,
  };
}

async function saveShipment(event) {
  event.preventDefault();
  hideBanner();

  const routeId = routeIdInput.value.trim();
  const response = await fetch(routeId ? `/api/shipments/${routeId}` : "/api/shipments", {
    method: routeId ? "PATCH" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formPayload()),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not save shipment");
  }

  shipments = data.shipments || shipments;
  renderAll();
  resetForm();
  showBanner(routeId ? "Shipment updated successfully." : "Shipment added successfully.", "success");
}

async function rerouteShipment(routeId) {
  const response = await fetch(`/api/shipments/${routeId}/reroute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: "shipment database operator action" }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not reroute shipment");
  }
  shipments = data.shipments || shipments;
  renderAll();
  showBanner(`Triggered reroute for ${routeId}.`, "success");
}

shipmentsList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) {
    return;
  }

  hideBanner();
  const routeId = button.dataset.routeId;
  if (button.dataset.action === "edit") {
    fillForm(routeId);
    return;
  }

  if (button.dataset.action === "reroute") {
    try {
      await rerouteShipment(routeId);
    } catch (error) {
      showBanner(error.message, "error");
    }
  }
});

document.querySelectorAll("[data-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach((item) => item.classList.toggle("active", item === button));
    renderShipments();
  });
});

searchInput.addEventListener("input", () => {
  renderShipments();
});

refreshButton.addEventListener("click", async () => {
  hideBanner();
  try {
    await loadShipments("Shipment database refreshed.");
  } catch (error) {
    showBanner(error.message, "error");
  }
});

seedButton.addEventListener("click", async () => {
  hideBanner();
  try {
    const response = await fetch("/api/shipments/seed", { method: "POST" });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Could not restore seed data");
    }
    shipments = data.shipments || [];
    renderAll();
    resetForm();
    showBanner(data.message || "Restored shipment seed data.", "success");
  } catch (error) {
    showBanner(error.message, "error");
  }
});

shipmentForm.addEventListener("submit", async (event) => {
  try {
    await saveShipment(event);
  } catch (error) {
    showBanner(error.message, "error");
  }
});

resetFormButton.addEventListener("click", () => {
  hideBanner();
  resetForm();
});

cancelEditButton.addEventListener("click", () => {
  hideBanner();
  resetForm();
});

logoutButton.addEventListener("click", async () => {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

dashboardButton.addEventListener("click", () => {
  window.location.href = "/";
});

themeToggleButton.addEventListener("click", () => {
  applyTheme(currentTheme() === "dark" ? "light" : "dark");
});

updateThemeToggleLabel();
loadShipments().then(resetForm).catch((error) => {
  showBanner(error.message, "error");
});
