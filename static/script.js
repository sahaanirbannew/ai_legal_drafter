let pipelineCancelled = false
let currentCaseId = null
let analysisReady = false
let validationReady = false
let currentCaseState = null
let citations = []
let reviewerComments = []
let selectedText = ""
let activeCitationIndex = null
let finalizeInProgress = false
let sidebarCollapsed = false

function setUploadButtonEnabled(enabled) {
    document.getElementById("uploadBtn").disabled = !enabled
}

function setStrategiseEnabled(enabled) {
    analysisReady = enabled
    document.getElementById("strategiseBtn").disabled = !enabled
}

function setDownloadEnabled(enabled) {
    document.getElementById("downloadBtn").disabled = !enabled || finalizeInProgress
}

function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed
    document.querySelector(".side-panel").classList.toggle("collapsed", sidebarCollapsed)
}

function showSpinner(active) {
    let spinner = document.getElementById("spinner")
    if (!spinner) return
    spinner.classList.toggle("hidden", !active)
}

function updateStatus(message) {
    let status = document.getElementById("status")
    if (status) status.innerText = message
}

function appendLog(message) {
    let log = document.getElementById("log")
    if (!log) return

    let item = document.createElement("li")
    let ts = new Date().toLocaleString()
    item.innerHTML = `<span class="log-time">${ts}</span><span class="log-level">agent call</span>${escapeHtml(message)}`
    log.appendChild(item)
    log.scrollTop = log.scrollHeight
}

function setAgentCalls(calls) {
    if (!calls || calls.length === 0) return
    calls.forEach((call) => appendLog(call))
}

function appendDownloadLog(message) {
    let log = document.getElementById("downloadLog")
    if (!log) return
    if (log.children.length === 1 && log.children[0].innerText === "No download activity yet.") {
        log.innerHTML = ""
    }
    let item = document.createElement("li")
    item.innerText = `${new Date().toLocaleTimeString()}: ${message}`
    log.appendChild(item)
    log.scrollTop = log.scrollHeight
}

function buildValidationSummary(validationData) {
    let issues = (validationData.issues_found || []).map(item => `- ${item}`).join("\n") || "- None reported"
    let improvements = (validationData.suggested_improvements || []).map(item => `- ${item}`).join("\n") || "- None reported"
    let summary =
        `Overall validity: ${validationData.overall_validity_score ?? "N/A"}/10\n` +
        `Logic: ${validationData.logic_score ?? "N/A"}/10\n` +
        `Citations: ${validationData.citation_validity_score ?? "N/A"}/10\n\n`

    if (validationData.validation_failed) {
        summary += `Validation status: Failed\n`
        summary += `Reason: ${validationData.failure_reason || "Unknown validation failure."}\n\n`
    }

    summary +=
        `Issues:\n${issues}\n\n` +
        `Suggested improvements:\n${improvements}`

    if (validationData.raw_text) {
        summary += `\n\nRaw validator response:\n${validationData.raw_text}`
    }

    return summary
}

function setDownloadProgress(value, message) {
    let bar = document.getElementById("downloadProgressBar")
    let label = document.getElementById("downloadProgressLabel")
    if (bar) bar.style.width = `${Math.max(0, Math.min(100, value))}%`
    if (label) label.innerText = message
}

