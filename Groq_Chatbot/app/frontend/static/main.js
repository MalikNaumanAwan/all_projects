let currentUserId = null; // 🔐 Global user ID
const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const chatBox = document.getElementById("chat-box");
let sessionId = localStorage.getItem("chat_session_id") || null;
// Typing effect function
function fakeStreamText(text, streamBubble, delay = 20) {
  // defensive: ensure we have a string
  const fullText = String(text || "");
  // Initialize raw text area (no markdown parsing while streaming)
  streamBubble.setRaw("");

  let i = 0;
  function step() {
    if (i < fullText.length) {
      // append one char (you can switch to word-chunks if you prefer)
      streamBubble.appendRaw(fullText.charAt(i));
      i++;
      // keep viewport anchored to bottom
      scrollToBottom();
      setTimeout(step, delay);
    } else {
      // done: parse markdown and apply syntax highlighting
      streamBubble.finish();
      scrollToBottom();
    }
  }
  step();
}

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
    // 🎯 Instead of instantly updating, fake stream it
    fakeStreamText(data.response, streamBubble, 3);
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
      relative text-sm leading-relaxed px-4 py-2 rounded-2xl max-w-2xl whitespace-pre-wrap break-words shadow
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

function createStreamedBubble(role) {
  const wrapper = document.createElement("div");
  wrapper.className = `w-full flex ${
    role === "user" ? "justify-end" : "justify-start"
  } mb-2`;

  const bubble = document.createElement("div");
  bubble.className = `
      relative text-sm leading-relaxed px-4 py-2 rounded-2xl max-w-2xl whitespace-pre-wrap break-words shadow
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

  // internal buffer for incremental updates
  let buffer = "";

  return {
    wrapper,
    // full update (final) — parse markdown & highlight
    update(text) {
      buffer = text || "";
      typingIndicator.style.display = "none";
      contentDiv.innerHTML = marked.parse(buffer);
      try {
        if (window.hljs) hljs.highlightAll();
      } catch (e) {
        /* ignore */
      }
    },
    // used to initialize raw stream text (unparsed)
    setRaw(text) {
      buffer = text || "";
      contentDiv.textContent = buffer;
    },
    // append raw chunk during fake streaming
    appendRaw(chunk) {
      buffer += chunk;
      contentDiv.textContent = buffer;
    },
    // getter for buffer (keeps backwards compatibility)
    getText() {
      return buffer;
    },
    // finalize streaming: parse markdown & highlight
    finish() {
      typingIndicator.style.display = "none";
      contentDiv.innerHTML = marked.parse(buffer);
      try {
        if (window.hljs) hljs.highlightAll();
      } catch (e) {
        /* ignore */
      }
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
//***************************************************************** */
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
//***************************************************************** */
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

//***************************************************************** */
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
//***************************************************************** */
async function resendMessage(text) {
  // Render the user bubble again (optional: could highlight instead of duplicating)
  createBubble("user", text);

  // Prepare bot bubble for streaming
  const streamBubble = createStreamedBubble("bot");
  chatBox.appendChild(streamBubble.wrapper);
  scrollToBottom();

  try {
    const model = document.getElementById("model-select").value;
    const token = localStorage.getItem("token");

    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch("http://localhost:2000/chat", {
      method: "POST",
      headers,
      body: JSON.stringify({
        session_id: currentSessionId,
        messages: [{ role: "user", content: text }],
        model: model,
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
    // 🧠 Update streamed bot response
    // 🎯 Instead of instantly updating, fake stream it
    fakeStreamText(data.response, streamBubble, 3);
    scrollToBottom();
  } catch (err) {
    if (streamBubble?.wrapper?.parentNode) {
      streamBubble.wrapper.remove();
    }
    createBubble("bot", `❌ Error: ${err.message}`);
    console.error("Resend error:", err);
  }
}
