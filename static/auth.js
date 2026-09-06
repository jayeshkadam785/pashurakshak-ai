(function () {
  const url = document.body.dataset.supabaseUrl || "";
  const key = document.body.dataset.supabaseKey || "";

  let client = null;

  // Initialize Supabase
  if (window.supabase && url && key) {
    client = window.supabase.createClient(url, key);
  }

  window.PashuAuth = {

    client: client,

    // Login
    async login(email, password) {
      if (!client) {
        throw new Error("Supabase Auth is not configured.");
      }

      return await client.auth.signInWithPassword({
        email: email,
        password: password
      });
    },

    // Signup
    async signup(email, password, role) {
      if (!client) {
        throw new Error("Supabase Auth is not configured.");
      }

      return await client.auth.signUp({
        email: email,
        password: password,
        options: {
          data: {
            role: role || "farmer"
          }
        }
      });
    },

    // Get current session
    async session() {
      if (!client) {
        return null;
      }

      const { data } = await client.auth.getSession();

      return data.session || null;
    },

    // Get access token
    async token() {
      const session = await this.session();

      return session
        ? session.access_token
        : null;
    },

    // Logout
    async logout() {
      if (client) {
        await client.auth.signOut();
      }

      localStorage.removeItem("pashu_role");

      window.location.href = "/login";
    },

    // Save role
    setRole(role) {
      localStorage.setItem("pashu_role", role);
    },

    // Get role
    role() {
      return localStorage.getItem("pashu_role") || "farmer";
    },

    // Protect page
    async requireLogin() {
      const session = await this.session();

      if (!session) {
        window.location.href = "/login";
        return null;
      }

      return session;
    },

    // Authenticated API request
    async authFetch(url, options = {}) {
      const token = await this.token();

      const headers = new Headers(
        options.headers || {}
      );

      if (token) {
        headers.set(
          "Authorization",
          "Bearer " + token
        );
      }

      if (
        options.body &&
        !headers.has("Content-Type")
      ) {
        headers.set(
          "Content-Type",
          "application/json"
        );
      }

      return await fetch(url, {
        ...options,
        headers: headers
      });
    }
  };


  // Protect pages marked with data-protected="true"
  document.addEventListener(
    "DOMContentLoaded",
    async function () {

      if (
        document.body.dataset.protected === "true"
      ) {
        await window.PashuAuth.requireLogin();
      }

      // Logout buttons
      document
        .querySelectorAll("[data-logout]")
        .forEach(function (button) {

          button.addEventListener(
            "click",
            function () {
              window.PashuAuth.logout();
            }
          );

        });

    }
  );

})();
