(function () {

  async function call(url, options = {}) {

    const response = window.PashuAuth
      ? await window.PashuAuth.authFetch(url, options)
      : await fetch(url, options);

    const data = await response.json().catch(() => ({}));

    if (!response.ok || data.success === false) {
      throw new Error(
        data.error || "Request failed"
      );
    }

    return data;
  }


  window.PashuFeatures = {

    // 🩺 Vet Case Verification
    verifyCase(id, payload) {
      return call(
        "/api/cases/" +
        encodeURIComponent(id) +
        "/verify",
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );
    },


    // 💉 Add Vaccination
    addVaccination(payload) {
      return call(
        "/api/vaccinations",
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );
    },


    // 💉 Get Vaccination Records
    vaccinations() {
      return call("/api/vaccinations");
    },


    // 🗺️ Outbreak Risk
    outbreakRisk() {
      return call("/api/outbreak-risk");
    },


    // 📊 Dashboard KPIs
    kpis() {
      return call("/api/dashboard-kpis");
    }

  };

})();
