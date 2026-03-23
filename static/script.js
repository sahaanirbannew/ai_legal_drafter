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

function showSpinner(active) {
    let spinner = document.getElementById("spinner")
    if (!spinner) return
    spinner.classList.toggle("hidden", !active)
}

function updateStatus(message) {
    let status = document.getElementById("status")
    if (status) status.innerText = message
}

function appendLog(message, level = "Info") {
    let log = document.getElementById("log")
    if (!log) return

    let item = document.createElement("li")
    let ts = new Date().toLocaleString()
    let levelClass = level.toLowerCase()
    item.innerHTML = `<span class="log-time">${ts}</span><span class="log-level ${levelClass}">${level}</span>${escapeHtml(message)}`
    log.appendChild(item)
    log.scrollTop = log.scrollHeight
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
    document.getElementById("caseSummary").innerText = "Applicant: Not yet extracted.\nDefendant: Not yet extracted.\nCharges: Not yet extracted.\nDemands: Not yet extracted.\n\nExisting argument provided: Pending analysis."
    document.getElementById("downloadLog").innerHTML = "<li>No download activity yet.</li>"
    setDownloadProgress(0, "Waiting to finalise.")
    appendLog("Pipeline state reset for a fresh upload.", "Debug")
}

function cancelPipeline() {
    pipelineCancelled = true
    setUploadButtonEnabled(true)
    showSpinner(false)
    updateStatus("Pipeline cancelled.")
    appendLog("Pipeline cancellation requested by user.", "Info")
}

function showArgumentScreen() {
    if (!analysisReady) return
    document.getElementById("uploadScreen").classList.add("hidden")
    document.getElementById("argumentScreen").classList.remove("hidden")
    appendLog("Review workspace opened.", "Debug")
}

function showUploadScreen() {
    document.getElementById("argumentScreen").classList.add("hidden")
    document.getElementById("uploadScreen").classList.remove("hidden")
    appendLog("Returned to upload screen.", "Debug")
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
    appendLog(`Comment added for selected text: ${selectedText.slice(0, 80)}.`, "Info")
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

    let html =
        `<strong>${escapeHtml(citation.case_name)}</strong>` +
        `<div><em>Court:</em> ${escapeHtml(citation.court || "Unknown")}</div>` +
        `<div style="margin-top:8px;"><em>Description:</em> ${escapeHtml(citation.description || "No description")}</div>` +
        `<div style="margin-top:8px;"><em>Why cited:</em> ${escapeHtml(citation.why_cited || "No reason provided")}</div>` +
        `<div style="margin-top:8px;"><em>Relevance:</em> ${escapeHtml(String(citation.relevance_score ?? "N/A"))}</div>` +
        `<div><em>Strength:</em> ${escapeHtml(String(citation.strength_score ?? "N/A"))}</div>` +
        `<div><em>Link validation:</em> ${citation.link_verified ? "Verified direct link" : "Search-safe link"}</div>` +
        `<div style="margin-top:8px;"><em>Link note:</em> ${escapeHtml(citation.link_note || "No additional note.")}</div>` +
        `<div style="margin-top:8px;"><em>Link:</em> ${citation.link ? `<a href="${escapeHtml(citation.link)}" target="_blank" rel="noreferrer">${escapeHtml(citation.link)}</a>` : "No link provided"}</div>`
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
    appendLog("Upload began. Preparing selected PDF for ingestion.", "Info")
    setUploadButtonEnabled(false)

    try {
        let file = document.getElementById("file").files[0]
        if (!file) throw new Error("No file selected")

        appendLog(`Selected file: ${file.name} (${Math.round(file.size / 1024)} KB).`, "Debug")
        let form = new FormData()
        form.append("file", file)

        let response = await fetch("/upload", { method: "POST", body: form })
        let result = await response.json()
        if (!response.ok || result.status === "error") {
            throw new Error(result.message || "Upload failed")
        }

        currentCaseId = result.case_id
        appendLog(`Upload completed. Assigned case id ${currentCaseId}.`, "Info")
        updateStatus("Upload completed. Analysis is starting.")

        let genResult = await generate()
        if (!genResult.success || pipelineCancelled) {
            appendLog("Upload flow stopped before analysis could complete.", "Error")
            return { success: false }
        }

        appendLog("Case processed successfully. Strategise is now available.", "Info")
        updateStatus("File uploaded and processed. Open Strategise to review the argument.")
        setStrategiseEnabled(true)
        setDownloadEnabled(true)
        showArgumentScreen()

        let valResult = await validate()
        if (!valResult.success || pipelineCancelled) {
            appendLog("Validation did not complete after analysis.", "Error")
            return { success: false }
        }

        validationReady = true
        setDownloadEnabled(true)
        appendLog("Validation completed. Review the argument, add comments, then finalize and download.", "Info")
        updateStatus("Validation complete. Review, edit, comment, and download the final version.")
        return { success: true }
    } catch (err) {
        updateStatus("Upload failed.")
        appendLog(`Upload flow failed: ${err.message}`, "Error")
        alert("Upload failed: " + err.message)
        return { success: false }
    } finally {
        showSpinner(false)
        setUploadButtonEnabled(true)
    }
}

