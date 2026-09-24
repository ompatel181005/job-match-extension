const captureButton = document.getElementById("capture");
const pasteButton = document.getElementById("analyzePaste");
const jobText = document.getElementById("jobText");
const status = document.getElementById("status");
const results = document.getElementById("results");
const matchList = document.getElementById("matches");
const matchCount = document.getElementById("matchCount");
const requirementList = document.getElementById("requirements");
const count = document.getElementById("count");

function setBusy(busy, message = "") {
  captureButton.disabled = busy;
  pasteButton.disabled = busy;
  status.textContent = message;
}

function render(response) {
  const requirements = response.analysis.extraction.requirements;
  const matches = response.analysis.ranking.matches;
  requirementList.replaceChildren();
  matchList.replaceChildren();
  for (const match of matches) {
    const item = document.createElement("li");
    const heading = document.createElement("strong");
    heading.textContent = match.resume_name;
    const score = document.createElement("span");
    score.className = "score";
    score.textContent = `${match.score}%`;
    const summary = document.createElement("p");
    const gapCount = match.missing_requirement_ids.length;
    summary.textContent = gapCount
      ? `${gapCount} requirements missing`
      : "No detected gaps";
    item.append(heading, score, summary);
    matchList.append(item);
  }
  for (const requirement of requirements) {
    const item = document.createElement("li");
    const heading = document.createElement("strong");
    heading.textContent = requirement.keywords.join(", ");
    const metadata = document.createElement("span");
    metadata.className = `priority ${requirement.priority}`;
    metadata.textContent = `${requirement.priority} · weight ${requirement.weight}`;
    const source = document.createElement("p");
    source.textContent = requirement.text;
    item.append(heading, metadata, source);
    requirementList.append(item);
  }
  matchCount.textContent = String(matches.length);
  count.textContent = String(requirements.length);
  results.hidden = false;
  const warning = response.analysis.extraction.warnings?.[0];
  const close = response.analysis.ranking.close_match;
  status.textContent =
    warning ||
    (close
      ? "The top resume bases are close; compare their evidence before choosing."
      : `Ranked ${matches.length} resume bases against ${requirements.length} requirements.`);
}

async function send(type, text = null) {
  setBusy(true, "Reading requirements…");
  results.hidden = true;
  try {
    const response = await chrome.runtime.sendMessage({ type, text });
    if (!response?.ok) throw new Error(response?.error || "Analysis failed.");
    render(response);
  } catch (error) {
    status.textContent = error.message;
  } finally {
    setBusy(false, status.textContent);
  }
}

captureButton.addEventListener("click", () => send("EXTRACT_ACTIVE_JOB"));
pasteButton.addEventListener("click", () => {
  const text = jobText.value.trim();
  if (text.length < 50) {
    status.textContent = "Paste at least 50 characters from the job description.";
    return;
  }
  send("EXTRACT_PASTED_JOB", text);
});
