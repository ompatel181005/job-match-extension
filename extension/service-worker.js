const DEFAULT_API_URL = "http://localhost:8000";

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(console.error);

async function configuration() {
  const stored = await chrome.storage.local.get(["apiUrl", "bearerToken"]);
  return {
    apiUrl: (stored.apiUrl || DEFAULT_API_URL).replace(/\/$/, ""),
    bearerToken: stored.bearerToken || "",
  };
}

async function callApi(path, payload) {
  const { apiUrl, bearerToken } = await configuration();
  const headers = { "Content-Type": "application/json" };
  if (bearerToken) headers.Authorization = `Bearer ${bearerToken}`;
  const response = await fetch(`${apiUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Backend returned ${response.status}: ${detail.slice(0, 200)}`);
  }
  return response.json();
}

async function activeJob() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active job tab was found.");
  const response = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_JOB_PAGE" });
  if (!response?.ok) throw new Error(response?.error || "The job page could not be read.");
  return response.job;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!["EXTRACT_ACTIVE_JOB", "EXTRACT_PASTED_JOB"].includes(message.type)) return false;
  (async () => {
    try {
      const job =
        message.type === "EXTRACT_ACTIVE_JOB"
          ? await activeJob()
          : { text: message.text, title: null, company: null, source_url: null };
      const analysis = await callApi("/v1/jobs/rank", job);
      sendResponse({ ok: true, job, analysis });
    } catch (error) {
      sendResponse({ ok: false, error: error.message });
    }
  })();
  return true;
});
