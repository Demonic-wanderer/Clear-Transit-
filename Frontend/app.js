const statsGrid = document.getElementById("stats-grid");
const routesList = document.getElementById("routes-list");
const alertsList = document.getElementById("alerts-list");
const weatherCard = document.getElementById("weather-card");
const trafficCard = document.getElementById("traffic-card");
const networkPill = document.getElementById("network-pill");
const objectiveText = document.getElementById("objective");
const routeChooser = document.getElementById("route-chooser");
const focusPanel = document.getElementById("focus-panel");
const activeBrief = document.getElementById("active-brief");
const refreshButton = document.getElementById("refresh-btn");
const autoButton = document.getElementById("auto-btn");
const systemBanner = document.getElementById("system-banner");
const userName = document.getElementById("user-name");
const logoutButton = document.getElementById("logout-btn");
const navPill = document.getElementById("nav-pill");
const themeToggleButton = document.getElementById("theme-toggle-btn");
const shipmentsDbButton = document.getElementById("shipments-db-btn");

const MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/bright";
const THEME_STORAGE_KEY = "clear-transit-theme";

const map = new maplibregl.Map({
  container: "map",
  style: MAP_STYLE_URL,
  center: [75.8577, 22.7196],
  zoom: 7.4,
  pitch: 42,
  bearing: -10,
  attributionControl: false,
});

map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");

let mapReady = false;
let mapMarkers = [];
let currentSnapshot = null;
let selectedRouteId = null;

function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function updateThemeToggleLabel() {
  if (!themeToggleButton) {
    return;
  }

  const theme = currentTheme();
  themeToggleButton.textContent = theme === "dark" ? "Dark mode" : "Light mode";
  themeToggleButton.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  updateThemeToggleLabel();
}

