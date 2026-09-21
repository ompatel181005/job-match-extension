const SITE_ADAPTERS = [
  {
    source: "greenhouse",
    hosts: new Set(["boards.greenhouse.io", "job-boards.greenhouse.io"]),
    title: ["h1", ".app-title"],
    company: ["[data-mapped='companyName']", ".company-name"],
    description: ["#content", "#job_description", ".job__description"],
  },
  {
    source: "lever",
    hosts: new Set(["jobs.lever.co"]),
    title: ["h2", ".posting-headline h2"],
    company: [".main-header-logo img", ".posting-categories"],
    description: [".posting-page", ".posting"],
  },
];

function firstText(selectors) {
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    const value = element?.getAttribute("alt") || element?.textContent;
    if (value?.trim()) return value.trim();
  }
  return "";
}

function extractJob() {
  const adapter = SITE_ADAPTERS.find((candidate) => candidate.hosts.has(location.hostname));
  if (!adapter) throw new Error("This site is not supported yet. Paste the job description instead.");
  const text = firstText(adapter.description);
  if (text.length < 100) throw new Error("The job description could not be read from this page.");
  return {
    source: adapter.source,
    source_url: location.href,
    title: firstText(adapter.title) || document.title,
    company: firstText(adapter.company),
    text,
  };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== "EXTRACT_JOB_PAGE") return false;
  try {
    sendResponse({ ok: true, job: extractJob() });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
  return false;
});
