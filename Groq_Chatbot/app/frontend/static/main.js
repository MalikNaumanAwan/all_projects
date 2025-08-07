let currentUserId = null; // 🔐 Global user ID
const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const chatBox = document.getElementById("chat-box");
let sessionId = localStorage.getItem("chat_session_id") || null;

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

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
    const token = localStorage.getItem("token");

    // 🔍 Load existing session_id from localStorage if available
    let sessionId = currentSessionId;

    const headers = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // 📨 Send chat request
    const response = await fetch("http://localhost:2000/chat", {
      method: "POST",
      headers,
      body: JSON.stringify({
        session_id: sessionId, // ✅ Send existing or null session_id
        messages: [{ role: "user", content: text }],
        model: model,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    // ✅ Parse backend response
    const data = await response.json();

    // 💾 If backend returns a session_id, store it in localStorage
    if (data.session_id && data.session_id !== sessionId) {
      sessionId = data.session_id;
      localStorage.setItem("chat_session_id", sessionId);
      console.log("💾 Stored session_id:", sessionId);
    }
    await fetchAndRenderSessions();
    // 🧠 Update streamed bot response
    streamBubble.update(data.response);
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

function createBubble(role, content) {
  const wrapper = document.createElement("div");
  wrapper.className = `w-full flex ${
    role === "user" ? "justify-end" : "justify-start"
  } mb-2`;
  const bubble = document.createElement("div");
  bubble.className = `
            text-sm leading-relaxed px-4 py-2 rounded-2xl max-w-2xl whitespace-pre-wrap break-words shadow
            ${
              role === "user"
                ? "bg-gray-300 text-black rounded-br-none"
                : "bg-gray-100 text-black rounded-bl-none"
            }
          `;
  bubble.innerHTML = content
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>");
  wrapper.appendChild(bubble);
  chatBox.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function createStreamedBubble(role) {
  const wrapper = document.createElement("div");
  wrapper.className = `w-full flex ${
    role === "user" ? "justify-end" : "justify-start"
  } mb-2`;
  const bubble = document.createElement("div");
  bubble.className = `
            text-sm leading-relaxed px-4 py-2 rounded-2xl max-w-2xl whitespace-pre-wrap break-words shadow
            ${
              role === "user"
                ? "bg-gray-300 text-black rounded-br-none"
                : "bg-gray-100 text-black rounded-bl-none"
            }
          `;
  const contentDiv = document.createElement("div");
  const typingIndicator = document.createElement("div");
  typingIndicator.className = "typing-indicator";
  typingIndicator.innerHTML = "<span></span><span></span><span></span>";
  bubble.appendChild(contentDiv);
  bubble.appendChild(typingIndicator);
  wrapper.appendChild(bubble);
  return {
    wrapper,
    update(text) {
      typingIndicator.style.display = "none";
      contentDiv.innerHTML = marked.parse(text);
    },
  };
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    chatBox.scrollTop = chatBox.scrollHeight;
  });
}
const API_BASE = "http://localhost:2000"; // Adjust to your backend

function showAuthModal() {
  document.getElementById("auth-modal").classList.remove("hidden");
}

function hideAuthModal() {
  document.getElementById("auth-modal").classList.add("hidden");
}

let isLogin = true;
document.getElementById("auth-toggle").onclick = () => {
  isLogin = !isLogin;
  document.getElementById("auth-title").innerText = isLogin
    ? "Login"
    : "Register";
  document.getElementById("auth-toggle").innerText = isLogin
    ? "No account? Register"
    : "Have account? Login";
};

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
    await loadProfile();
  } else {
    alert("Registration successful. You may now login.");
    isLogin = true;
    document.getElementById("auth-title").innerText = "Login";
    document.getElementById("auth-toggle").innerText = "No account? Register";
  }
}

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
}

function logout() {
  localStorage.removeItem("token");
  location.reload();
}

// Initialize on load
window.addEventListener("DOMContentLoaded", loadProfile);

//*********************RENDER SESSIONS******************************* */
let chatSessions = [];
let currentSessionId = null;

async function fetchAndRenderSessions() {
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
  chatSessions = data.sessions; // ✅ Fix here
  renderSidebarSessions(chatSessions);
}

function renderSidebarSessions(sessions) {
  const sidebar = document.getElementById("chat-sessions");
  sidebar.innerHTML = "";

  sessions.forEach((session) => {
    const button = document.createElement("button");
    button.className =
      "block w-full text-left px-3 py-2 rounded text-sm border " +
      (session.id === currentSessionId
        ? "bg-blue-600 border-blue-500"
        : "bg-gray-800 hover:bg-gray-700 border-gray-700");

    button.textContent = session.title || `Chat ${session.id.slice(0, 6)}`;
    button.onclick = () => loadChatFromSession(session);
    sidebar.appendChild(button);
  });
}
//***************************************************************** */
function clearChatUI() {
  const container = document.getElementById("chat-container");
  if (container) {
    container.innerHTML = "";
  }
}

//***************************************************************** */
async function loadChatFromSession(sessionMeta) {
  currentSessionId = sessionMeta.id;
  localStorage.setItem("chat_session_id", currentSessionId);

  // ✅ CLEAR CHATBOX
  chatBox.innerHTML = "";

  try {
    const token = localStorage.getItem("token");
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    const response = await fetch(
      `http://localhost:2000/chat/session/${sessionMeta.id}/messages`,
      { headers }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const sessionData = await response.json();

    // Render all messages from selected session
    sessionData.messages.forEach((msg) => createBubble(msg.role, msg.content));

    scrollToBottom();
  } catch (err) {
    createBubble("bot", `❌ Failed to load chat: ${err.message}`);
    console.error("Chat load error:", err);
  }
}

//******************************************************************** */
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