async function generate() {
    updateStatus("Analysis in progress.")
    appendLog("Analysis agent started. Extracting demands, arguments, and citations.", "Info")

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

        appendLog("Analysis completed successfully. Draft argument received from backend.", "Info")
        appendLog(`Citation count returned: ${data.citations.length}.`, "Debug")
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

        return { success: true }
    } catch (err) {
        updateStatus("Analysis failed.")
        appendLog(`Analysis failed: ${err.message}`, "Error")
        alert("Generation failed: " + err.message)
        return { success: false }
    }
}

async function validate() {
    updateStatus("Validation in progress.")
    appendLog("Validation agent started. Polling backend for detailed review.", "Info")

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
        appendLog(`Validation task created: ${taskId}.`, "Debug")

        return new Promise((resolve) => {
            let pollInterval = setInterval(async () => {
                try {
                    let statusRes = await fetch(`/validate/status/${taskId}`)
                    let statusData = await statusRes.json()

                    if (pipelineCancelled) {
                        clearInterval(pollInterval)
                        updateStatus("Validation cancelled.")
                        appendLog("Validation polling stopped because the pipeline was cancelled.", "Info")
                        resolve({ success: false })
                        return
                    }

                    if (statusData.status === "pending") {
                        appendLog("Validation still running. Awaiting Gemini review output.", "Debug")
                        return
                    }

                    clearInterval(pollInterval)
                    if (statusData.status === "error") {
                        throw new Error(statusData.error || "Validation failed")
                    }

                    let validationData = typeof statusData.result === "string" ? JSON.parse(statusData.result) : statusData.result
                    let summary =
                        `Overall validity: ${validationData.overall_validity_score ?? "N/A"}/10\n` +
                        `Logic: ${validationData.logic_score ?? "N/A"}/10\n` +
                        `Citations: ${validationData.citation_validity_score ?? "N/A"}/10\n\n` +
                        `Issues:\n${(validationData.issues_found || []).map(item => `- ${item}`).join("\n") || "- None reported"}\n\n` +
                        `Suggested improvements:\n${(validationData.suggested_improvements || []).map(item => `- ${item}`).join("\n") || "- None reported"}`

                    document.getElementById("validationSummary").innerText = summary
                    appendLog("Validation completed and the summary panel was updated.", "Info")
                    appendLog(`Validation scores: overall ${validationData.overall_validity_score ?? "N/A"}, logic ${validationData.logic_score ?? "N/A"}, citations ${validationData.citation_validity_score ?? "N/A"}.`, "Debug")
                    resolve({ success: true })
                } catch (pollErr) {
                    clearInterval(pollInterval)
                    updateStatus("Validation failed.")
                    appendLog(`Validation polling failed: ${pollErr.message}`, "Error")
                    alert("Validation failed: " + pollErr.message)
                    resolve({ success: false })
                }
            }, 2000)
        })
    } catch (err) {
        updateStatus("Validation failed.")
        appendLog(`Validation start failed: ${err.message}`, "Error")
        alert("Validation failed: " + err.message)
        return { success: false }
    }
}

async function finalizeAndDownload() {
    updateStatus("Finalizing argument and generating PDF.")
    appendLog("Finalization requested. Sending edited draft and reviewer comments to backend.", "Info")
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

        appendLog(`Finalized argument downloaded successfully: ${filename}.`, "Info")
        updateStatus(`Finalized PDF generated: ${filename}.`)
        return { success: true }
    } catch (err) {
        setDownloadProgress(100, "Finalisation failed.")
        appendDownloadLog(`Finalisation failed: ${err.message}`)
        updateStatus("Finalization failed.")
        appendLog(`Finalization failed: ${err.message}`, "Error")
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