function emptyCollection() {
  return { type: "FeatureCollection", features: [] };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatTimestamp(value) {
  const timestamp = new Date(value);
  return Number.isNaN(timestamp.getTime()) ? "Just now" : timestamp.toLocaleString();
}

function normalizeAlert(alert) {
  return {
    event_type: alert?.event_type || "system",
    severity: formatSeverity(alert?.severity),
    summary: alert?.summary || "New network event detected.",
    timestamp: alert?.timestamp || new Date().toISOString(),
    location: alert?.location || "Control center",
  };
}

function severityClass(severity) {
  return `severity-${(severity || "LOW").toLowerCase()}`;
}

function formatSeverity(severity) {
  return (severity || "LOW").toUpperCase();
}

function routeLevel(route) {
  return route.risk_score >= 70 ? "HIGH" : route.risk_score >= 45 ? "MEDIUM" : "LOW";
}

function routeColor(route) {
  return route.status === "REROUTED" ? "#f29c8f" : route.risk_score >= 55 ? "#e3c887" : "#8cc7b0";
}

function delayRiskLevel(route) {
  const prediction = getPrediction(route);
  const delay = prediction.predicted_delay_minutes || 0;
  if (route.risk_score >= 75 || delay >= 25) {
    return "HIGH";
  }
  if (route.risk_score >= 55 || delay >= 12) {
    return "MEDIUM";
  }
  return "LOW";
}

function getPrediction(route) {
  return route.ai_prediction || {
    predicted_delay_minutes: 0,
    on_time_probability: 92,
    confidence_score: 84,
    severity: routeLevel(route),
    recommended_action: "Keep route active and continue monitoring.",
    recommended_reroute: "Primary path",
    factors: [],
    improvement: {
      before_eta_minutes: route.eta_minutes || 0,
      after_eta_minutes: route.eta_minutes || 0,
      improvement_minutes: 0,
      comparison_label: "Current path",
      recommended_path_label: "Primary path",
    },
    summary: "AI prediction is not available yet for this route.",
  };
}

function getActiveRoute(routes) {
  if (!routes.length) {
    return null;
  }
  return routes.find((route) => route.route_id === selectedRouteId) || routes[0];
}

function showSystemBanner(message, tone = "info") {
  systemBanner.textContent = message;
  systemBanner.className = `system-banner ${tone}`;
}

function hideSystemBanner() {
  systemBanner.textContent = "";
  systemBanner.className = "system-banner hidden";
}

function redirectToLogin() {
  window.location.href = "/login";
}

function setBusyState(isBusy) {
  refreshButton.disabled = isBusy;
  autoButton.disabled = isBusy;
  refreshButton.textContent = isBusy ? "Refreshing..." : "Refresh Network";
  autoButton.textContent = isBusy ? "Working..." : "Auto-Respond to High Risk";
}

function renderStats(kpis) {
  if (!statsGrid) {
    return;
  }

  const items = [
    ["Active shipments", kpis.total_shipments || 0],
    ["At risk", kpis.at_risk_shipments || 0],
    ["Rerouted", kpis.rerouted_shipments || 0],
    ["CO2 saved", `${kpis.co2_saved_kg || 0} kg`],
    ["High alerts", kpis.sms_dispatched || 0],
    ["Network risk", `${kpis.network_risk_score || 0}/100`],
  ];

  statsGrid.innerHTML = items
    .map(
      ([label, value]) => `
        <div class="stat-card">
          <span>${label}</span>
          <strong>${value}</strong>
        </div>
      `
    )
    .join("");
}

function renderSignals(liveSignals) {
  if (!weatherCard || !trafficCard || !networkPill) {
    return;
  }

  const weather = liveSignals?.weather || {
    severity: "LOW",
    summary: "Weather signal unavailable",
    timestamp: new Date().toISOString(),
  };
  const traffic = liveSignals?.traffic || {
    severity: "LOW",
    summary: "Traffic signal unavailable",
    timestamp: new Date().toISOString(),
  };
  const networkSeverity =
    weather.severity === "HIGH" || traffic.severity === "HIGH"
      ? "HIGH"
      : weather.severity === "MEDIUM" || traffic.severity === "MEDIUM"
        ? "MEDIUM"
        : "LOW";

  weatherCard.innerHTML = `
    <div class="signal-top">
      <span class="signal-label">Weather</span>
      <span class="severity-badge ${severityClass(weather.severity)}">${formatSeverity(weather.severity)}</span>
    </div>
    <h3>${escapeHtml(weather.summary)}</h3>
    <p>${formatTimestamp(weather.timestamp)}</p>
  `;

  trafficCard.innerHTML = `
    <div class="signal-top">
      <span class="signal-label">Traffic</span>
      <span class="severity-badge ${severityClass(traffic.severity)}">${formatSeverity(traffic.severity)}</span>
    </div>
    <h3>${escapeHtml(traffic.summary)}</h3>
    <p>${formatTimestamp(traffic.timestamp)}</p>
  `;

  networkPill.className = `signal-pill ${severityClass(networkSeverity)}`;
  networkPill.textContent =
    networkSeverity === "HIGH" ? "High Risk" : networkSeverity === "MEDIUM" ? "Watchlist" : "Stable";
}

function renderErrorState(message) {
  if (!weatherCard || !trafficCard || !focusPanel || !routeChooser || !routesList || !alertsList || !navPill) {
    return;
  }

  showSystemBanner(message, "error");
  weatherCard.innerHTML = `
    <div class="signal-top">
      <span class="signal-label">Weather</span>
      <span class="severity-badge severity-medium">WAITING</span>
    </div>
    <h3>Live signal feed unavailable</h3>
    <p>${message}</p>
  `;
  trafficCard.innerHTML = `
    <div class="signal-top">
      <span class="signal-label">Traffic</span>
      <span class="severity-badge severity-medium">WAITING</span>
    </div>
    <h3>Backend snapshot not ready</h3>
    <p>Reconnect the API to restore live conditions and route intelligence.</p>
  `;
  focusPanel.innerHTML = `
    <div class="focus-empty">
      <span class="focus-label">Live shipment</span>
      <h3>Waiting for the command layer</h3>
      <p>${message}</p>
    </div>
  `;
  routeChooser.innerHTML = "";
  routesList.innerHTML = `<div class="route-card route-empty"><h3>No shipment snapshot yet</h3><p>The UI loaded, but the backend snapshot failed. This is why the dashboard looked disconnected.</p></div>`;
  alertsList.innerHTML = `<div class="alert-card route-empty"><h3>No alert memory yet</h3><p>Once the API recovers, alert history will render here.</p></div>`;
  navPill.className = "nav-pill hidden";
  navPill.textContent = "";
}

function buildFeatureCollection(routes) {
  const activeRoute = getActiveRoute(routes);
  const activeFeatures = [];
  const completedFeatures = [];
  const secondaryFeatures = [];
  const pushFeature = (target, geometry, properties) => {
    if (!geometry || geometry.type !== "LineString") {
      return;
    }
    target.push({
      type: "Feature",
      geometry,
      properties,
    });
  };

  if (activeRoute) {
    pushFeature(activeFeatures, activeRoute.remaining_geometry || activeRoute.map_geometry, {
      routeId: activeRoute.route_id,
      lineColor: "#9db9df",
    });
    pushFeature(completedFeatures, activeRoute.completed_geometry, {
      routeId: activeRoute.route_id,
    });

    const alternatePath = (activeRoute.route_options || []).find((option, index) => {
      if (index === 0) {
        return false;
      }
      return option.label === "Previous path" || option.label === "Option 2";
    });

    if (alternatePath) {
      pushFeature(secondaryFeatures, alternatePath.geometry, {
        routeId: activeRoute.route_id,
        summary: alternatePath.summary,
        label: alternatePath.label,
        lineColor: "#b4bccb",
      });
    }
  }

  return {
    active: { type: "FeatureCollection", features: activeFeatures },
    completed: { type: "FeatureCollection", features: completedFeatures },
    secondary: { type: "FeatureCollection", features: secondaryFeatures },
  };
}

function clearMarkers() {
  mapMarkers.forEach((marker) => marker.remove());
  mapMarkers = [];
}

function makeMarkerElement(className, label) {
  const element = document.createElement("div");
  element.className = className;
  element.innerHTML = `<span>${escapeHtml(label)}</span>`;
  return element;
}

function syncMap(routes) {
  if (!mapReady) {
    return;
  }

  const activeRoute = getActiveRoute(routes);
  const collections = buildFeatureCollection(routes);
  map.getSource("routes-active").setData(collections.active);
  map.getSource("routes-completed").setData(collections.completed);
  map.getSource("routes-secondary").setData(collections.secondary);
  clearMarkers();

  if (!activeRoute) {
    return;
  }

  const currentPosition = activeRoute.current_position || activeRoute.current_location;
  if (currentPosition?.lon && currentPosition?.lat) {
    const vehicleMarker = new maplibregl.Marker({
      element: makeMarkerElement(`vehicle-marker ${severityClass(routeLevel(activeRoute))}`, activeRoute.vehicle_label || "CT"),
      anchor: "center",
    })
      .setLngLat([currentPosition.lon, currentPosition.lat])
      .addTo(map);
    mapMarkers.push(vehicleMarker);
  }

  if (activeRoute.destination_location?.lon && activeRoute.destination_location?.lat) {
    const destinationMarker = new maplibregl.Marker({
      element: makeMarkerElement("stop-marker destination-marker", "Dest"),
      anchor: "bottom",
    })
      .setLngLat([activeRoute.destination_location.lon, activeRoute.destination_location.lat])
      .addTo(map);
    mapMarkers.push(destinationMarker);
  }

  if (activeRoute.current_location?.lon && activeRoute.current_location?.lat) {
    const sourceMarker = new maplibregl.Marker({
      element: makeMarkerElement("stop-marker source-marker", "Hub"),
      anchor: "bottom",
    })
      .setLngLat([activeRoute.current_location.lon, activeRoute.current_location.lat])
      .addTo(map);
    mapMarkers.push(sourceMarker);
  }

  const bounds = new maplibregl.LngLatBounds();
  const coordinates = activeRoute.remaining_geometry?.coordinates || activeRoute.route_options?.[0]?.geometry?.coordinates || [];
  coordinates.forEach((coordinate) => bounds.extend(coordinate));
  if (!bounds.isEmpty()) {
    if (currentPosition?.lon && currentPosition?.lat) {
      map.easeTo({
        center: [currentPosition.lon, currentPosition.lat],
        zoom: Math.min(13.8, Math.max(11.8, map.getZoom())),
        pitch: 58,
        bearing: activeRoute.current_bearing || 0,
        duration: 900,
      });
    } else {
      map.fitBounds(bounds, {
        padding: { top: 120, right: 70, bottom: 90, left: 70 },
        maxZoom: 11.8,
        duration: 900,
      });
    }
  }
}

function renderFocusPanel(routes) {
  if (!focusPanel) {
    return;
  }

  const activeRoute = getActiveRoute(routes);
  if (!activeRoute) {
    focusPanel.innerHTML = `
      <div class="focus-empty">
        <span class="focus-label">Live shipment</span>
        <h3>No active route</h3>
        <p>Refresh the network to load shipment focus details.</p>
      </div>
    `;
    return;
  }

  const prediction = getPrediction(activeRoute);
  const nextStep = activeRoute.next_navigation_step;
  const delayRisk = delayRiskLevel(activeRoute);
  const improvement = prediction.improvement || {};
  const topFactors = (prediction.factors || []).slice(0, 3);
  focusPanel.innerHTML = `
    <div class="focus-top">
      <div>
        <span class="focus-label">Live shipment</span>
        <h3>${activeRoute.source} -> ${activeRoute.destination}</h3>
      </div>
      <span class="focus-live ${severityClass(delayRisk)}">Active shipment</span>
    </div>
    <div class="focus-meta">
      <span>${activeRoute.vehicle_label || activeRoute.route_id}</span>
      <span>${activeRoute.cargo_type || "General cargo"}</span>
      <span>${activeRoute.distance_remaining_km || 0} km left</span>
    </div>
    <div class="focus-metrics focus-metrics-primary">
      <div>
        <strong>${activeRoute.projected_eta_minutes || activeRoute.eta_minutes} min</strong>
        <span>ETA</span>
      </div>
      <div>
        <strong>${formatSeverity(delayRisk)}</strong>
        <span>Delay risk</span>
      </div>
      <div>
        <strong>${nextStep ? escapeHtml(nextStep.instruction) : "Cruising"}</strong>
        <span>Next step</span>
      </div>
    </div>
    <div class="focus-progress">
      <span style="width:${activeRoute.progress_percent || 0}%;"></span>
    </div>
    <div class="focus-summary compact-summary">
      <p>${escapeHtml(prediction.recommended_action)}</p>
    </div>
    <div class="focus-metrics focus-metrics-secondary">
      <div>
        <strong>${prediction.confidence_score || prediction.on_time_probability}%</strong>
        <span>Confidence</span>
      </div>
      <div>
        <strong>${formatSeverity(prediction.severity || delayRisk)}</strong>
        <span>Severity</span>
      </div>
      <div>
        <strong>${escapeHtml(prediction.recommended_reroute || "Primary path")}</strong>
        <span>Reroute</span>
      </div>
    </div>
    <div class="next-step-card compact-card">
      <span class="focus-label">Before / after</span>
      <strong>${improvement.before_eta_minutes || activeRoute.projected_eta_minutes} min -> ${improvement.after_eta_minutes || activeRoute.projected_eta_minutes} min</strong>
      <small>Improvement: ${improvement.improvement_minutes || 0} min via ${escapeHtml(improvement.recommended_path_label || "current path")}</small>
    </div>
    ${
      nextStep
        ? `
          <div class="next-step-card compact-card">
            <span class="focus-label">Next maneuver</span>
            <strong>${nextStep.instruction}</strong>
            <small>In ${nextStep.distance_km} km | ${nextStep.duration_minutes} min on ${nextStep.road_name}</small>
          </div>
        `
        : ""
    }
    <div class="factor-list compact-factor-list">
      ${topFactors
        .map(
          (factor) => `
            <div class="factor-pill">
              <strong>${escapeHtml(factor.label)} | +${factor.impact_minutes} min</strong>
              <span>${escapeHtml(factor.detail || factor.category || "")}</span>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function renderFocusPanelCompact(routes) {
  if (!focusPanel) {
    return;
  }

  const activeRoute = getActiveRoute(routes);
  if (!activeRoute) {
    focusPanel.innerHTML = `
      <div class="focus-empty">
        <span class="focus-label">Live shipment</span>
        <h3>No active route</h3>
        <p>Refresh to load shipment focus.</p>
      </div>
    `;
    return;
  }

  const prediction = getPrediction(activeRoute);
  const nextStep = activeRoute.next_navigation_step;
  const delayRisk = delayRiskLevel(activeRoute);
  focusPanel.innerHTML = `
    <div class="focus-top">
      <div>
        <span class="focus-label">Live shipment</span>
        <h3>${escapeHtml(activeRoute.route_id)} | ${escapeHtml(activeRoute.destination)}</h3>
      </div>
      <span class="focus-live ${severityClass(delayRisk)}">Live</span>
    </div>
    <div class="focus-meta">
      <span>${escapeHtml(activeRoute.vehicle_label || activeRoute.route_id)}</span>
      <span>${activeRoute.distance_remaining_km || 0} km left</span>
    </div>
    <div class="focus-metrics focus-metrics-primary">
      <div>
        <strong>${activeRoute.projected_eta_minutes || activeRoute.eta_minutes} min</strong>
        <span>ETA</span>
      </div>
      <div>
        <strong>${formatSeverity(delayRisk)}</strong>
        <span>Risk</span>
      </div>
      <div>
        <strong>${nextStep ? escapeHtml(nextStep.instruction) : "Cruising"}</strong>
        <span>Next step</span>
      </div>
      <div>
        <strong>+${prediction.predicted_delay_minutes || 0} min</strong>
        <span>Delay</span>
      </div>
    </div>
  `;
}

function renderActiveBrief(routes) {
  if (!activeBrief) {
    return;
  }

  const activeRoute = getActiveRoute(routes);
  if (!activeRoute) {
    activeBrief.innerHTML = "";
    return;
  }

  const prediction = getPrediction(activeRoute);
  const improvement = prediction.improvement || {};
  const nextStep = activeRoute.next_navigation_step;
  const factors = (prediction.factors || []).slice(0, 5);
  const severity = prediction.severity || delayRiskLevel(activeRoute);

  activeBrief.innerHTML = `
    <div class="active-brief-head">
      <div>
        <p class="panel-kicker">Shipment Debrief</p>
        <h2>${escapeHtml(activeRoute.route_id)} | ${escapeHtml(activeRoute.source)} to ${escapeHtml(activeRoute.destination)}</h2>
      </div>
      <span class="severity-badge ${severityClass(severity)}">${formatSeverity(severity)}</span>
    </div>
    <div class="active-brief-grid">
      <div class="brief-stat">
        <strong>${activeRoute.projected_eta_minutes || activeRoute.eta_minutes} min</strong>
        <span>Projected ETA</span>
      </div>
      <div class="brief-stat">
        <strong>+${prediction.predicted_delay_minutes || 0} min</strong>
        <span>Predicted delay</span>
      </div>
      <div class="brief-stat">
        <strong>${prediction.confidence_score || prediction.on_time_probability}%</strong>
        <span>Confidence</span>
      </div>
      <div class="brief-stat">
        <strong>${escapeHtml(prediction.recommended_reroute || "Primary path")}</strong>
        <span>Recommended reroute</span>
      </div>
    </div>
    <div class="active-brief-columns">
      <div class="brief-card">
        <span class="focus-label">Detected Risk Factors</span>
        <div class="brief-factor-list">
          ${factors
            .map(
              (factor) => `
                <div class="brief-factor">
                  <strong>${escapeHtml(factor.label)}</strong>
                  <span>${escapeHtml(factor.detail || factor.category || "")}</span>
                  <small>+${factor.impact_minutes} min</small>
                </div>
              `
            )
            .join("")}
        </div>
      </div>
      <div class="brief-card">
        <span class="focus-label">Decision</span>
        <p class="brief-copy">${escapeHtml(prediction.recommended_action)}</p>
        <div class="brief-before-after">
          <strong>${improvement.before_eta_minutes || activeRoute.projected_eta_minutes} min -> ${improvement.after_eta_minutes || activeRoute.projected_eta_minutes} min</strong>
          <span>Improvement: ${improvement.improvement_minutes || 0} min</span>
        </div>
        <div class="brief-next-step">
          <strong>${nextStep ? escapeHtml(nextStep.instruction) : "Cruising"}</strong>
          <span>${nextStep ? `${nextStep.distance_km} km ahead` : "No immediate maneuver"}</span>
        </div>
      </div>
    </div>
  `;
}

function renderNavigationPill(routes) {
  if (!navPill) {
    return;
  }

  const activeRoute = getActiveRoute(routes);
  if (!activeRoute || !activeRoute.next_navigation_step) {
    navPill.className = "nav-pill hidden";
    navPill.textContent = "";
    return;
  }

  navPill.className = "nav-pill";
  navPill.innerHTML = `
    <strong>${activeRoute.next_navigation_step.instruction}</strong>
    <span>${activeRoute.next_navigation_step.distance_km} km ahead</span>
  `;
}

function renderRouteChooser(routes) {
  if (!routeChooser) {
    return;
  }

  const activeRoute = getActiveRoute(routes);
  routeChooser.innerHTML = routes
    .map((route) => {
      const active = route.route_id === activeRoute?.route_id;
      const delayRisk = delayRiskLevel(route);
      return `
        <button class="route-chip ${active ? "active" : ""}" data-focus-route="${route.route_id}">
          <span>${route.shipment_id || route.route_id} ${active ? "- Selected" : ""}</span>
          <strong>${route.destination}</strong>
          <small>${route.route_id} | ${route.projected_eta_minutes || route.eta_minutes} min ETA | ${formatSeverity(delayRisk)} risk</small>
        </button>
      `;
    })
    .join("");

  document.querySelectorAll("[data-focus-route]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedRouteId = button.dataset.focusRoute;
      renderSnapshot(currentSnapshot);
    });
  });
}

