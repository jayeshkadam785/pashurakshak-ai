/* =========================================================
   PASHURAKSHAK AI — MAIN FRONTEND JS
   Features:
   1. AI Risk Dashboard
   2. AI Image Screening support
   3. Voice Reporting support
   4. Livestock Disease Heatmap
   5. Offline Report Queue + Auto Sync
   6. Dashboard Analytics
   ========================================================= */

(() => {
  "use strict";

  const API = "/api";

  // ---------------------------------------------------------
  // Utility
  // ---------------------------------------------------------

  const $ = (id) => document.getElementById(id);

  function safeJSON(value, fallback = null) {
    try {
      return JSON.parse(value);
    } catch {
      return fallback;
    }
  }

  function escapeHTML(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function riskClass(level) {
    return String(level || "LOW").toLowerCase();
  }

  function showLoader(show) {
    const loader = $("loader");
    if (loader) loader.style.display = show ? "flex" : "none";
  }

  function showMessage(message, type = "info") {
    const box = $("message");

    if (!box) {
      console.log(`[${type}]`, message);
      return;
    }

    box.textContent = message;
    box.className = `message ${type}`;
    box.style.display = "block";

    setTimeout(() => {
      box.style.display = "none";
    }, 5000);
  }

  // ---------------------------------------------------------
  // API helper
  // ---------------------------------------------------------

  async function apiFetch(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      }
    });

    const contentType = response.headers.get("content-type") || "";

    const data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      throw new Error(
        data?.error ||
        data?.message ||
        `Request failed (${response.status})`
      );
    }

    return data;
  }

  // ---------------------------------------------------------
  // SYMPTOM CHIPS
  // ---------------------------------------------------------

  function initSymptomChips() {
    const chips = document.querySelectorAll(
      ".symptom-chip, [data-symptom]"
    );

    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        chip.classList.toggle("selected");
      });
    });
  }

  function getSelectedSymptoms() {
    return [...document.querySelectorAll(
      ".symptom-chip.selected, [data-symptom].selected"
    )]
      .map((el) => el.dataset.symptom || el.textContent.trim())
      .filter(Boolean);
  }

  // ---------------------------------------------------------
  // GPS
  // ---------------------------------------------------------

  function initGPS() {
    const gpsBtn = $("gpsBtn");

    if (!gpsBtn) return;

    gpsBtn.addEventListener("click", () => {
      if (!navigator.geolocation) {
        showMessage("GPS is not supported on this device.", "error");
        return;
      }

      gpsBtn.disabled = true;
      gpsBtn.textContent = "📍 Getting location...";

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;

          if ($("latitude")) $("latitude").value = lat;
          if ($("longitude")) $("longitude").value = lng;

          gpsBtn.textContent = "✓ Location Captured";
          showMessage("GPS location captured successfully.", "success");
        },
        (error) => {
          console.error(error);

          gpsBtn.disabled = false;
          gpsBtn.textContent = "📍 Get GPS Location";

          showMessage(
            "Unable to get GPS location. Please allow location permission.",
            "error"
          );
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000
        }
      );
    });
  }

  // ---------------------------------------------------------
  // IMAGE PREVIEW
  // ---------------------------------------------------------

  function initImagePreview() {
    const input = $("animalImage");
    const preview = $("imagePreview");

    if (!input) return;

    input.addEventListener("change", () => {
      const file = input.files?.[0];

      if (!file) return;

      if (!file.type.startsWith("image/")) {
        showMessage("Please select a valid image.", "error");
        input.value = "";
        return;
      }

      if (file.size > 8 * 1024 * 1024) {
        showMessage("Image must be smaller than 8 MB.", "error");
        input.value = "";
        return;
      }

      if (preview) {
        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
      }
    });
  }

  // ---------------------------------------------------------
  // AI IMAGE SCREENING
  // ---------------------------------------------------------

  function initImageScreening() {
    const button = $("screenImageBtn");
    const input = $("animalImage");
    const resultBox = $("imageResult");

    if (!button || !input) return;

    button.addEventListener("click", async () => {
      const file = input.files?.[0];

      if (!file) {
        showMessage("Please capture or select an animal image first.", "error");
        return;
      }

      const formData = new FormData();
      formData.append("image", file);

      button.disabled = true;
      button.textContent = "🤖 AI Screening...";

      if (resultBox) {
        resultBox.style.display = "block";
        resultBox.innerHTML = "Analyzing image...";
      }

      try {
        const response = await fetch(`${API}/image-screen`, {
          method: "POST",
          body: formData
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Image screening failed");
        }

        renderImageScreening(data);
      } catch (error) {
        console.error(error);

        if (resultBox) {
          resultBox.innerHTML = `
            <div class="result-error">
              ❌ ${escapeHTML(error.message)}
            </div>
          `;
        }

        showMessage(error.message, "error");
      } finally {
        button.disabled = false;
        button.textContent = "🤖 Screen Image with AI";
      }
    });
  }

  function renderImageScreening(data) {
    const box = $("imageResult");

    if (!box) return;

    const level = data.risk_level || data.riskLevel || "LOW";
    const confidence = data.confidence || 0;

    const signs = data.visible_signs || [];
    const categories = data.possible_categories || [];

    box.style.display = "block";

    box.innerHTML = `
      <div class="ai-screen-card ${riskClass(level)}">

        <div class="screen-header">
          <strong>🤖 AI Image Screening</strong>
          <span class="risk-badge ${riskClass(level)}">
            ${escapeHTML(level)}
          </span>
        </div>

        <div class="screen-confidence">
          Confidence: <strong>${confidence}%</strong>
        </div>

        ${
          signs.length
            ? `
              <div class="screen-section">
                <strong>Visible Signs</strong>
                <ul>
                  ${signs.map(s => `<li>${escapeHTML(s)}</li>`).join("")}
                </ul>
              </div>
            `
            : ""
        }

        ${
          categories.length
            ? `
              <div class="screen-section">
                <strong>Possible Categories</strong>
                <ul>
                  ${categories.map(s => `<li>${escapeHTML(s)}</li>`).join("")}
                </ul>
              </div>
            `
            : ""
        }

        <div class="screen-recommendation">
          <strong>Recommendation</strong>
          <p>${escapeHTML(data.recommendation || "Consult a veterinarian.")}</p>
        </div>

        <small>
          ⚠️ AI screening is decision support, not a final veterinary diagnosis.
        </small>

      </div>
    `;
  }

  // ---------------------------------------------------------
  // VOICE REPORTING
  // ---------------------------------------------------------

  function initVoiceReporting() {
    const button = $("startVoiceBtn");
    const transcript = $("voiceTranscript");
    const language = $("voiceLanguage");

    if (!button || !transcript) return;

    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      button.disabled = true;
      button.textContent = "🎙️ Voice Not Supported";
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = true;

    button.addEventListener("click", () => {
      recognition.lang = language?.value || "mr-IN";

      transcript.value = "";
      button.textContent = "🔴 Listening...";
      button.classList.add("recording");

      recognition.start();
    });

    recognition.onresult = (event) => {
      let text = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        text += event.results[i][0].transcript;
      }

      transcript.value = text;
    };

    recognition.onend = () => {
      button.textContent = "🎙️ Start Voice Report";
      button.classList.remove("recording");
    };

    recognition.onerror = (event) => {
      console.error(event);

      button.textContent = "🎙️ Start Voice Report";
      button.classList.remove("recording");

      showMessage(
        "Voice recognition failed. Please try again.",
        "error"
      );
    };
  }

  // ---------------------------------------------------------
  // REPORT DATA
  // ---------------------------------------------------------

  function collectReportData() {
    return {
      animal_type:
        $("animalType")?.value ||
        $("animal_type")?.value ||
        "cattle",

      affected_count:
        Number(
          $("affectedCount")?.value ||
          $("affected_count")?.value ||
          1
        ),

      days_since_onset:
        Number(
          $("daysSinceOnset")?.value ||
          $("days_since_onset")?.value ||
          1
        ),

      vaccination_status:
        $("vaccinationStatus")?.value || "unknown",

      symptoms: getSelectedSymptoms(),

      notes:
        $("notes")?.value ||
        $("voiceTranscript")?.value ||
        "",

      village:
        $("village")?.value || "Satara",

      block:
        $("block")?.value || "",

      latitude:
        Number($("latitude")?.value || 17.6805),

      longitude:
        Number($("longitude")?.value || 74.0183),

      reported_by:
        localStorage.getItem("user_id") || "demo-user"
    };
  }

  // ---------------------------------------------------------
  // OFFLINE QUEUE
  // ---------------------------------------------------------

  const QUEUE_KEY = "pashurakshak_offline_reports";

  function getOfflineQueue() {
    return safeJSON(
      localStorage.getItem(QUEUE_KEY) || "[]",
      []
    );
  }

  function saveOfflineQueue(queue) {
    localStorage.setItem(
      QUEUE_KEY,
      JSON.stringify(queue)
    );
  }

  function addToOfflineQueue(report) {
    const queue = getOfflineQueue();

    queue.push({
      ...report,
      queued_at: new Date().toISOString()
    });

    saveOfflineQueue(queue);
  }

  async function syncOfflineReports() {
    const queue = getOfflineQueue();

    if (!queue.length || !navigator.onLine) return;

    const remaining = [];

    for (const report of queue) {
      try {
        await apiFetch(`${API}/reports`, {
          method: "POST",
          body: JSON.stringify(report)
        });
      } catch (error) {
        console.error("Offline sync failed:", error);
        remaining.push(report);
      }
    }

    saveOfflineQueue(remaining);

    if (queue.length && remaining.length === 0) {
      showMessage(
        `${queue.length} offline report(s) synced successfully.`,
        "success"
      );
    }
  }

  window.addEventListener("online", syncOfflineReports);

  // ---------------------------------------------------------
  // REPORT SUBMIT
  // ---------------------------------------------------------

  function initReportSubmit() {
    const form =
      $("reportForm") ||
      document.querySelector("form[data-report-form]");

    const button = $("submitBtn");

    if (!form || !button) return;

    // Prevent duplicate listeners
    if (form.dataset.appSubmitBound === "true") return;

    form.dataset.appSubmitBound = "true";

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const report = collectReportData();

      if (!report.symptoms.length && !report.notes) {
        showMessage(
          "Please select at least one symptom or add a description.",
          "error"
        );
        return;
      }

      button.disabled = true;
      button.textContent = "Saving...";

      try {
        if (!navigator.onLine) {
          addToOfflineQueue(report);

          showMessage(
            "No internet. Report saved offline and will sync automatically.",
            "success"
          );

          form.reset();
          return;
        }

        const response = await apiFetch(`${API}/reports`, {
          method: "POST",
          body: JSON.stringify(report)
        });

        renderRiskResult(response);

        showMessage(
          "Livestock health report submitted successfully.",
          "success"
        );

      } catch (error) {
        console.error(error);

        addToOfflineQueue(report);

        showMessage(
          "Server unavailable. Report saved offline for automatic sync.",
          "info"
        );
      } finally {
        button.disabled = false;
        button.textContent = "Submit Health Report";
      }
    });
  }

  // ---------------------------------------------------------
  // RISK RESULT
  // ---------------------------------------------------------

  function renderRiskResult(data) {
    const box = $("riskResult");

    if (!box) return;

    const level =
      data.risk_level ||
      data.riskLevel ||
      "LOW";

    const score =
      Number(data.risk_score || data.riskScore || 0);

    const confidence =
      Number(data.confidence || 0);

    const factors =
      data.factors ||
      data.risk_factors ||
      [];

    box.style.display = "block";

    if ($("riskLevel")) {
      $("riskLevel").textContent = level;
      $("riskLevel").className =
        `risk-badge ${riskClass(level)}`;
    }

    if ($("riskScore")) {
      $("riskScore").textContent = `${score}/100`;
    }

    if ($("confidence")) {
      $("confidence").textContent = `${confidence}%`;
    }

    if ($("riskProgress")) {
      $("riskProgress").style.width = `${score}%`;
    }

    if ($("factors")) {
      $("factors").innerHTML = factors.length
        ? factors.map((factor) => {
            if (typeof factor === "string") {
              return `<li>${escapeHTML(factor)}</li>`;
            }

            return `
              <li>
                <strong>${escapeHTML(factor.factor || "")}</strong>
                ${factor.impact ? ` — ${escapeHTML(factor.impact)}` : ""}
              </li>
            `;
          }).join("")
        : "<li>No major risk factors detected.</li>";
    }

    if ($("recommendation")) {
      $("recommendation").textContent =
        data.recommendation ||
        "Continue monitoring the animal and contact a veterinarian if symptoms worsen.";
    }

    box.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  }

  // =========================================================
  // DASHBOARD
  // =========================================================

  let map = null;
  let mapLayers = [];
  let heatLayer = null;

  const FALLBACK_REPORTS = [
    {
      village: "Satara",
      block: "Satara",
      lat: 17.6805,
      lng: 74.0183,
      risk_level: "HIGH",
      risk_score: 86,
      animal_type: "cattle",
      affected_count: 8,
      date: "2026-09-06"
    },
    {
      village: "Wai",
      block: "Wai",
      lat: 17.9514,
      lng: 73.8900,
      risk_level: "MODERATE",
      risk_score: 54,
      animal_type: "buffalo",
      affected_count: 4,
      date: "2026-09-05"
    },
    {
      village: "Karad",
      block: "Karad",
      lat: 17.2894,
      lng: 74.1818,
      risk_level: "LOW",
      risk_score: 22,
      animal_type: "cattle",
      affected_count: 2,
      date: "2026-09-04"
    },
    {
      village: "Phaltan",
      block: "Phaltan",
      lat: 17.9911,
      lng: 74.4318,
      risk_level: "HIGH",
      risk_score: 78,
      animal_type: "goat",
      affected_count: 10,
      date: "2026-09-03"
    },
    {
      village: "Koregaon",
      block: "Koregaon",
      lat: 17.6953,
      lng: 74.0886,
      risk_level: "MODERATE",
      risk_score: 48,
      animal_type: "cattle",
      affected_count: 5,
      date: "2026-09-02"
    }
  ];

  async function loadReports() {
    try {
      const response = await apiFetch(`${API}/reports`);

      if (Array.isArray(response)) return response;

      return response.reports || [];
    } catch (error) {
      console.warn(
        "Using demo/fallback reports:",
        error.message
      );

      return FALLBACK_REPORTS;
    }
  }

  // ---------------------------------------------------------
  // LEAFLET MAP
  // ---------------------------------------------------------

  function initMap() {
    const mapElement = $("risk-map");

    if (!mapElement || typeof L === "undefined") {
      return null;
    }

    if (map) {
      return map;
    }

    map = L.map("risk-map").setView(
      [17.6805, 74.0183],
      9
    );

    L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 19
      }
    ).addTo(map);

    return map;
  }

  function clearMapLayers() {
    mapLayers.forEach(layer => {
      if (map && map.hasLayer(layer)) {
        map.removeLayer(layer);
      }
    });

    mapLayers = [];

    if (heatLayer && map?.hasLayer(heatLayer)) {
      map.removeLayer(heatLayer);
    }

    heatLayer = null;
  }

  function getRiskValue(level) {
    switch (String(level).toUpperCase()) {
      case "HIGH":
        return 1;
      case "MODERATE":
      case "WATCH":
        return 0.65;
      case "LOW":
      default:
        return 0.25;
    }
  }

  function renderHeatmap(reports) {
    if (!map) return;

    clearMapLayers();

    const points = reports
      .filter(r =>
        Number.isFinite(Number(r.lat)) &&
        Number.isFinite(Number(r.lng))
      )
      .map(r => [
        Number(r.lat),
        Number(r.lng),
        getRiskValue(r.risk_level)
      ]);

    // Leaflet.heat is optional.
    if (
      typeof L.heatLayer === "function" &&
      points.length
    ) {
      heatLayer = L.heatLayer(points, {
        radius: 35,
        blur: 25,
        maxZoom: 12,
        minOpacity: 0.35
      }).addTo(map);

      mapLayers.push(heatLayer);
    }

    // Always add individual risk markers.
    reports.forEach(report => {
      const lat = Number(report.lat);
      const lng = Number(report.lng);

      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        return;
      }

      const level =
        String(report.risk_level || "LOW").toUpperCase();

      const score =
        Number(report.risk_score || 0);

      const radius =
        level === "HIGH"
          ? 12
          : level === "MODERATE"
            ? 9
            : 7;

      const marker = L.circleMarker(
        [lat, lng],
        {
          radius,
          fillOpacity: 0.75,
          opacity: 0.9,
          weight: 2
        }
      ).addTo(map);

      marker.bindPopup(`
        <div style="min-width:190px">
          <strong>🐄 ${escapeHTML(report.village || "Unknown")}</strong>
          <hr>

          <b>Risk:</b>
          ${escapeHTML(level)}
          <br>

          <b>Risk Score:</b>
          ${score}/100
          <br>

          <b>Animal:</b>
          ${escapeHTML(report.animal_type || "Unknown")}
          <br>

          <b>Affected:</b>
          ${Number(report.affected_count || 0)}
          <br>

          <b>Date:</b>
          ${escapeHTML(report.date || "")}
        </div>
      `);

      marker.on("click", () => {
        map.setView(
          [lat, lng],
          Math.max(map.getZoom(), 11)
        );
      });

      mapLayers.push(marker);
    });
  }

  // ---------------------------------------------------------
  // MAP FILTERS
  // ---------------------------------------------------------

  function applyMapFilters(reports) {
    const riskFilter =
      $("riskFilter")?.value || "ALL";

    const animalFilter =
      $("animalFilter")?.value || "ALL";

    return reports.filter(report => {
      const risk =
        String(report.risk_level || "LOW").toUpperCase();

      const animal =
        String(report.animal_type || "").toLowerCase();

      const riskMatch =
        riskFilter === "ALL" ||
        risk === riskFilter;

      const animalMatch =
        animalFilter === "ALL" ||
        animal === animalFilter.toLowerCase();

      return riskMatch && animalMatch;
    });
  }

  function initMapFilters(reports) {
    const riskFilter = $("riskFilter");
    const animalFilter = $("animalFilter");

    function refresh() {
      const filtered = applyMapFilters(reports);

      renderHeatmap(filtered);

      updateDashboardStats(filtered);
      renderCaseTable(filtered);
    }

    riskFilter?.addEventListener("change", refresh);
    animalFilter?.addEventListener("change", refresh);
  }

  // ---------------------------------------------------------
  // DASHBOARD STATS
  // ---------------------------------------------------------

  function updateDashboardStats(reports) {
    const total =
      reports.length;

    const high =
      reports.filter(r =>
        ["HIGH", "CLUSTER"].includes(
          String(r.risk_level || "").toUpperCase()
        )
      ).length;

    const moderate =
      reports.filter(r =>
        ["MODERATE", "WATCH"].includes(
          String(r.risk_level || "").toUpperCase()
        )
      ).length;

    const low =
      reports.filter(r =>
        String(r.risk_level || "").toUpperCase() === "LOW"
      ).length;

    const affected =
      reports.reduce(
        (sum, r) =>
          sum + Number(r.affected_count || 0),
        0
      );

    const setStat = (id, value) => {
      const element = $(id);

      if (element) {
        element.textContent = value;
      }
    };

    setStat("totalCases", total);
    setStat("highRiskCases", high);
    setStat("moderateRiskCases", moderate);
    setStat("lowRiskCases", low);
    setStat("affectedAnimals", affected);
  }

  // ---------------------------------------------------------
  // CASE TABLE
  // ---------------------------------------------------------

  function renderCaseTable(reports) {
    const tbody =
      $("caseTableBody") ||
      document.querySelector("#caseTable tbody");

    if (!tbody) return;

    tbody.innerHTML = reports
      .slice()
      .sort(
        (a, b) =>
          Number(b.risk_score || 0) -
          Number(a.risk_score || 0)
      )
      .map(report => {
        const level =
          String(
            report.risk_level || "LOW"
          ).toUpperCase();

        return `
          <tr>
            <td>${escapeHTML(report.village || "—")}</td>

            <td>
              ${escapeHTML(
                report.animal_type || "—"
              )}
            </td>

            <td>
              ${Number(report.affected_count || 0)}
            </td>

            <td>
              <span class="risk-badge ${riskClass(level)}">
                ${escapeHTML(level)}
              </span>
            </td>

            <td>
              ${Number(report.risk_score || 0)}/100
            </td>

            <td>
              ${escapeHTML(report.date || "—")}
            </td>
          </tr>
        `;
      })
      .join("");
  }

  // ---------------------------------------------------------
  // TREND CHART
  // ---------------------------------------------------------

  function renderTrendChart(reports) {
    const canvas =
      $("trendChart");

    if (!canvas || typeof Chart === "undefined") {
      return;
    }

    const grouped = {};

    reports.forEach(report => {
      const date =
        report.date ||
        String(report.created_at || "").slice(0, 10) ||
        "Unknown";

      if (!grouped[date]) {
        grouped[date] = {
          total: 0,
          high: 0,
          moderate: 0,
          low: 0
        };
      }

      grouped[date].total++;

      const level =
        String(
          report.risk_level || "LOW"
        ).toUpperCase();

      if (level === "HIGH") {
        grouped[date].high++;
      } else if (
        level === "MODERATE" ||
        level === "WATCH"
      ) {
        grouped[date].moderate++;
      } else {
        grouped[date].low++;
      }
    });

    const dates =
      Object.keys(grouped).sort();

    const chartData = {
      labels: dates,
      datasets: [
        {
          label: "High Risk",
          data: dates.map(d => grouped[d].high)
        },
        {
          label: "Watch / Moderate",
          data: dates.map(d => grouped[d].moderate)
        },
        {
          label: "Low Risk",
          data: dates.map(d => grouped[d].low)
        }
      ]
    };

    if (canvas._pashuChart) {
      canvas._pashuChart.destroy();
    }

    canvas._pashuChart =
      new Chart(canvas, {
        type: "line",
        data: chartData,
        options: {
          responsive: true,
          maintainAspectRatio: false,

          interaction: {
            intersect: false,
            mode: "index"
          },

          plugins: {
            legend: {
              display: true
            }
          },

          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                precision: 0
              }
            }
          }
        }
      });
  }

  // ---------------------------------------------------------
  // DASHBOARD INIT
  // ---------------------------------------------------------

  async function initDashboard() {
    const mapElement = $("risk-map");

    if (!mapElement) return;

    const reports =
      await loadReports();

    initMap();

    const filtered =
      applyMapFilters(reports);

    renderHeatmap(filtered);
    updateDashboardStats(filtered);
    renderCaseTable(filtered);
    renderTrendChart(reports);
    initMapFilters(reports);
  }

  // ---------------------------------------------------------
  // ONLINE/OFFLINE STATUS
  // ---------------------------------------------------------

  function initNetworkStatus() {
    const update = () => {
      const status = $("networkStatus");

      if (!status) return;

      if (navigator.onLine) {
        status.textContent = "🟢 Online";
        status.className = "online";
      } else {
        status.textContent = "🔴 Offline";
        status.className = "offline";
      }
    };

    window.addEventListener("online", update);
    window.addEventListener("offline", update);

    update();
  }

  // ---------------------------------------------------------
  // APP START
  // ---------------------------------------------------------

  document.addEventListener("DOMContentLoaded", async () => {
    initSymptomChips();
    initGPS();
    initImagePreview();
    initImageScreening();
    initVoiceReporting();
    initReportSubmit();
    initNetworkStatus();

    await syncOfflineReports();

    // Dashboard only initializes when map exists.
    await initDashboard();
  });

})();
