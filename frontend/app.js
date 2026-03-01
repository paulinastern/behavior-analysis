const analyzeBtn = document.getElementById("analyzeBtn");
const input = document.getElementById("analysisInput");
const output = document.getElementById("analysisOutput");

analyzeBtn.onclick = async () => {
  output.textContent = "Analyzing...";

  const res = await fetch("http://localhost:8000/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: input.value })
  });

  const data = await res.json();
  output.textContent = data.analysis || "Error.";
};