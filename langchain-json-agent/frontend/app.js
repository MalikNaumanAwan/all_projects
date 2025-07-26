document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("query-form");
  const input = document.getElementById("query-input");
  const chat = document.getElementById("chat-container");

  function addMessage(role, text) {
    const wrapper = document.createElement("div");
    wrapper.className = `flex ${
      role === "user" ? "justify-end" : "justify-start"
    }`;

    const bubble = document.createElement("div");
    bubble.className = `
      max-w-[75%] px-4 py-3 rounded-2xl shadow 
      ${
        role === "user"
          ? "bg-blue-600 text-white rounded-br-none"
          : "bg-gray-100 text-gray-800 rounded-bl-none"
      }
    `;
    bubble.textContent = text;

    wrapper.appendChild(bubble);
    chat.appendChild(wrapper);
    chat.scrollTop = chat.scrollHeight;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    addMessage("user", question);
    input.value = "";

    try {
      addMessage("agent", "Typing...");

      const res = await fetch("http://localhost:8081/api/query/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
      });

      const data = await res.json();
      const bubbles = chat.querySelectorAll("div.justify-start:last-child div");
      if (bubbles.length)
        bubbles[bubbles.length - 1].textContent =
          data.answer || "No response returned.";
    } catch (err) {
      console.error("Backend error:", err);
      const bubbles = chat.querySelectorAll("div.justify-start:last-child div");
      if (bubbles.length)
        bubbles[bubbles.length - 1].textContent =
          "❌ Failed to get response from backend.";
    }
  });
});