function renderRouteChooserFocused(routes) {
  if (!routeChooser) {
    return;
  }

  const activeRoute = getActiveRoute(routes);
  if (!activeRoute) {
    routeChooser.innerHTML = "";
    return;
  }

  const prediction = getPrediction(activeRoute);
  const delayRisk = delayRiskLevel(activeRoute);
  routeChooser.innerHTML = `
    <button class="route-chip active live-route-chip" data-focus-route="${activeRoute.route_id}">
      <span>${activeRoute.route_id} [LIVE]</span>
      <strong>${escapeHtml(activeRoute.destination)}</strong>
      <small>${activeRoute.projected_eta_minutes || activeRoute.eta_minutes} min ETA | ${formatSeverity(delayRisk)} risk | +${prediction.predicted_delay_minutes} min</small>
    </button>
  `;

  document.querySelectorAll("[data-focus-route]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedRouteId = button.dataset.focusRoute;
      renderSnapshot(currentSnapshot);
    });
  });
}

function renderRoutes(routes) {
  if (!routesList) {
    return;
  }

  routesList.innerHTML = routes
    .map((route) => {
      const prediction = getPrediction(route);
      return `
        <div class="route-card">
          <div class="route-top">
            <div>
              <p class="route-id">${route.route_id} / ${route.shipment_id}</p>
              <h3>${route.source} -> ${route.destination}</h3>
            </div>
            <span class="severity-badge ${severityClass(routeLevel(route))}">${route.status}</span>
          </div>
          <div class="route-meta">
            <span>${route.distance_km} km</span>
            <span>${route.projected_eta_minutes || route.eta_minutes} min ETA</span>
            <span>${route.cargo_type || "General"} | $${(route.cargo_value_usd || 0).toLocaleString()}</span>
            <span>${route.telemetry_temperature_c ?? "--"} C | Risk ${route.risk_score}</span>
          </div>
          <div class="route-ai-row">
            <div class="route-ai-stat">
              <strong>${route.progress_percent || 0}%</strong>
              <span>Progress</span>
            </div>
            <div class="route-ai-stat">
              <strong>+${prediction.predicted_delay_minutes} min</strong>
              <span>AI delay</span>
            </div>
            <div class="route-ai-stat">
              <strong>${prediction.on_time_probability}%</strong>
              <span>On-time</span>
            </div>
          </div>
          <div class="option-list">
            ${(route.route_options || [])
              .map(
                (option) => `
                  <div class="option-pill ${option.is_fastest ? "is-fastest" : ""}">
                    <strong>${option.label}</strong>
                    <span>${option.summary}</span>
                  </div>
                `
              )
              .join("")}
          </div>
          <p class="route-intel">${prediction.recommended_action}</p>
          <button class="route-btn" data-route-id="${route.route_id}">Trigger reroute</button>
          ${route.last_action ? `<p class="route-note">${route.last_action}</p>` : ""}
        </div>
      `;
    })
    .join("");

  document.querySelectorAll("[data-route-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      setBusyState(true);
      try {
        const response = await fetch(`/api/routes/${button.dataset.routeId}/reroute`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: "operator intervention" }),
        });
        if (!response.ok) {
          throw new Error(`Reroute failed with status ${response.status}`);
        }
        const snapshot = await response.json();
        renderSnapshot(snapshot);
        showSystemBanner("Route successfully rerouted.", "success");
      } catch (error) {
        showSystemBanner(error.message, "error");
      } finally {
        setBusyState(false);
      }
    });
  });
}

