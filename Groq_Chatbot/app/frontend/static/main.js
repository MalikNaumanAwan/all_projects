// Global variables
let currentUserId = null; // 🔐 Global user ID
let currentSessionId = localStorage.getItem("chat_session_id") || null;
let chatSessions = [];
let isLogin = true;
const API_BASE = "http://192.168.100.4:2022"; // Adjust to your backend

// DOM elements
const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const chatBox = document.getElementById("chat-box");
const placeholder = document.getElementById("placeholder-message");
const ta = document.getElementById("user-input");
// Event listeners
window.addEventListener("DOMContentLoaded", async () => {
  await loadProfile();
  await fetchAndRenderSessions(true);
  await fetchAndRenderModels(true);
});

document.addEventListener("DOMContentLoaded", () => {
  setupApiKeyModal();
  setupAuthModal();
});
//**************************************************************************** */
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  // Hide placeholder when the first message is sent
  if (placeholder) {
    placeholder.style.display = "none";
  }
  // Reset textarea
  ta.value = "";
  ta.autogrowResize(); // recompute height to minimal state
  // Render user bubble
  createBubble("user", text);
  input.value = "";
  input.focus();

  // Prepare bot bubble for streaming
  const streamBubble = createStreamedBubble("bot");
  chatBox.appendChild(streamBubble.wrapper);
  scrollToBottom();

  try {
    const model = document.getElementById("model-select").value;
    const category = document.getElementById("mode-select").value;
    const token = localStorage.getItem("token");
    // ✅ Read web search checkbox
    const webSearch = document.getElementById("web-search-toggle").checked;

    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    // 📨 Send chat request with web_search flag
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        session_id: currentSessionId,
        messages: [{ role: "user", content: text }],
        model: model,
        category: category,
        web_search: webSearch, // 👈 Added flag here
      }),
    });
    // 🔍 Debug log before sending
    console.log("🚀 Sending payload:", webSearch);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    // ✅ Parse backend response
    const data = await response.json();

    // 💾 Store new session_id if provided
    if (data.session_id && data.session_id !== currentSessionId) {
      currentSessionId = data.session_id;
      localStorage.setItem("chat_session_id", currentSessionId);
      console.log("💾 Stored session_id:", currentSessionId);
    }

    await fetchAndRenderSessions();

    // 🧠 Merge model + response for display
    const mergedResponse = `**|\`${data.model}\`|**\n\n\n${data.response}`;

    // 🔄 Update dropdown to reflect actual model used
    const modelSelect = document.getElementById("model-select");
    if (modelSelect && data.model) {
      // If the model already exists in the dropdown → select it
      let option = Array.from(modelSelect.options).find(
        (opt) => opt.value === data.model
      );

      // If the model is missing → add it dynamically
      if (!option) {
        option = new Option(data.model, data.model, true, true);
        modelSelect.add(option);
      }

      modelSelect.value = data.model;
    }

    // 🧠 Update streamed bot response
    fakeStreamText(mergedResponse, streamBubble, 1);
    scrollToBottom();
  } catch (err) {
    // 💥 Remove broken bot bubble if render failed
    if (streamBubble?.wrapper?.parentNode) {
      streamBubble.wrapper.remove();
    }
    createBubble("bot", `❌ Error: ${err.message}`);
    console.error("Chat error:", err);
  }
});
//************************************************************************ */
// Functions
async function setupApiKeyModal() {
  const apiKeyBtn = document.getElementById("api-key-btn");
  const apiKeyModal = document.getElementById("api-key-modal");
  const cancelApiKeyButtons = document.querySelectorAll("#cancel-api-key");
  const saveApiKey = document.getElementById("save-api-key");

  if (apiKeyBtn && apiKeyModal) {
    apiKeyBtn.addEventListener("click", () => {
      apiKeyModal.classList.remove("hidden");
    });
  }

  cancelApiKeyButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      apiKeyModal.classList.add("hidden");
    });
  });

  if (saveApiKey && apiKeyModal) {
    saveApiKey.addEventListener("click", async () => {
      const key = document.getElementById("api-key-input").value.trim();
      const provider = document.getElementById("select-provider").value;
      const token = localStorage.getItem("token");

      if (!key) {
        alert("Please enter a valid API key.");
        return;
      }

      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      try {
        const response = await fetch(`${API_BASE}/save_api_key`, {
          method: "POST",
          headers,
          body: JSON.stringify({ api_provider: provider, api_key: key }),
        });

        if (!response.ok) {
          const err = await response.json();
          alert(`Failed to save API key: ${err.detail || response.statusText}`);
          return;
        }

        apiKeyModal.classList.add("hidden");
        alert("API key saved successfully.");
        location.reload();
      } catch (error) {
        alert("Network error while saving API key.");
        console.error(error);
      }
    });
  }
  apiKeyModal.addEventListener("click", (e) => {
    if (e.target === apiKeyModal) {
      apiKeyModal.classList.add("hidden");
    }
  });
}
//************************************************************************ */
function setupAuthModal() {
  const authModal = document.getElementById("auth-modal");

  // Add click listener on backdrop to close modal if clicked outside modal content
  authModal.addEventListener("click", (e) => {
    if (e.target === authModal) {
      authModal.classList.add("hidden");
    }
  });

  document.getElementById("auth-toggle").onclick = () => {
    isLogin = !isLogin;
    document.getElementById("auth-title").innerText = isLogin
      ? "Login"
      : "Register";
    document.getElementById("auth-toggle").innerText = isLogin
      ? "No account? Register"
      : "Have account? Login";
  };
}
//************************************************************************ */
async function submitAuth() {
  const email = document.getElementById("auth-email").value;
  const password = document.getElementById("auth-password").value;

  const endpoint = isLogin ? "/login" : "/register";
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await res.json();
  if (!res.ok) return alert(data.detail || "Auth failed");

  if (isLogin) {
    localStorage.setItem("token", data.access_token);
    hideAuthModal();
    location.reload();
    await loadProfile();
    await fetchAndRenderSessions(true);
    await fetchAndRenderModels(); // ⬅ fetch models right after login
  } else {
    alert("Registration successful. Verification Link Sent to Email.");
    isLogin = true;
    document.getElementById("auth-title").innerText = "Login";
    document.getElementById("auth-toggle").innerText = "No account? Register";
  }
}
//************************************************************************ */
async function loadProfile() {
  const token = localStorage.getItem("token");
  if (!token) return;

  const res = await fetch(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) return logout();

  const user = await res.json();
  currentUserId = user.id; // ✅ Save for session creation
  document.getElementById("login-btn").classList.add("hidden");
  document.getElementById("profile-menu").classList.remove("hidden");
  document.getElementById("profile-email").innerText = user.email;

  const profileBtn = document.getElementById("profile-btn");
  const dropdown = document.getElementById("profile-dropdown");
  profileBtn.onclick = () => dropdown.classList.toggle("hidden");

  await fetchAndRenderSessions(); // 🔥 fetch sessions on login
  await fetchAndRenderModels();
}

