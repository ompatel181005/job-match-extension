const DEFAULT_API_URL = "http://localhost:8005";

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(console.error);

async function configuration() {
  const stored = await chrome.storage.local.get(["apiUrl", "bearerToken"]);
  const savedUrl = (stored.apiUrl || "").replace(/\/$/, "");
  if (["http://localhost:8000", "http://127.0.0.1:8000"].includes(savedUrl)) {
    stored.apiUrl = DEFAULT_API_URL;
    await chrome.storage.local.set({ apiUrl: DEFAULT_API_URL });
  }
  return {
    apiUrl: (stored.apiUrl || DEFAULT_API_URL).replace(/\/$/, ""),
    bearerToken: stored.bearerToken || "",
  };
}

async function callApi(path, payload) {
  const { apiUrl, bearerToken } = await configuration();
  const headers = { "Content-Type": "application/json" };
  if (bearerToken) headers.Authorization = `Bearer ${bearerToken}`;
  let response;
  try {
    response = await fetch(`${apiUrl}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error(`Cannot reach the backend at ${apiUrl}. Confirm it is running.`);
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Backend returned ${response.status}: ${detail.slice(0, 200)}`);
  }
  return response.json();
}

async function activeJob() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active job tab was found.");
  let response;
  try {
    response = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_JOB_PAGE" });
  } catch {
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ["content-script.js"],
      });
      response = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_JOB_PAGE" });
    } catch {
      throw new Error(
        "Chrome cannot read this page. Refresh a normal job page and try again, or paste the description.",
      );
    }
  }
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