function renderRoutesFocused(routes) {
  if (!routesList) {
    return;
  }

  const activeRoute = getActiveRoute(routes);
  routesList.innerHTML = routes
    .map((route) => {
      const prediction = getPrediction(route);
      const isActive = route.route_id === activeRoute?.route_id;
      const delayRisk = delayRiskLevel(route);
      const nextStep = route.next_navigation_step?.instruction || "Cruising";
      const improvement = prediction.improvement || {};

      return `
        <div class="route-card ${isActive ? "active-route-card" : "compact-route-card"}">
          <div class="route-top">
            <div>
              <p class="route-id">${route.route_id} / ${route.shipment_id}</p>
              <h3>${escapeHtml(route.source)} -> ${escapeHtml(route.destination)}</h3>
            </div>
            <span class="severity-badge ${severityClass(isActive ? delayRisk : routeLevel(route))}">${isActive ? "ACTIVE" : escapeHtml(route.status)}</span>
          </div>
          <div class="route-meta">
            <span>${route.distance_km} km</span>
            <span>${route.projected_eta_minutes || route.eta_minutes} min ETA</span>
            <span>${formatSeverity(delayRisk)} delay risk</span>
            <span>${route.telemetry_temperature_c ?? "--"} C</span>
          </div>
          <div class="route-ai-row">
            <div class="route-ai-stat">
              <strong>${route.projected_eta_minutes || route.eta_minutes} min</strong>
              <span>ETA</span>
            </div>
            <div class="route-ai-stat">
              <strong>+${prediction.predicted_delay_minutes} min</strong>
              <span>Delay window</span>
            </div>
            <div class="route-ai-stat">
              <strong>${prediction.confidence_score || prediction.on_time_probability}%</strong>
              <span>Confidence</span>
            </div>
          </div>
          ${
            isActive
              ? `
                <div class="option-list">
                  ${(route.route_options || [])
                    .slice(0, 2)
                    .map(
                      (option) => `
                        <div class="option-pill ${option.is_fastest ? "is-fastest" : ""}">
                          <strong>${escapeHtml(option.label)}</strong>
                          <span>${escapeHtml(option.summary)}</span>
                        </div>
                      `
                    )
                    .join("")}
                </div>
                <div class="route-ai-row">
                  <div class="route-ai-stat">
                    <strong>${escapeHtml(prediction.recommended_reroute || "Primary path")}</strong>
                    <span>Recommended reroute</span>
                  </div>
                  <div class="route-ai-stat">
                    <strong>${formatSeverity(prediction.severity || delayRisk)}</strong>
                    <span>Severity</span>
                  </div>
                  <div class="route-ai-stat">
                    <strong>${improvement.before_eta_minutes || route.projected_eta_minutes} -> ${improvement.after_eta_minutes || route.projected_eta_minutes} min</strong>
                    <span>Before / after</span>
                  </div>
                </div>
                <div class="next-step-card">
                  <span class="focus-label">Detected risk factors</span>
                  <strong>${(prediction.factors || []).map((factor) => escapeHtml(factor.label)).join(", ") || "No active risk factors"}</strong>
                  <small>${escapeHtml(nextStep)}</small>
                </div>
                <p class="route-intel">${escapeHtml(prediction.recommended_action)}</p>
              `
              : ""
          }
          <button class="route-btn" data-route-id="${route.route_id}">Trigger reroute</button>
          ${isActive && route.last_action ? `<p class="route-note">${escapeHtml(route.last_action)}</p>` : ""}
        </div>
      `;
    })
    .join("");

  document.querySelectorAll("[data-route-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      setBusyState(true);
      try {
        const response = await fetch(`/api/routes/${button.dataset.routeId}/reroute`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: "operator intervention" }),
        });
        if (!response.ok) {
          throw new Error(`Reroute failed with status ${response.status}`);
        }
        const snapshot = await response.json();
        renderSnapshot(snapshot);
        showSystemBanner("Route successfully rerouted.", "success");
      } catch (error) {
        showSystemBanner(error.message, "error");
      } finally {
        setBusyState(false);
      }
    });
  });
}