function logout() {
  localStorage.removeItem("token");
  location.reload();
}
//************************************************************************ */
async function fetchAndRenderSessions(loadFirstSession = false) {
  const token = localStorage.getItem("token");
  if (!token) return;

  const res = await fetch(`${API_BASE}/get_sessions`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    console.error("Failed to fetch sessions");
    return;
  }

  const data = await res.json();
  chatSessions = data.sessions;
  renderSidebarSessions(chatSessions);

  if (loadFirstSession) {
    // Check currentSessionId validity
    let validSession = chatSessions.find((s) => s.id === currentSessionId);

    if (!validSession && chatSessions.length > 0) {
      // No valid session — load first session by default
      currentSessionId = chatSessions[0].id;
      localStorage.setItem("chat_session_id", currentSessionId);
      validSession = chatSessions[0];
    }

    if (validSession) {
      console.log(validSession.model);
      await loadChatFromSession(validSession);
    }
  }
}
//************************************************************************ */
function renderSidebarSessions(sessions) {
  const sidebar = document.getElementById("chat-sessions");
  sidebar.innerHTML = "";

  sessions.forEach((session) => {
    // Outer container for chat + menu
    const container = document.createElement("div");
    container.className =
      "relative group flex items-center justify-between px-3 py-2 rounded text-sm border mb-1 " +
      (session.id === currentSessionId
        ? "bg-blue-600 border-blue-500"
        : "bg-gray-800 hover:bg-gray-700 border-gray-700");

    // Chat title button (click to load chat)
    const titleBtn = document.createElement("button");
    titleBtn.className = "flex-1 text-left";
    titleBtn.textContent = session.title || `Chat ${session.id.slice(0, 6)}`;
    titleBtn.onclick = () => loadChatFromSession(session);

    // Three-dot menu button
    const menuBtn = document.createElement("button");
    menuBtn.className = "ml-2 text-gray-400 hover:text-white";
    menuBtn.innerHTML = "&#8942;"; // ⋮ symbol
    menuBtn.onclick = (e) => {
      e.stopPropagation(); // Prevent loading chat when clicking dots
      const dropdown = container.querySelector(".dropdown-menu");
      dropdown.classList.toggle("hidden");
    };

    // Dropdown menu
    const dropdown = document.createElement("div");
    dropdown.className =
      "dropdown-menu hidden absolute right-2 top-8 bg-gray-900 border border-gray-700 rounded shadow-lg z-10";
    dropdown.innerHTML = `
      <button class="block w-full text-left px-4 py-2 hover:bg-red-600 text-white">Delete Chat</button>
    `;

    // Delete button action
    dropdown.querySelector("button").onclick = async () => {
      await deleteChatSession(session.id);
      dropdown.classList.add("hidden");
    };

    container.appendChild(titleBtn);
    container.appendChild(menuBtn);
    container.appendChild(dropdown);
    sidebar.appendChild(container);
  });
}
//************************************************************************ */
async function deleteChatSession(sessionId) {
  const token = localStorage.getItem("token");
  if (!token) return alert("You must be logged in.");

  const res = await fetch(`${API_BASE}/chat/delete_session/${sessionId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const err = await res.json();
    return alert(err.detail || "Failed to delete chat");
  }

  // Refresh sidebar after deletion
  await fetchAndRenderSessions();

  // If the deleted session was open, clear the chat box
  if (sessionId === currentSessionId) {
    chatBox.innerHTML = "";
    currentSessionId = null;
    localStorage.removeItem("chat_session_id");
  }
}
//************************************************************************ */
async function loadChatFromSession(sessionMeta) {
  currentSessionId = sessionMeta.id;
  localStorage.setItem("chat_session_id", currentSessionId);

  // 🔹 Re-render sidebar immediately so highlight changes
  renderSidebarSessions(chatSessions);

  // ✅ CLEAR CHATBOX
  chatBox.innerHTML = "";

  try {
    const token = localStorage.getItem("token");
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    const response = await fetch(
      `${API_BASE}/chat/session/${sessionMeta.id}/messages`,
      { headers }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const sessionData = await response.json();

    // Render all messages from selected session
    sessionData.messages.forEach((msg) => {
      let displayContent = msg.content;
      console.log(msg.model);
      if (msg.role === "assistant") {
        displayContent = `**|\`${msg.model}\`|**\n\n\n${msg.content}`;
      }
      console.log(displayContent);
      createBubble(msg.role, displayContent);
    });
    scrollToBottom();
  } catch (err) {
    createBubble("bot", `❌ Failed to load chat: ${err.message}`);
    console.error("Chat load error:", err);
  }
}
//************************************************************************ */
async function createNewChat() {
  const token = localStorage.getItem("token");
  const userRes = await fetch(`${API_BASE}/profile`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const user = await userRes.json();
  const res = await fetch(`${API_BASE}/chat/session`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      user_id: user.id,
      title: "New Chat Session",
    }),
  });

  if (!res.ok) {
    console.error("❌ Failed to create session");
    return;
  }

  const data = await res.json();
  console.log("✅ Created session:", data);
  currentSessionId = data.id;
  await fetchAndRenderSessions(); // reload sidebar
  loadChatFromSession({ id: data.id, title: data.title }); // ✅ clean & compatible
}
//************************************************************************ */
async function resendMessage(text) {
  // Render the user bubble again (optional: could highlight instead of duplicating)
  createBubble("user", text);

  // Prepare bot bubble for streaming
  const streamBubble = createStreamedBubble("bot");
  chatBox.appendChild(streamBubble.wrapper);
  scrollToBottom();

  try {
    const model = document.getElementById("model-select").value;
    const category = document.getElementById("mode-select").value;
    const token = localStorage.getItem("token");
    const webSearch = document.getElementById("web-search-toggle").checked;
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        session_id: currentSessionId,
        messages: [{ role: "user", content: text }],
        model: model,
        category: category,
        web_search: webSearch, // 👈 Added flag here
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.session_id && data.session_id !== currentSessionId) {
      currentSessionId = data.session_id;
      localStorage.setItem("chat_session_id", currentSessionId);
    }

    await fetchAndRenderSessions();

    // 🧠 Merge model + response for display
    const mergedResponse = `**|\`${data.model}\`|**\n\n\n${data.response}`;
    // 🔄 Update dropdown to reflect actual model used
    const modelSelect = document.getElementById("model-select");
    if (modelSelect && data.model) {
      // If the model already exists in the dropdown → select it
      let option = Array.from(modelSelect.options).find(
        (opt) => opt.value === data.model
      );

      // If the model is missing → add it dynamically
      if (!option) {
        option = new Option(data.model, data.model, true, true);
        modelSelect.add(option);
      }

      modelSelect.value = data.model;
    }
    // 🧠 Update streamed bot response
    fakeStreamText(mergedResponse, streamBubble, 1);
    scrollToBottom();
  } catch (err) {
    if (streamBubble?.wrapper?.parentNode) {
      streamBubble.wrapper.remove();
    }
    createBubble("bot", `❌ Error: ${err.message}`);
    console.error("Resend error:", err);
  }
}
//************************************************************************ */
async function fetchAndRenderModels() {
  const token = localStorage.getItem("token");
  if (!token) {
    console.warn("No token found — skipping model fetch.");
    return;
  }

  const selectEl = document.getElementById("model-select");
  const modeEl = document.getElementById("mode-select");

  if (!selectEl) {
    console.error("Model select element not found in DOM.");
    return;
  }
  if (!modeEl) {
    console.error("Mode select element not found in DOM.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/get_models`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) {
      console.error(`Failed to fetch models: ${res.status}`);
      selectEl.innerHTML = `<option disabled>Failed to load models</option>`;
      return;
    }

    const payload = await res.json();

    // Normalize payload
    const models = Array.isArray(payload)
      ? payload
      : payload.models || payload.data || [];

    if (!models.length) {
      selectEl.innerHTML = `<option disabled>No models available</option>`;
      return;
    }

    // 🔹 Restore last selected model + mode
    const lastSelectedModel = localStorage.getItem("selected_model_id");
    const lastSelectedMode = localStorage.getItem("selected_mode");

    selectEl.innerHTML = ""; // Clear previous

    // 🔹 Group models by category
    const grouped = {};
    console.log("Models payload:", models);
    models.forEach((m) => {
      const category = (m.category || "Uncategorized").toLowerCase();
      if (!grouped[category]) grouped[category] = [];
      grouped[category].push(m);
    });

    // 🔹 Render categories
    Object.entries(grouped).forEach(([category, modelsInCat]) => {
      // sort by rating descending
      modelsInCat.sort((a, b) => {
        const ra = parseInt(a.rating) || 0;
        const rb = parseInt(b.rating) || 0;
        return rb - ra;
      });

      const optGroup = document.createElement("optgroup");
      optGroup.label = category.charAt(0).toUpperCase() + category.slice(1);

      modelsInCat.forEach((m) => {
        const id = m.model_id ?? m.id ?? "";
        const provider = m.provider ?? "unknown";
        const rating = m.rating ?? "N/A";

        const opt = document.createElement("option");
        opt.value = id;
        opt.textContent = `${id} – ${provider} (⭐ ${rating})`;

        if (lastSelectedModel && id === lastSelectedModel) {
          opt.selected = true;
        }

        optGroup.appendChild(opt);
      });

      selectEl.appendChild(optGroup);
    });

    // 🔹 Restore mode selection if saved
    if (lastSelectedMode) {
      modeEl.value = lastSelectedMode;
    }

    // Save selection on change
    selectEl.addEventListener("change", () => {
      const selectedId = selectEl.value;
      localStorage.setItem("selected_model_id", selectedId);
    });

    modeEl.addEventListener("change", () => {
      const selectedMode = modeEl.value;
      localStorage.setItem("selected_mode", selectedMode);
    });
  } catch (err) {
    console.error("Error fetching models:", err);
    selectEl.innerHTML = `<option disabled>Error loading models</option>`;
  }
}

