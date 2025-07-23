document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("query-form");
  const input = document.getElementById("query-input");
  const responseContainer = document.getElementById("response-container");
  const responseText = document.getElementById("response-text");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const userQuery = input.value.trim();

    if (!userQuery) return;

    try {
      const rawPrice = "2000.0 (assuming iPhones are less than $2000)";
      const cleaned = parseFloat(rawPrice); // ✅ 2000.0
      const res = await fetch("http://localhost:8082/api/query/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ question: userQuery })
      });

      const data = await res.json();

      responseText.textContent = data.answer || "No answer returned.";
      responseContainer.classList.remove("hidden");
    } catch (err) {
      console.error("Error fetching response:", err);
      responseText.textContent = "Error: Could not get response from backend.";
      responseContainer.classList.remove("hidden");
    }
  });
});
 
