console.log("✅ JS is loading");

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("match-form");
  const resumeInput = document.getElementById("resume");
  const jdInput = document.getElementById("jd");
  const resultDiv = document.getElementById("result");
  const scoreEl = document.getElementById("score");
  const reasoningEl = document.getElementById("reasoning");
  const spinner = document.getElementById("spinner");
  const canvas = document.getElementById("canvas");
  const chartCanvas = document.getElementById("scoreChart");

  let scoreChartInstance = null; // ✅ only once, at the top

  canvas.classList.add("hidden");

  console.log("🔧 DOMContentLoaded triggered");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    console.log("📤 Form submitted");

    // Reset UI
    canvas.classList.add("hidden");
    chartCanvas.classList.add("hidden");
    spinner.classList.remove("hidden");

    // Destroy existing chart
    if (scoreChartInstance) {
      scoreChartInstance.destroy();
      scoreChartInstance = null;
    }

    const resumeFile = resumeInput.files[0];
    const jdFile = jdInput.files[0];

    if (!resumeFile || !jdFile) {
      alert("⚠️ Please upload both files");
      return;
    }

    const formData = new FormData();
    formData.append("resume", resumeFile);
    formData.append("jd", jdFile);

    scoreEl.textContent = "⏳ Processing...";
    scoreEl.className = "";
    reasoningEl.textContent = "";
    resultDiv.classList.remove("hidden");

    try {
      const startTime = performance.now();
      console.log("🌍 Sending request to backend...");
      const response = await fetch("http://localhost:8082/match/", {
        method: "POST",
        body: formData,
      });

      console.log("📥 Raw response:", response);
      const data = await response.json();
      console.log("✅ Parsed JSON:", data);
      const endTime = performance.now();
      const responseTime = endTime - startTime;
      console.log(`✅ API response received in ${responseTime.toFixed(2)} ms`);
      if (!response.ok) {
        throw new Error(data.detail || "Server error");
      }

      if (typeof data.score === "undefined" || !data.reasoning) {
        console.warn("⚠️ Response missing expected fields", data);
        scoreEl.textContent = "❌ Unexpected response";
        reasoningEl.textContent = JSON.stringify(data, null, 2);
        reasoningEl.classList.add("text-red-600");
        return;
      }

      const score = parseInt(data.score);
      scoreEl.textContent = `✅ Match Score: ${score}%`;
      reasoningEl.textContent = data.reasoning;

      if (score >= 75) {
        scoreEl.classList.add("text-green-700");
      } else if (score >= 50) {
        scoreEl.classList.add("text-yellow-600");
      } else {
        scoreEl.classList.add("text-red-700");
      }

      spinner.classList.add("hidden");
      canvas.classList.remove("hidden");

      // ✅ Create Chart
      const ctx = chartCanvas.getContext('2d');
      scoreChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: ['Match ', 'Misalignment'],
          datasets: [{
            data: [score, 100 - score],
            backgroundColor: ['#4ade80', '#f87171'],
          }]
        },
        options: {
          cutout: '70%',
        }
      });

      chartCanvas.classList.remove("hidden");

    } catch (err) {
      console.error("❌ Fetch or parsing failed:", err);
      scoreEl.textContent = "Error:";
      reasoningEl.textContent = err.message;
      reasoningEl.classList.add("text-red-600");
    }
  });
});