function renderAlerts(alerts) {
  if (!alertsList) {
    return;
  }

  if (!alerts.length) {
    alertsList.innerHTML = `<p class="empty-state">Refresh the network to create alert history.</p>`;
    return;
  }

  alertsList.innerHTML = alerts
    .map(
      (alert) => `
        <div class="alert-card">
          <div class="signal-top">
            <span class="signal-label">${alert.event_type}</span>
            <span class="severity-badge ${severityClass(alert.severity)}">${formatSeverity(alert.severity)}</span>
          </div>
          <h3>${alert.summary}</h3>
          <p>${new Date(alert.timestamp).toLocaleString()} | ${alert.location}</p>
        </div>
      `
    )
    .join("");
}

function renderAlertsSafe(alerts) {
  if (!alertsList) {
    return;
  }

  const normalizedAlerts = Array.isArray(alerts) ? alerts.map(normalizeAlert) : [];
  if (!normalizedAlerts.length) {
    alertsList.innerHTML = `<p class="empty-state">Refresh the network to create alert history.</p>`;
    return;
  }

  alertsList.innerHTML = normalizedAlerts
    .map(
      (alert) => `
        <div class="alert-card">
          <div class="signal-top">
            <span class="signal-label">${escapeHtml(alert.event_type)}</span>
            <span class="severity-badge ${severityClass(alert.severity)}">${formatSeverity(alert.severity)}</span>
          </div>
          <h3>${escapeHtml(alert.summary)}</h3>
          <p>${formatTimestamp(alert.timestamp)} | ${escapeHtml(alert.location)}</p>
        </div>
      `
    )
    .join("");
}

