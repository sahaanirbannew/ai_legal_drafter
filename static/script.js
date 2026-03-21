// Client-side JavaScript for AI legal arguments app

async function upload(){

let status = document.getElementById("status")
status.innerText = "Uploading..."

let file=document.getElementById("file").files[0]

let form=new FormData()
form.append("file",file)

await fetch("/upload",{method:"POST",body:form})

status.innerText = "Uploaded"
}

async function validate(){

let status = document.getElementById("status")
status.innerText = "Validating..."

let res = await fetch("/validate",{method:"POST"})

let data = await res.json()

status.innerText = "Validation complete"

let validationData = JSON.parse(data.validation)

let validationText = `VALIDATION REPORT

Overall Validity Score: ${validationData.overall_validity_score}/10
Logic Score: ${validationData.logic_score}/10
Citation Validity Score: ${validationData.citation_validity_score}/10

Issues Found:
${validationData.issues_found.map(issue => `- ${issue}`).join('\n')}

Suggested Improvements:
${validationData.suggested_improvements.map(improvement => `- ${improvement}`).join('\n')}

Hallucinated Citations:
${validationData.hallucinated_citations.map(citation => `- ${citation}`).join('\n')}`

document.getElementById("validation").innerText = validationText
}

async function generate(){

let status = document.getElementById("status")
status.innerText = "Generating..."

let res=await fetch("/analyze",{method:"POST"})

let data=await res.json()

status.innerText = "Done"

document.getElementById("output").innerText=data.text

let div=document.getElementById("citations")

div.innerHTML=""

data.citations.forEach((c,i)=>{

let btn=document.createElement("button")

btn.innerText=c.case_name

btn.onclick=()=>{

alert(
"Description:"+c.description+
"\nWhy cited:"+c.why_cited+
"\nRelevance:"+c.relevance_score+
"\nStrength:"+c.strength_score+
"\nLink:"+c.link
)

}

div.appendChild(btn)

})

}

async function download(){

let status = document.getElementById("status")
status.innerText = "Generating PDF..."

let res = await fetch("/generate_pdf", {method: "POST"})

if (!res.ok) {
    status.innerText = "PDF generation failed"
    alert("Error generating PDF. Try again.")
    return
}

let filename = "legal_argument.pdf"
let contentDisposition = res.headers.get("content-disposition")
if (contentDisposition) {
    let match = contentDisposition.match(/filename="?(.*)"?$/)
    if (match && match[1]) {
        filename = match[1]
    }
}

let blob = await res.blob()
let url = URL.createObjectURL(blob)
let a = document.createElement("a")
a.href = url
a.download = filename
document.body.appendChild(a)
a.click()
document.body.removeChild(a)
URL.revokeObjectURL(url)

status.innerText = `PDF generated: ${filename}.\nSaved in your browser downloads folder (typically ~/Downloads).`

let info = document.getElementById("status")
info.innerText = `PDF generated as ${filename}. It will be saved to your browser's default download folder (usually ~/Downloads).`
}
