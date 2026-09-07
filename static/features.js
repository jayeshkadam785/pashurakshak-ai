```javascript
(function () {
  "use strict";

  /*
   * PashuRakshak AI
   * Feature API Client
   *
   * All requests automatically use PashuAuth.authFetch()
   * when authentication is available.
   */

  async function call(url, options = {}) {
    let response;

    try {
      if (window.PashuAuth && typeof window.PashuAuth.authFetch === "function") {
        response = await window.PashuAuth.authFetch(url, options);
      } else {
        response = await fetch(url, options);
      }
    } catch (error) {
      console.error("API network error:", error);
      throw new Error(
        "Unable to connect to PashuRakshak server."
      );
    }

    let data = {};

    try {
      data = await response.json();
    } catch (error) {
      data = {};
    }

    /*
     * Authentication failure
     */
    if (response.status === 401) {
      throw new Error(
        "Your login session has expired. Please login again."
      );
    }

    /*
     * Permission failure
     */
    if (response.status === 403) {
      throw new Error(
        "You do not have permission to perform this action."
      );
    }

    /*
     * General API failure
     */
    if (!response.ok || data.success === false) {
      throw new Error(
        data.error ||
        data.message ||
        "Request failed. Please try again."
      );
    }

    return data;
  }


  /*
   * ============================================================
   * PUBLIC FEATURE API
   * ============================================================
   */

  window.PashuFeatures = {

    /*
     * 🩺 Vet Case Verification
     *
     * Example:
     * PashuFeatures.verifyCase(caseId, {
     *   case_status: "VERIFIED",
     *   vet_notes: "Animal examined",
     *   diagnosis: "Suspected infection",
     *   treatment: "Supportive treatment"
     * });
     */
    async verifyCase(id, payload = {}) {
      if (!id) {
        throw new Error("Case ID is required.");
      }

      return await call(
        "/api/cases/" +
        encodeURIComponent(id) +
        "/verify",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        }
      );
    },


    /*
     * 💉 Add Vaccination Record
     *
     * Required backend fields:
     * species
     * vaccine_name
     * vaccination_date
     */
    async addVaccination(payload = {}) {
      if (!payload.species) {
        throw new Error("Animal species is required.");
      }

      if (!payload.vaccine_name) {
        throw new Error("Vaccine name is required.");
      }

      if (!payload.vaccination_date) {
        throw new Error("Vaccination date is required.");
      }

      return await call(
        "/api/vaccinations",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        }
      );
    },


    /*
     * 💉 Get Vaccination Records
     */
    async vaccinations() {
      return await call(
        "/api/vaccinations",
        {
          method: "GET"
        }
      );
    },


    /*
     * 🚨 Outbreak Risk
     *
     * Returns location-wise outbreak risk clusters.
     */
    async outbreakRisk() {
      return await call(
        "/api/outbreak-risk",
        {
          method: "GET"
        }
      );
    },


    /*
     * 📊 Dashboard KPIs
     *
     * Returns:
     * total_cases
     * high_risk_cases
     * moderate_cases
     * animals_affected
     * verified_cases
     */
    async kpis() {
      return await call(
        "/api/dashboard-kpis",
        {
          method: "GET"
        }
      );
    },


    /*
     * ❤️ Feature Health Check
     */
    async health() {
      return await call(
        "/api/feature-health",
        {
          method: "GET"
        }
      );
    },


    /*
     * 🔐 Check whether user is logged in
     */
    async isAuthenticated() {
      try {
        if (
          !window.PashuAuth ||
          typeof window.PashuAuth.session !== "function"
        ) {
          return false;
        }

        const session = await window.PashuAuth.session();

        return !!session;
      } catch (error) {
        console.error(
          "Authentication check failed:",
          error
        );

        return false;
      }
    }

  };


  /*
   * ============================================================
   * DEBUG / DEVELOPMENT INFO
   * ============================================================
   */

  console.log(
    "✅ PashuRakshak Features API loaded."
  );

})();
```

### Ab kya karna hai

1. `static/features.js` open karo.
2. **Old complete code delete** karo.
3. Upar wala code paste karo.
4. Save.
5. GitHub par commit karo:

**Commit message:**
`Improve feature API client and authentication handling`

6. Vercel ko redeploy hone do.

### Phir test karo

Open:

`https://pashurakshak-ai.vercel.app/login`

Login → **Vet Cases**

Then browser console me:

```javascript
PashuFeatures.health()
```

Expected:

```json
{
  "success": true,
  "features": [
    "authentication",
    "role_based_access",
    "vet_verification",
    "smart_alerts",
    "vaccination_tracking",
    "outbreak_prediction"
  ],
  "supabase": true
}
```

**Important:** frontend token bhej raha hai, lekin abhi backend ke `/api/reports` aur feature endpoints JWT ko properly verify nahi kar rahe. Isliye next step **real server-side Supabase authentication + role-based access + RLS** banana hona chahiye. यही security part production/SIH demo ke liye important hai.
