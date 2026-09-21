const apiUrl = document.getElementById("apiUrl");
const bearerToken = document.getElementById("bearerToken");
const status = document.getElementById("status");

chrome.storage.local.get(["apiUrl", "bearerToken"]).then((stored) => {
  apiUrl.value = stored.apiUrl || "http://localhost:8000";
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