function renderSnapshot(snapshot) {
  if (!snapshot || !Array.isArray(snapshot.routes)) {
    renderErrorState("The backend returned an invalid snapshot.");
    return;
  }

  currentSnapshot = snapshot;
  if (!selectedRouteId || !snapshot.routes.some((route) => route.route_id === selectedRouteId)) {
    selectedRouteId = snapshot.routes[0]?.route_id || null;
  }

  if (snapshot.mock_notifications?.length) {
    const smsEvents = snapshot.mock_notifications.map((notification) => ({
      event_type: "STAKEHOLDER ALERT",
      severity: "MEDIUM",
      summary: notification,
      timestamp: new Date().toISOString(),
      location: "Notification service",
    }));
    snapshot.alerts = smsEvents.concat(snapshot.alerts || []);
  }

  objectiveText.textContent = snapshot.mission?.objective || objectiveText.textContent;
  renderStats(snapshot.kpis || {});
  renderSignals(snapshot.live_signals || {});
  renderNavigationPill(snapshot.routes);
  renderFocusPanelCompact(snapshot.routes);
  renderActiveBrief(snapshot.routes);
  renderRouteChooser(snapshot.routes);
  renderRoutesFocused(snapshot.routes);
  renderAlertsSafe(snapshot.alerts || []);
  syncMap(snapshot.routes);
}

