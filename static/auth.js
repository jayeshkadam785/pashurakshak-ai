(function () {
  const url = document.body.dataset.supabaseUrl || "";
  const key = document.body.dataset.supabaseKey || "";
  let client = null;

  if (window.supabase && url && key) {
    client = window.supabase.createClient(url, key);
  }

  window.PashuAuth = {
    client,

    async login(email, password) {
      if (!client) throw new Error("Supabase Auth is not configured.");
      return client.auth.signInWithPassword({ email, password });
    },

    async signup(email, password, role) {
      if (!client) throw new Error("Supabase Auth is not configured.");
      return client.auth.signUp({
        email,
        password,
        options: { data: { role: role || "farmer" } }
      });
    },

    async session() {
      if (!client) return null;
      const { data } = await client.auth.getSession();
      return data.session || null;
    },

    async token() {
      const session = await this.session();
      return session ? session.access_token : null;
    },

    async logout() {
      if (client) await client.auth.signOut();
      localStorage.removeItem("pashu_role");
      location.href = "/login";
    },

    setRole(role) {
      localStorage.setItem("pashu_role", role);
    },

    role() {
      return localStorage.getItem("pashu_role") || "farmer";
    },

    async requireLogin() {
      const session = await this.session();
      if (!session) {
        location.href = "/login";
        return null;
      }
      return session;
    },

    async authFetch(url, options = {}) {
      const token = await this.token();
      const headers = new Headers(options.headers || {});
      if (token) headers.set("Authorization", "Bearer " + token);

      if (options.body && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }

      return fetch(url, { ...options, headers });
    }
  };

  document.addEventListener("DOMContentLoaded", async () => {
    if (document.body.dataset.protected === "true") {
      await window.PashuAuth.requireLogin();
    }

    document.querySelectorAll("[data-logout]").forEach(btn => {
      btn.addEventListener("click", () => window.PashuAuth.logout());
    });
  });
})();
