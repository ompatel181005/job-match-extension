const apiUrl = document.getElementById("apiUrl");
const bearerToken = document.getElementById("bearerToken");
const status = document.getElementById("status");

chrome.storage.local.get(["apiUrl", "bearerToken"]).then((stored) => {
  const savedUrl = (stored.apiUrl || "").replace(/\/$/, "");
  apiUrl.value = !savedUrl || ["http://localhost:8000", "http://127.0.0.1:8000"].includes(savedUrl)
    ? "http://localhost:8005"
    : savedUrl;
  bearerToken.value = stored.bearerToken || "";
});

document.getElementById("save").addEventListener("click", async () => {
  const normalizedUrl = apiUrl.value.trim().replace(/\/$/, "");
  if (!/^https?:\/\//.test(normalizedUrl)) {
    status.textContent = "Enter a complete HTTP or HTTPS URL.";
    return;
  }
  await chrome.storage.local.set({ apiUrl: normalizedUrl, bearerToken: bearerToken.value });
  status.textContent = "Settings saved.";
});
