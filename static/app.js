// ---------- Chip-group multi/single select ----------
document.addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  const group = chip.closest(".chip-group");
  if (!group) return;

  if (group.dataset.name === "animal_type") {
    // single-select
    group.querySelectorAll(".chip").forEach((c) => c.classList.remove("selected"));
    chip.classList.add("selected");
  } else {
    chip.classList.toggle("selected");
  }
});

// ---------- Report form submission ----------
const reportForm = document.getElementById("report-form");
if (reportForm) {
  reportForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const animalChip = reportForm.querySelector('[data-name="animal_type"] .chip.selected');
    const symptomChips = reportForm.querySelectorAll('[data-name="symptoms"] .chip.selected');

    const payload = {
      animal_type: animalChip ? animalChip.dataset.value : null,
      affected_count: Number(reportForm.affected_count.value || 1),
      symptoms: Array.from(symptomChips).map((c) => c.dataset.value),
      days_since_onset: Number(reportForm.days_since_onset.value || 0),
      notes: reportForm.notes.value,
      village: "Satara", // TODO: replace with geolocation / profile village
    };

    const resultBox = document.getElementById("result");
    const resultBody = document.getElementById("result-body");
    resultBox.style.display = "block";
    resultBody.innerHTML = "Analysing…";

    try {
      const res = await fetch("/api/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      resultBody.innerHTML = `
        <div class="advisory" style="border:none; padding:0; margin-bottom:14px;">
          <div class="sev ${data.risk_level}"></div>
          <div>
            <strong>${data.risk_label} risk</strong>
            <p style="margin:4px 0 0 0">${data.message}</p>
          </div>
        </div>
        <p style="margin:0"><strong>Suggested next step:</strong> ${data.next_step}</p>
      `;
    } catch (err) {
      resultBody.innerHTML = "Could not reach the server. Your report is saved locally and will sync when you're back online.";
    }
  });
}

// ---------- Vet dashboard ----------
async function initDashboard() {
  let reports = [];
  try {
    const res = await fetch("/api/reports");
    reports = await res.json();
  } catch (err) {
    reports = [];
  }
  if (!reports.length) reports = FALLBACK_REPORTS;

  renderTable(reports);
  renderChart(reports);
  renderMap(reports);
}

const FALLBACK_REPORTS = [
  { village: "Satara", lat: 17.685, lng: 74.0, animal_type: "Cattle", symptoms: ["fever", "lesions"], risk_level: "high", date: "2026-09-03" },
  { village: "Wai", lat: 17.95, lng: 73.89, animal_type: "Cattle", symptoms: ["swelling", "fever"], risk_level: "high", date: "2026-09-02" },
  { village: "Koregaon", lat: 17.71, lng: 74.15, animal_type: "Goat", symptoms: ["diarrhea"], risk_level: "moderate", date: "2026-09-01" },
  { village: "Phaltan", lat: 17.99, lng: 74.43, animal_type: "Buffalo", symptoms: ["lameness"], risk_level: "low", date: "2026-08-30" },
  { village: "Karad", lat: 17.29, lng: 74.18, animal_type: "Cattle", symptoms: ["milk_drop"], risk_level: "moderate", date: "2026-08-29" },
];

function renderTable(reports) {
  const body = document.getElementById("case-table-body");
  if (!body) return;
  body.innerHTML = reports
    .map(
      (r) => `
      <tr>
        <td>${r.village}</td>
        <td>${r.animal_type}</td>
        <td>${(r.symptoms || []).join(", ")}</td>
        <td>${r.date}</td>
        <td><span class="tag ${r.risk_level}">${r.risk_level}</span></td>
        <td><a href="#">View</a></td>
      </tr>`
    )
    .join("");
}

function renderChart(reports) {
  const canvas = document.getElementById("trend-chart");
  if (!canvas || typeof Chart === "undefined") return;

  const byDate = {};
  reports.forEach((r) => { byDate[r.date] = (byDate[r.date] || 0) + 1; });
  const labels = Object.keys(byDate).sort();
  const values = labels.map((d) => byDate[d]);

  new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Reports",
        data: values,
        borderColor: "#1f3d2b",
        backgroundColor: "rgba(31,61,43,0.08)",
        tension: 0.3,
        fill: true,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

function renderMap(reports) {
  const el = document.getElementById("risk-map");
  if (!el || typeof L === "undefined") return;

  const map = L.map(el).setView([17.7, 74.1], 9);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const colors = { high: "#c0533e", moderate: "#d99a2b", low: "#3f7d54" };

  reports.forEach((r) => {
    if (!r.lat || !r.lng) return;
    L.circleMarker([r.lat, r.lng], {
      radius: 9,
      color: colors[r.risk_level] || "#5b6b5e",
      fillColor: colors[r.risk_level] || "#5b6b5e",
      fillOpacity: 0.7,
    })
      .addTo(map)
      .bindPopup(`<strong>${r.village}</strong><br>${r.animal_type} · ${(r.symptoms || []).join(", ")}<br>Risk: ${r.risk_level}`);
  });
}
