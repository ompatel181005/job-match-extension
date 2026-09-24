(() => {
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
    {
      source: "ashby",
      hosts: new Set(["jobs.ashbyhq.com"]),
      title: ["h1"],
      company: ["header img", "header a", "[class*='company']"],
      description: ["main", "[role='main']"],
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

  function textFromHtml(value) {
    const container = document.createElement("div");
    container.innerHTML = value || "";
    return container.textContent?.trim() || "";
  }

  function findJobPosting(value) {
    if (!value || typeof value !== "object") return null;
    const types = Array.isArray(value["@type"]) ? value["@type"] : [value["@type"]];
    if (types.includes("JobPosting")) return value;
    const nested = value["@graph"];
    if (Array.isArray(nested)) {
      return nested.map(findJobPosting).find(Boolean) || null;
    }
    return null;
  }

  function structuredJob() {
    for (const script of document.querySelectorAll("script[type='application/ld+json']")) {
      try {
        const posting = findJobPosting(JSON.parse(script.textContent || "null"));
        const text = textFromHtml(posting?.description);
        if (text.length < 100) continue;
        return {
          source: location.hostname === "jobs.ashbyhq.com" ? "ashby" : "structured-data",
          source_url: location.href,
          title: posting.title || document.title,
          company: posting.hiringOrganization?.name || "",
          text,
        };
      } catch {
        // Ignore malformed structured data and continue to visible-page extraction.
      }
    }
    return null;
  }

  function extractJob() {
    const structured = structuredJob();
    if (structured) return structured;

    const adapter = SITE_ADAPTERS.find((candidate) => candidate.hosts.has(location.hostname));
    const source = adapter?.source || "generic";
    const titleSelectors = adapter?.title || ["h1", "main h2", "[role='main'] h2"];
    const companySelectors = adapter?.company || [
      "[data-company-name]",
      ".company-name",
      "[class*='company']",
    ];
    const descriptionSelectors = adapter?.description || [
      "[data-job-description]",
      "[class*='job-description']",
      "main",
      "[role='main']",
      "article",
    ];
    const text = firstText(descriptionSelectors);
    if (text.length < 100) {
      throw new Error("The job description could not be read from this page.");
    }
    return {
      source,
      source_url: location.href,
      title: firstText(titleSelectors) || document.title,
      company: firstText(companySelectors),
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
})();
