const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const chatBox = document.getElementById("chat-box");

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

    const headers = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch("http://localhost:2521/chat", {
      method: "POST",
      headers,
      body: JSON.stringify({
        messages: [{ role: "user", content: text }],
        model: model,
      }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assembledResponse = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const parts = chunk.split("data:");

      for (let i = 1; i < parts.length; i++) {
        const token = parts[i].trim();
        if (!token || token === "[DONE]") continue;

        let content = "";

        try {
          const parsed = JSON.parse(token);
          content = parsed.choices?.[0]?.delta?.content || "";
        } catch (err) {
          content = token;
        }

        const prevChar = assembledResponse.slice(-1);
        const nextChar = content.charAt(0);

        const needsSpace =
          assembledResponse.length &&
          ![" ", "\n"].includes(prevChar) &&
          ![".", ",", "!", "?", ":", ";", "'"].includes(nextChar);

        if (needsSpace) {
          assembledResponse += " ";
        }

        assembledResponse += content;

        streamBubble.update(assembledResponse);
        scrollToBottom();
      }
    }
  } catch (err) {
    createBubble("bot", `❌ Error: ${err.message}`);
    console.error("Streaming error:", err);
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
const API_BASE = "http://localhost:2521"; // Adjust to your backend

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

  // Hide login button
  document.getElementById("login-btn").classList.add("hidden");

  // Show profile
  document.getElementById("profile-menu").classList.remove("hidden");
  document.getElementById("profile-email").innerText = user.email;

  // Toggle dropdown
  const profileBtn = document.getElementById("profile-btn");
  const dropdown = document.getElementById("profile-dropdown");
  profileBtn.onclick = () => dropdown.classList.toggle("hidden");
}

function logout() {
  localStorage.removeItem("token");
  location.reload();
}

// Initialize on load
window.addEventListener("DOMContentLoaded", loadProfile);