//************************************************************************ */
// Typing effect function
function fakeStreamText(text, streamBubble, baseDelay = 20) {
  const tokens = text.split(/(\s+)/); // keep spaces
  let index = 0;

  function step() {
    if (index < tokens.length) {
      streamBubble.appendParsed(tokens[index]);
      index++;

      const progress = index / tokens.length;
      const dynamicDelay = baseDelay * (1 - 0.99 * progress);

      scrollToBottom();
      setTimeout(step, dynamicDelay);
    } else {
      streamBubble.finish();
      scrollToBottom();
    }
  }

  step();
}
//************************************************************************ */
// Create bubble functions
function createBubble(role, content) {
  const wrapper = document.createElement("div");
  wrapper.className = `w-full flex ${
    role === "user" ? "justify-end" : "justify-start"
  } mb-2`;

  const bubble = document.createElement("div");
  bubble.className = `relative leading-relaxed px-4 py-2 rounded-2xl max-w-4xl break-words shadow ${
    role === "user"
      ? "bg-gray-200 text-black rounded-br-none"
      : "bg-gray-100 text-black rounded-bl-none"
  }`;

  const contentDiv = document.createElement("div");
  contentDiv.className = "bubble-content";
  contentDiv.innerHTML = marked.parse(content);

  const contentWrapper = document.createElement("div");
  contentWrapper.className = "content-wrapper";
  contentWrapper.appendChild(contentDiv);

  bubble.appendChild(contentWrapper);

  // 🔄 Add resend button only for user messages
  if (role === "user") {
    const resendBtn = document.createElement("button");
    resendBtn.innerHTML = "↻";
    resendBtn.title = "Resend message";
    resendBtn.className =
      "absolute -left-6 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-black";
    resendBtn.onclick = () => resendMessage(content);

    wrapper.classList.add("relative"); // so absolute resend button works
    bubble.appendChild(resendBtn);
  }

  wrapper.appendChild(bubble);
  chatBox.appendChild(wrapper);
  scrollToBottom();

  return wrapper;
}
//************************************************************************ */
function createStreamedBubble(role) {
  const wrapper = document.createElement("div");
  wrapper.className = `w-full flex ${
    role === "user" ? "justify-end" : "justify-start"
  } mb-2`;

  const bubble = document.createElement("div");
  bubble.className = `relative leading-relaxed px-4 py-2 rounded-2xl max-w-4xl break-words shadow ${
    role === "user"
      ? "bg-gray-200 text-black rounded-br-none"
      : "bg-gray-200 text-black rounded-bl-none"
  }`;

  const contentDiv = document.createElement("div");
  contentDiv.className = "bubble-content";

  const contentWrapper = document.createElement("div");
  contentWrapper.className = "content-wrapper";
  contentWrapper.appendChild(contentDiv);

  const typingIndicator = document.createElement("div");
  typingIndicator.className = "typing-indicator";
  typingIndicator.innerHTML = "<span></span><span></span><span></span>";

  bubble.appendChild(contentWrapper);
  bubble.appendChild(typingIndicator);
  wrapper.appendChild(bubble);

  let buffer = "";

  return {
    wrapper,
    update(text) {
      buffer = text || "";
      typingIndicator.style.display = "none";
      contentDiv.innerHTML = marked.parse(buffer);
      try {
        if (window.hljs) hljs.highlightAll();
      } catch (e) {}
    },
    appendParsed(chunk) {
      buffer += chunk;
      contentDiv.innerHTML = marked.parse(buffer);
      try {
        if (window.hljs) hljs.highlightAll();
      } catch (e) {}
    },
    finish() {
      typingIndicator.style.display = "none";
      contentDiv.innerHTML = marked.parse(buffer);
      try {
        if (window.hljs) hljs.highlightAll();
      } catch (e) {}
    },
    getText() {
      return buffer;
    },
  };
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    chatBox.scrollTop = chatBox.scrollHeight;
  });
}