async function loadSnapshot(url, options) {
  setBusyState(true);
  showSystemBanner("Connecting live network...", "loading");

  try {
    const response = await fetch(url, options);
    if (response.status === 401) {
      redirectToLogin();
      return;
    }
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Dashboard request failed (${response.status}). ${text.slice(0, 120)}`);
    }
    const snapshot = await response.json();
    hideSystemBanner();
    renderSnapshot(snapshot);
  } catch (error) {
    console.error(error);
    renderErrorState(error.message);
  } finally {
    setBusyState(false);
  }
}

async function hydrateUser() {
  if (!userName) {
    return;
  }

  const response = await fetch("/api/auth/me");
  const data = await response.json();
  if (!data.authenticated) {
    redirectToLogin();
    return;
  }
  userName.textContent = data.user.full_name;
}

map.on("load", () => {
  mapReady = true;

  map.addSource("routes-secondary", {
    type: "geojson",
    data: emptyCollection(),
  });
  map.addSource("routes-active", {
    type: "geojson",
    data: emptyCollection(),
  });
  map.addSource("routes-completed", {
    type: "geojson",
    data: emptyCollection(),
  });

  map.addLayer({
    id: "routes-secondary-layer",
    type: "line",
    source: "routes-secondary",
    layout: {
      "line-cap": "round",
      "line-join": "round",
    },
    paint: {
      "line-color": "#b0b7c8",
      "line-width": ["interpolate", ["linear"], ["zoom"], 6, 3, 13, 7],
      "line-opacity": 0.35,
      "line-dasharray": [2, 2],
    },
  });

  map.addLayer({
    id: "routes-completed-casing",
    type: "line",
    source: "routes-completed",
    layout: {
      "line-cap": "round",
      "line-join": "round",
    },
    paint: {
      "line-color": "#ffffff",
      "line-width": ["interpolate", ["linear"], ["zoom"], 6, 7, 13, 12],
      "line-opacity": 0.55,
    },
  });

  map.addLayer({
    id: "routes-completed-layer",
    type: "line",
    source: "routes-completed",
    layout: {
      "line-cap": "round",
      "line-join": "round",
    },
    paint: {
      "line-color": "#c4c9d3",
      "line-width": ["interpolate", ["linear"], ["zoom"], 6, 4, 13, 6],
      "line-opacity": 0.95,
    },
  });

  map.addLayer({
    id: "routes-active-casing",
    type: "line",
    source: "routes-active",
    layout: {
      "line-cap": "round",
      "line-join": "round",
    },
    paint: {
      "line-color": "#ffffff",
      "line-width": ["interpolate", ["linear"], ["zoom"], 6, 9, 13, 16],
      "line-opacity": 0.98,
    },
  });

  map.addLayer({
    id: "routes-active-layer",
    type: "line",
    source: "routes-active",
    layout: {
      "line-cap": "round",
      "line-join": "round",
    },
    paint: {
      "line-color": "#9db9df",
      "line-width": ["interpolate", ["linear"], ["zoom"], 6, 5, 13, 9],
      "line-opacity": 0.98,
    },
  });

  map.addLayer({
    id: "routes-active-centerline",
    type: "line",
    source: "routes-active",
    layout: {
      "line-cap": "round",
      "line-join": "round",
    },
    paint: {
      "line-color": "#d8e2f5",
      "line-width": ["interpolate", ["linear"], ["zoom"], 6, 1.4, 13, 2.2],
      "line-opacity": 0.85,
    },
  });

  if (currentSnapshot?.routes) {
    syncMap(currentSnapshot.routes);
  }
});

if (refreshButton) {
  refreshButton.addEventListener("click", () => {
    loadSnapshot("/api/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apply_relocation: false }),
    });
  });
}

if (autoButton) {
  autoButton.addEventListener("click", () => {
    loadSnapshot("/api/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apply_relocation: true }),
    });
  });
}

if (logoutButton) {
  logoutButton.addEventListener("click", async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    redirectToLogin();
  });
}

themeToggleButton?.addEventListener("click", () => {
  applyTheme(currentTheme() === "dark" ? "light" : "dark");
});

shipmentsDbButton?.addEventListener("click", () => {
  window.location.href = "/shipments";
});

updateThemeToggleLabel();
hydrateUser();
loadSnapshot("/api/dashboard");