function getFilenameFromContentDisposition(headerValue, fallbackName) {
    if (!headerValue) return fallbackName

    let utf8Match = headerValue.match(/filename\*\s*=\s*UTF-8''([^;]+)/i)
    if (utf8Match && utf8Match[1]) {
        try {
            return decodeURIComponent(utf8Match[1]).replace(/^["']|["']$/g, "")
        } catch (_) {
        }
    }

    let quotedMatch = headerValue.match(/filename\s*=\s*"([^"]+)"/i)
    if (quotedMatch && quotedMatch[1]) {
        return quotedMatch[1].trim()
    }

    let plainMatch = headerValue.match(/filename\s*=\s*([^;]+)/i)
    if (plainMatch && plainMatch[1]) {
        return plainMatch[1].trim().replace(/^["']|["']$/g, "")
    }

    return fallbackName
}

function sanitizeDownloadFilename(filename, fallbackName) {
    let cleaned = String(filename || fallbackName)
        .replace(/[<>:"/\\|?*\u0000-\u001F]/g, "_")
        .trim()

    cleaned = cleaned.replace(/[._\s]+$/, "")
    if (!cleaned.toLowerCase().endsWith(".pdf")) {
        cleaned = `${cleaned}.pdf`
    }
    return cleaned || fallbackName
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;")
}

function resetPipelineState() {
    pipelineCancelled = false
    analysisReady = false
    validationReady = false
    currentCaseState = null
    citations = []
    reviewerComments = []
    selectedText = ""
    activeCitationIndex = null
    setStrategiseEnabled(false)
    setDownloadEnabled(false)
    document.getElementById("argumentEditor").innerHTML = ""
    document.getElementById("selectedExcerpt").innerText = "No text selected."
    document.getElementById("commentInput").value = ""
    document.getElementById("commentList").innerHTML = `<div class="muted-note">No comments added yet.</div>`
    document.getElementById("citationDetails").innerText = "Click a citation inside the argument to view its details here."
    document.getElementById("validationSummary").innerText = "No validation result yet."
    document.getElementById("argumentDifferenceSummary").innerText = "No comparison available yet."
    document.getElementById("caseSummary").innerText = "Applicant: Not yet extracted.\nDefendant: Not yet extracted.\nCharges: Not yet extracted.\nDemands: Not yet extracted.\n\nExisting argument provided: Pending analysis."
    document.getElementById("downloadLog").innerHTML = "<li>No download activity yet.</li>"
    setDownloadProgress(0, "Waiting to finalise.")
    appendLog("Pipeline state reset for a fresh upload.")
}

function cancelPipeline() {
    pipelineCancelled = true
    setUploadButtonEnabled(true)
    showSpinner(false)
    updateStatus("Pipeline cancelled.")
    appendLog("Pipeline cancellation requested by user.")
}

function showArgumentScreen() {
    if (!analysisReady) return
    document.getElementById("uploadScreen").classList.add("hidden")
    document.getElementById("argumentScreen").classList.remove("hidden")
    appendLog("Review workspace opened.")
}

function showUploadScreen() {
    document.getElementById("argumentScreen").classList.add("hidden")
    document.getElementById("uploadScreen").classList.remove("hidden")
    appendLog("Returned to upload screen.")
}

function applyEditorCommand(command, value = null) {
    document.execCommand(command, false, value)
    document.getElementById("argumentEditor").focus()
}

function normaliseText(text) {
    return String(text || "").replace(/\s+/g, " ").trim()
}

function captureSelection() {
    let selection = window.getSelection()
    if (!selection || selection.rangeCount === 0) {
        selectedText = ""
    } else {
        let range = selection.getRangeAt(0)
        let editor = document.getElementById("argumentEditor")
        if (!editor.contains(range.commonAncestorContainer)) {
            selectedText = ""
        } else {
            selectedText = normaliseText(selection.toString())
        }
    }
    document.getElementById("selectedExcerpt").innerText = selectedText || "No text selected."
}

function addComment() {
    let input = document.getElementById("commentInput")
    let note = normaliseText(input.value)
    if (!selectedText) {
        alert("Select a section of the draft first.")
        return
    }
    if (!note) {
        alert("Write a comment before adding it.")
        return
    }

    reviewerComments.push({
        selected_text: selectedText,
        comment: note,
        created_at: new Date().toISOString(),
    })
    appendLog(`Comment added for selected text: ${selectedText.slice(0, 80)}.`)
    input.value = ""
    selectedText = ""
    document.getElementById("selectedExcerpt").innerText = "No text selected."
    renderCommentList()
}

function renderCommentList() {
    let container = document.getElementById("commentList")
    if (reviewerComments.length === 0) {
        container.innerHTML = `<div class="muted-note">No comments added yet.</div>`
        return
    }

    container.innerHTML = ""
    reviewerComments.forEach((item, index) => {
        let block = document.createElement("div")
        block.className = "comment-item"
        block.innerHTML = `
            <strong>Comment ${index + 1}</strong>
            <div><em>Selected text:</em> ${escapeHtml(item.selected_text)}</div>
            <div style="margin-top:6px;">${escapeHtml(item.comment)}</div>
        `
        container.appendChild(block)
    })
}

function renderArgumentDifferences(points) {
    let container = document.getElementById("argumentDifferenceSummary")
    if (!container) return
    let items = Array.isArray(points) ? points.filter(Boolean) : []
    if (!items.length) {
        container.innerText = "No comparison available yet."
        return
    }
    container.innerText = items.map(item => `- ${item}`).join("\n")
}

function buildCitationLinkButton(label, url) {
    if (!url) return ""
    return `<a class="citation-link-button" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`
}

function renderCaseSummary(analysis, draftText) {
    let demands = (analysis.demands || []).length ? analysis.demands.join("; ") : "Not extracted."
    let charges = Array.isArray(analysis.charges) && analysis.charges.length
        ? analysis.charges.join("; ")
        : "Not extracted."
    let snapshot =
        `Applicant: ${analysis.applicant || "Not extracted."}\n` +
        `Defendant: ${analysis.defendant || "Not extracted."}\n` +
        `Charges: ${charges}\n` +
        `Demands: ${demands}\n\n` +
        `Existing argument provided:\n${draftText || "Pending analysis."}`
    document.getElementById("caseSummary").innerText = snapshot
}

function buildCitationToken(index, citation) {
    return `<span class="citation-ref" data-citation-index="${index}" title="Open citation details">[${index + 1}] ${escapeHtml(citation.case_name)}</span>`
}

function renderEditor(text, citationData) {
    let paragraphs = String(text || "")
        .split(/\n{2,}/)
        .map(part => part.trim())
        .filter(Boolean)
        .map(part => `<p>${escapeHtml(part).replace(/\n/g, "<br />")}</p>`)

    if (citationData.length) {
        let authorityLine = citationData.map((citation, index) => buildCitationToken(index, citation)).join(" ")
        paragraphs.push(`<p><strong>Authorities relied upon:</strong> ${authorityLine}</p>`)
    }

    document.getElementById("argumentEditor").innerHTML = paragraphs.join("")
    bindCitationClicks()
}

function bindCitationClicks() {
    document.querySelectorAll(".citation-ref").forEach((element) => {
        element.addEventListener("click", () => {
            let index = Number(element.dataset.citationIndex)
            showCitationDetails(index)
        })
    })
}

function showCitationDetails(index) {
    activeCitationIndex = index
    document.querySelectorAll(".citation-ref").forEach((node) => {
        node.classList.toggle("active", Number(node.dataset.citationIndex) === index)
    })

    let citation = citations[index]
    if (!citation) return
    let validation = citation.llm_link_validation || {}
    let validationText = `SC: ${validation.is_SupremeCourt ? "true" : "false"}, HC: ${validation.is_HighCourt ? "true" : "false"}, PDF: ${validation.is_PDF ? "true" : "false"}, Correct: ${validation.is_Correct ? "true" : "false"}, Accessible: ${validation.is_accessible ? "true" : "false"}`
    let validLinks = []
    if (validation.is_Correct && validation.is_accessible) {
        if (validation.indian_court_link) {
            validLinks.push(buildCitationLinkButton("Open IndianCourt Link", validation.indian_court_link))
        }
        if (validation.indian_kanoon_link) {
            validLinks.push(buildCitationLinkButton("Open IndianKanoon Link", validation.indian_kanoon_link))
        }
        if (citation.link && !validLinks.length) {
            validLinks.push(buildCitationLinkButton("Open Selected Citation Link", citation.link))
        }
    }

    let html =
        `<strong>${escapeHtml(citation.case_name)}</strong>` +
        `<div><em>Court:</em> ${escapeHtml(citation.court || "Unknown")}</div>` +
        `<div style="margin-top:8px;"><em>Description:</em> ${escapeHtml(citation.description || "No description")}</div>` +
        `<div style="margin-top:8px;"><em>Why cited:</em> ${escapeHtml(citation.why_cited || "No reason provided")}</div>` +
        `<div style="margin-top:8px;"><em>Relevance:</em> ${escapeHtml(String(citation.relevance_score ?? "N/A"))}</div>` +
        `<div><em>Strength:</em> ${escapeHtml(String(citation.strength_score ?? "N/A"))}</div>` +
        `<div><em>Link validation:</em> ${citation.link_verified ? "Validated LLM link" : "No validated link"}</div>` +
        `<div style="margin-top:8px;"><em>LLM validation flags:</em> ${escapeHtml(validationText)}</div>` +
        `<div style="margin-top:8px;"><em>Validated link buttons:</em> ${validLinks.length ? validLinks.join(" ") : "No validated accessible links"}</div>` +
        `<div style="margin-top:8px;"><em>IndianCourt candidate:</em> ${validation.indian_court_link ? `<a href="${escapeHtml(validation.indian_court_link)}" target="_blank" rel="noreferrer">${escapeHtml(validation.indian_court_link)}</a>` : "No link provided"}</div>` +
        `<div style="margin-top:8px;"><em>IndianKanoon candidate:</em> ${validation.indian_kanoon_link ? `<a href="${escapeHtml(validation.indian_kanoon_link)}" target="_blank" rel="noreferrer">${escapeHtml(validation.indian_kanoon_link)}</a>` : "No link provided"}</div>` +
        `<div style="margin-top:8px;"><em>LLM reason:</em> ${escapeHtml(validation.reason || "No reason provided.")}</div>` +
        `<div style="margin-top:8px;"><em>Link note:</em> ${escapeHtml(citation.link_note || "No additional note.")}</div>` +
        `<div style="margin-top:8px;"><em>LLM input prompt:</em><pre class="llm-response-box">${escapeHtml(citation.llm_link_prompt || "No LLM prompt captured.")}</pre></div>` +
        `<div style="margin-top:8px;"><em>LLM returned citation link:</em> ${citation.link ? `<a href="${escapeHtml(citation.link)}" target="_blank" rel="noreferrer">${escapeHtml(citation.link)}</a>` : "No link provided"}</div>` +
        `<div style="margin-top:8px;"><em>LLM raw response:</em><pre class="llm-response-box">${escapeHtml(citation.llm_link_response || "No LLM response captured.")}</pre></div>`
    document.getElementById("citationDetails").innerHTML = html
}

async function fetchCaseState() {
    if (!currentCaseId) return null
    let response = await fetch(`/cases/${currentCaseId}`)
    let data = await response.json()
    if (!response.ok || data.status === "error") {
        throw new Error(data.message || "Failed to fetch case state")
    }
    currentCaseState = data
    return data
}

async function upload() {
    resetPipelineState()
    showSpinner(true)
    updateStatus("Upload started.")
    setAgentCalls(["IntakeAgent: saving uploaded PDF", "Gemini workflow: preparing document for analysis"])
    appendLog("Upload began. Preparing selected PDF for ingestion.")
    setUploadButtonEnabled(false)

    try {
        let file = document.getElementById("file").files[0]
        if (!file) throw new Error("No file selected")

        appendLog(`Selected file: ${file.name} (${Math.round(file.size / 1024)} KB).`)
        let form = new FormData()
        form.append("file", file)

        let response = await fetch("/upload", { method: "POST", body: form })
        let result = await response.json()
        if (!response.ok || result.status === "error") {
            throw new Error(result.message || "Upload failed")
        }

        currentCaseId = result.case_id
        appendLog(`Upload completed. Assigned case id ${currentCaseId}.`)
        updateStatus("Upload completed. Analysis is starting.")
        setAgentCalls(["CaseAnalysisAgent: extracting structured case data", "DraftingAgent: building initial argument"])

        let genResult = await generate()
        if (!genResult.success || pipelineCancelled) {
            appendLog("Upload flow stopped before analysis could complete.")
            return { success: false }
        }

        appendLog("Case processed successfully. Strategise is now available.")
        updateStatus("File uploaded and processed. Open Strategise to review the argument.")
        setStrategiseEnabled(true)
        setDownloadEnabled(true)
        showArgumentScreen()
        setAgentCalls(["ValidationAgent: sending draft to Gemini", "RevisionAgent: waiting for validation result"])

        let valResult = await validate()
        if (!valResult.success || pipelineCancelled) {
            appendLog("Validation did not complete after analysis.")
            return { success: false }
        }

        validationReady = true
        setDownloadEnabled(true)
        setAgentCalls(["Review workspace: user edits/comments", "OutputAgent: final PDF generation available"])
        appendLog("Validation completed. Review the argument, add comments, then finalize and download.")
        updateStatus("Validation complete. Review, edit, comment, and download the final version.")
        return { success: true }
    } catch (err) {
        updateStatus("Upload failed.")
        appendLog(`Upload flow failed: ${err.message}`)
        alert("Upload failed: " + err.message)
        return { success: false }
    } finally {
        showSpinner(false)
        setUploadButtonEnabled(true)
    }
}

async function generate() {
    updateStatus("Analysis in progress.")
    setAgentCalls(["CaseAnalysisAgent: extracting applicant, defendant, charges, demands", "Citation resolver: refining citation links", "DraftingAgent: building draft"])
    appendLog("Analysis agent started. Extracting demands, arguments, and citations.")

    try {
        if (!currentCaseId) throw new Error("No active case. Upload a PDF first.")

        let res = await fetch("/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ case_id: currentCaseId })
        })
        let data = await res.json()
        if (!res.ok || data.status === "error") {
            throw new Error(data.message || "Analysis failed")
        }

        appendLog("Analysis completed successfully. Draft argument received from backend.")
        appendLog(`Citation count returned: ${data.citations.length}.`)
        citations = data.citations || []

        let caseState = await fetchCaseState()
        if (!caseState || !caseState.analysis) {
            throw new Error("Structured case analysis was not available.")
        }

        let analysis = caseState.analysis
        let hasRequiredExtraction =
            normaliseText(analysis.applicant).length > 0 &&
            normaliseText(analysis.defendant).length > 0 &&
            Array.isArray(analysis.charges) && analysis.charges.length > 0 &&
            Array.isArray(analysis.demands) && analysis.demands.length > 0

        if (!hasRequiredExtraction) {
            throw new Error("Required case details were not fully extracted.")
        }

        let draftText = (caseState && caseState.draft_text) || data.text || ""
        renderEditor(draftText, citations)
        renderCaseSummary(analysis, draftText)
        renderArgumentDifferences(caseState.argument_difference_points || [])

        return { success: true }
    } catch (err) {
        updateStatus("Analysis failed.")
        appendLog(`Analysis failed: ${err.message}`)
        alert("Generation failed: " + err.message)
        return { success: false }
    }
}

async function validate() {
    updateStatus("Validation in progress.")
    setAgentCalls(["ValidationAgent: Gemini review in progress", "RevisionAgent: revision pending validation output"])
    appendLog("Validation agent started. Polling backend for detailed review.")

    try {
        if (!currentCaseId) throw new Error("No active case. Upload a PDF first.")

        let startRes = await fetch("/validate/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ case_id: currentCaseId })
        })
        let startData = await startRes.json()
        if (!startRes.ok || startData.status === "error") {
            throw new Error(startData.message || "Failed to start validation")
        }

        let taskId = startData.task_id
        appendLog(`Validation task created: ${taskId}.`)

        return new Promise((resolve) => {
            let pollInterval = setInterval(async () => {
                try {
                    let statusRes = await fetch(`/validate/status/${taskId}`)
                    let statusData = await statusRes.json()

                    if (pipelineCancelled) {
                        clearInterval(pollInterval)
                        updateStatus("Validation cancelled.")
                        appendLog("Validation polling stopped because the pipeline was cancelled.")
                        resolve({ success: false })
                        return
                    }

                    if (statusData.status === "pending") {
                        appendLog("Validation still running. Awaiting Gemini review output.")
                        return
                    }

                    clearInterval(pollInterval)
                    let validationData = typeof statusData.result === "string" ? JSON.parse(statusData.result) : statusData.result
                    if (statusData.status === "error" && !validationData) {
                        throw new Error(statusData.error || "Validation failed")
                    }

                    validationData = validationData || {
                        validation_failed: true,
                        failure_reason: statusData.error || "Validation failed",
                        overall_validity_score: null,
                        logic_score: null,
                        citation_validity_score: null,
                        issues_found: [statusData.error || "Validation failed"],
                        suggested_improvements: ["Retry validation."],
                        hallucinated_citations: [],
                    }
                    let summary = buildValidationSummary(validationData)

                    document.getElementById("validationSummary").innerText = summary
                    setAgentCalls(["RevisionAgent: revised draft ready", "Review workspace: user can finalise and download"])
                    appendLog(statusData.status === "error"
                        ? "Validation failed, but a fallback summary was rendered in the UI."
                        : "Validation completed and the summary panel was updated.")
                    appendLog(`Validation scores: overall ${validationData.overall_validity_score ?? "N/A"}, logic ${validationData.logic_score ?? "N/A"}, citations ${validationData.citation_validity_score ?? "N/A"}.`)
                    updateStatus(statusData.status === "error" ? "Validation failed with fallback summary." : "Validation completed.")
                    resolve({ success: statusData.status !== "error" })
                } catch (pollErr) {
                    clearInterval(pollInterval)
                    updateStatus("Validation failed.")
                    document.getElementById("validationSummary").innerText = buildValidationSummary({
                        validation_failed: true,
                        failure_reason: pollErr.message,
                        overall_validity_score: null,
                        logic_score: null,
                        citation_validity_score: null,
                        issues_found: [pollErr.message],
                        suggested_improvements: [
                            "Retry validation after checking Gemini API access, model configuration, and PDF readability."
                        ],
                        hallucinated_citations: [],
                    })
                    appendLog(`Validation polling failed: ${pollErr.message}`)
                    alert("Validation failed: " + pollErr.message)
                    resolve({ success: false })
                }
            }, 2000)
        })
    } catch (err) {
        updateStatus("Validation failed.")
        document.getElementById("validationSummary").innerText = buildValidationSummary({
            validation_failed: true,
            failure_reason: err.message,
            overall_validity_score: null,
            logic_score: null,
            citation_validity_score: null,
            issues_found: [err.message],
            suggested_improvements: [
                "Retry validation after checking Gemini API access, model configuration, and PDF readability."
            ],
            hallucinated_citations: [],
        })
        appendLog(`Validation start failed: ${err.message}`)
        alert("Validation failed: " + err.message)
        return { success: false }
    }
}

async function finalizeAndDownload() {
    updateStatus("Finalizing argument and generating PDF.")
    setAgentCalls(["FinalizationService: incorporating edits/comments", "OutputAgent: generating final PDF"])
    appendLog("Finalization requested. Sending edited draft and reviewer comments to backend.")
    finalizeInProgress = true
    setDownloadEnabled(false)
    setDownloadProgress(8, "Preparing edited draft for finalisation.")
    appendDownloadLog("Collected the latest editor content.")

    try {
        if (!currentCaseId) throw new Error("No active case. Upload a PDF first.")

        let editedText = normaliseEditorText()
        if (!editedText) throw new Error("The proposed argument is empty.")
        setDownloadProgress(20, "Submitting edited draft and reviewer comments.")
        appendDownloadLog(`Submitting ${reviewerComments.length} reviewer comment(s) to the backend.`)

        let res = await fetch("/finalize_pdf", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                case_id: currentCaseId,
                edited_text: editedText,
                comments: reviewerComments,
            })
        })
        setDownloadProgress(65, "Backend finalisation completed. Preparing PDF download.")
        appendDownloadLog("Backend returned the finalized file stream.")

        if (!res.ok) {
            let error = await res.json().catch(() => ({}))
            throw new Error(error.message || "Unknown finalization error")
        }

        let filename = "legal_argument_final.pdf"
        let contentDisposition = res.headers.get("content-disposition")
        filename = sanitizeDownloadFilename(
            getFilenameFromContentDisposition(contentDisposition, filename),
            filename
        )

        let blob = await res.blob()
        setDownloadProgress(82, "Creating browser download.")
        appendDownloadLog(`Resolved final filename: ${filename}.`)
        let url = URL.createObjectURL(blob)
        let a = document.createElement("a")
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        setDownloadProgress(100, "Finalised argument downloaded successfully.")
        appendDownloadLog("Download finished and the file was handed to the browser.")

        appendLog(`Finalized argument downloaded successfully: ${filename}.`)
        updateStatus(`Finalized PDF generated: ${filename}.`)
        return { success: true }
    } catch (err) {
        setDownloadProgress(100, "Finalisation failed.")
        appendDownloadLog(`Finalisation failed: ${err.message}`)
        updateStatus("Finalization failed.")
        appendLog(`Finalization failed: ${err.message}`)
        alert("Finalization failed: " + err.message)
        return { success: false }
    } finally {
        finalizeInProgress = false
        setDownloadEnabled(analysisReady)
    }
}

function normaliseEditorText() {
    let text = document.getElementById("argumentEditor").innerText || ""
    return text.replace(/\n{3,}/g, "\n\n").trim()
}