// Helper functions
function showAuthModal() {
  document.getElementById("auth-modal").classList.remove("hidden");
}

function hideAuthModal() {
  document.getElementById("auth-modal").classList.add("hidden");
}

// Call after DOM is ready
document.addEventListener("DOMContentLoaded", fetchAndRenderModels);
//********************************************************* */
(function attachAutoGrow() {
  if (!ta) {
    console.error("AutoGrow: #user-input not found");
    return;
  }

  // === Config ===
  const MAX_PX = 288; // match Tailwind max-h-[18rem] if desired

  // === Create hidden mirror sizer (resilient to transforms & flex) ===
  const sizer = document.createElement("div");
  sizer.setAttribute("aria-hidden", "true");
  Object.assign(sizer.style, {
    position: "absolute",
    visibility: "hidden",
    height: "auto",
    top: "0",
    left: "-9999px",
    whiteSpace: "pre-wrap",
    wordWrap: "break-word",
    overflowWrap: "break-word",
    boxSizing: "border-box",
  });
  document.body.appendChild(sizer);

  // Helper: copy critical styles so measurement matches visual layout
  function copyStyles() {
    const cs = getComputedStyle(ta);
    const props = [
      "width",
      "paddingTop",
      "paddingRight",
      "paddingBottom",
      "paddingLeft",
      "borderTopWidth",
      "borderRightWidth",
      "borderBottomWidth",
      "borderLeftWidth",
      "fontFamily",
      "fontSize",
      "fontWeight",
      "fontStyle",
      "letterSpacing",
      "textTransform",
      "lineHeight",
      "textIndent",
      "tabSize",
      "wordSpacing",
      "whiteSpace",
    ];
    props.forEach((p) => (sizer.style[p] = cs[p]));
    // ensure sizer uses same width as textarea (account for box-sizing)
    sizer.style.width = ta.getBoundingClientRect().width + "px";
  }

  // Resize function uses mirror to compute exact height (robust)
  function resize() {
    copyStyles();
    // mirror content; add trailing newline ensures last line height counted
    const value = ta.value || ta.placeholder || "";
    sizer.textContent = value + "\n";
    const needed = sizer.scrollHeight;

    // apply height constrained by MAX_PX
    ta.style.height = "auto"; // reset so scrollHeight is accurate
    const scaleFactor = 0.85; // match your CSS transform scale
    const newHeight = Math.min(needed / scaleFactor, MAX_PX);
    ta.style.height = newHeight + "px";
    ta.style.overflowY = needed > MAX_PX ? "auto" : "hidden";
  }

  // Attach events: input, paste (deferred), change, programmatic checks
  ta.addEventListener("input", (e) => {
    // console debug to verify attachment
    if (window.__AUTOGROW_DEBUG) console.log("autogrow: input");
    resize();
  });

  ta.addEventListener("change", () => resize());

  ta.addEventListener("paste", () => {
    // pasted content is applied after paste event, so defer resize
    setTimeout(resize, 0);
  });

  // If content may be inserted programmatically, observe attribute/value changes
  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === "attributes" && m.attributeName === "value") {
        resize();
        break;
      }
    }
  });
  observer.observe(ta, { attributes: true });

  // Recompute on window resize (text wrapping changes height)
  window.addEventListener("resize", resize);

  // Initial sizing for prefilled values
  setTimeout(resize, 0);

  // Expose a manual hook if you want to trigger programmatically
  ta.autogrowResize = resize;
  // **Enter to submit, Shift+Enter for newline**
  ta.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (form) form.requestSubmit();
    }
  });

  // Debug hint
  if (window.__AUTOGROW_DEBUG) console.log("autogrow attached to #user-input");
})();
//***************************************************************************** */
document.addEventListener("DOMContentLoaded", async () => {
  const apiContainer = document.getElementById("api-container");
  const token = localStorage.getItem("token");

  async function loadApiKeys() {
    try {
      const response = await fetch(`${API_BASE}/get_api_keys`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch API keys");
      }

      const data = await response.json(); // { api_keys: [...] }
      const keys = Array.isArray(data?.api_keys) ? data.api_keys : [];

      apiContainer.innerHTML = ""; // clear old entries

      if (keys.length === 0) {
        apiContainer.innerHTML = `<p class="text-gray-400 text-sm">No API keys found</p>`;
        return;
      }

      keys.forEach((keyObj) => {
        const div = document.createElement("div");
        div.className =
          "flex items-center justify-between bg-gray-800 text-white px-3 py-2 rounded-md mb-2";

        // Optional masking
        const raw = keyObj.api_key ?? "";
        const masked =
          raw.length > 8 ? `${raw.slice(0, 4)}…${raw.slice(-4)}` : raw;

        div.innerHTML = `
          <span class="truncate">${keyObj.api_provider} — ${masked}</span>
          <button
            id="delete-btn-${keyObj.api_provider}"
            value="${keyObj.api_key}"
            class="ml-2 text-red-400 hover:text-red-600 text-sm"
            data-provider="${keyObj.api_provider}">
            Delete
          </button>
        `;

        apiContainer.appendChild(div);
      });
      attachDeleteHandlers();
    } catch (err) {
      console.error("⚠️ Error loading API keys:", err);
      apiContainer.innerHTML = `<p class="text-red-500 text-sm">Error loading keys</p>`;
    }
  }

  // Load immediately when page is ready
  await loadApiKeys();

  // Optional: re-fetch after "Add API Key" is clicked
  /* const addBtn = document.getElementById("api-key-btn");
  if (addBtn) {
    addBtn.addEventListener("click", async () => {
      // After adding a key elsewhere, refresh the list:
      await loadApiKeys();
    });
  } */
});
//**********************************DELETE API KEY***************************************** */
// Attach once after rendering all buttons
function attachDeleteHandlers() {
  document.querySelectorAll("button[id^='delete-btn-']").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const token = localStorage.getItem("token");
      const provider = btn.dataset.provider;
      const keyVal = btn.value;
      console.log(keyVal);
      if (!provider) {
        console.error("No provider found for delete");
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/delete_api_key`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ api_key: keyVal }), // optional, if backend requires
        });

        if (response.ok) {
          console.log(`Key deleted successfully`);
          location.reload();
          // Remove element from UI
          btn.parentElement.remove();
        } else {
          const err = await response.json();
          console.error("Failed to delete key:", err);
          alert("Error deleting API key");
        }
      } catch (err) {
        console.error("Request error:", err);
      }
    });
  });
}
