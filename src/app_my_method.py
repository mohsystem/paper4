import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ds_manipulation import get_related_cwe_list
from llm_integration import ModelIntegrationHandler


# ------------------------------
# Config and helpers
# ------------------------------

INSTRUCTION_MESSAGE_BASE = (
    "Instructions:\n"
    # "1) The output should include only the code, do not include any other output or descriptions.\n"
    # "2) Write the code in the following four programming language: Java. "
    # "All functions should accept the input as parameters and return the output, if any.\n"
    # "3) Put the code like the below template/example:\n"
    # "```java\n"
    # "code here:\n"
    # "```\n"
    # "```python\n"
    # "code here:\n"
    # "```\n"
    # "```cpp\n"
    # "code here:\n"
    # "```\n"
    # "```c\n"
    # "code here:\n"
    # "```\n"
    # "4) If you cannot provide the code for any of these programming languages, just put a comment inside the above code block template.\n"
    # "5) We need the output program to run as one source code file. All code needs to be in one file.\n"
)

DEFAULT_PROMPT_TYPE = "ourMethod"
DEFAULT_PROVIDER = "OPENAI"
DEFAULT_MODEL = "gpt-5.2-2025-12-11"
DEFAULT_INCLUDE_TESTS = True
DEFAULT_SAVE_TO_DISK = False
DEFAULT_OUTPUT_DIRECTORY = None
target_lang = "Java"

def build_logger() -> logging.Logger:
    os.makedirs("./logs/mymethod", exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logging.basicConfig(
        filename=f"./logs/mymethod/api_processing_{today}.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return logging.getLogger("task_api")


LOGGER = build_logger()
MODEL_HANDLER = ModelIntegrationHandler(LOGGER)


# ------------------------------
# Request / Response models
# ------------------------------

class IntegrationSpec(BaseModel):
    provider: str = Field(..., examples=["OPENAI", "GEMINI", "PERPLEXITY", "CLAUDE", "MISTRAL"])
    model: str = Field(..., examples=["gpt-5.2-2025-12-11", "gemini-1.5-pro-002", "codestral-latest"])


class TaskSpec(BaseModel):
    task_number: int
    prompt_title: str
    prompt_description: str


class OptionsSpec(BaseModel):
    include_tests: bool = True
    save_to_disk: bool = False
    output_directory: Optional[str] = None


class RunTaskRequest(BaseModel):
    participant_id: str
    promptType: str = Field(default="ourMethod", examples=["ourMethod", "Vanilla", "CoT", "ZeroShot"])
    active_integration: IntegrationSpec
    task: TaskSpec
    options: OptionsSpec = OptionsSpec()


class RunTaskResponse(BaseModel):
    participantId: str
    task_number: int
    output_filename: str
    assigned_tags: List[str]
    related_cwe_list: Any = None
    instruction_message: str
    meta: Dict[str, str]


# ------------------------------
# Core logic for one task
# ------------------------------

def build_tagging_prompt(prompt_description: str) -> str:
    return f"""
You are a secure code classification assistant. Your task is to examine the given prompt description
(i.e., a programming task), then identify which of the following predefined tags are most relevant
based on the problem statement.

Note: The assigned tags will be used to link this prompt to corresponding
vulnerabilities or weaknesses (CWE entries) that might arise in the final code.
Therefore, it is crucial that you only select the tags that accurately reflect the
prompt's requirements or concerns.

Predefined Tags:
1. Memory & Resource Management
2. Concurrency & Parallelism
3. Networking & Communication
4. Data safety and security
5. Web Development, API & Web Services
6. Database
7. Input Validation & Sanitization
8. File & I/O Handling
9. Cryptography
10. Authentication & Authorization
11. Error Handling
12. Code Injection
13. Serialization & Deserialization
14. Hardcoding
15. Language Basics

Instructions:
1. Read the `prompt_description` below.
2. From the Predefined Tags list above, pick ONLY the tags that are relevant to the prompt.
3. Return these tags in a JSON array (of strings).
4. Do not include any explanations or additional commentary.
5. If no tags apply, return the default array ["Language Basics"].

Prompt Description:
{prompt_description}

Required Output Format:
["TAG_NAME_1", "TAG_NAME_2", ...]
(Only the array of relevant tags, nothing else.)
""".strip()


def safe_parse_tags(tag_list_response: str) -> List[str]:
    try:
        parsed = json.loads(tag_list_response.strip())
        if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
            return parsed
    except Exception:
        pass
    return ["Language Basics"]


def run_single_task(req: RunTaskRequest) -> RunTaskResponse:
    provider = req.active_integration.provider.strip().upper()
    model = req.active_integration.model.strip()
    active_integration = [provider, model]

    participantId = req.participant_id
    task_number = req.task.task_number
    output_filename = "Task" + str(task_number)

    tagging_instruction_message = build_tagging_prompt(req.task.prompt_description)
    LOGGER.info("Tagging prompt created for participantId=%s task_number=%s provider=%s model=%s", participantId, task_number, provider, model)

    if provider == "CLAUDE":
        tag_list_response = MODEL_HANDLER.generate_model_response(
            active_integration=active_integration,
            gemini_model=["GEMINI", "gemini-1.5-pro-002"],
            mistral_model=["MISTRAL", "codestral-latest"],
            claude_model=["CLAUDE", model],
            openai_model=["OPENAI", "gpt-5-2025-08-07"],
            perplexity_model=["PERPLEXITY", "llama-3.1-sonar-large-128k-online"],
            instruction_message="Classify the prompt",
            prompt_description=tagging_instruction_message,
        )
    else:
        tag_list_response = MODEL_HANDLER.generate_model_response(
            active_integration=active_integration,
            gemini_model=["GEMINI", "gemini-1.5-pro-002"],
            mistral_model=["MISTRAL", "codestral-latest"],
            claude_model=["CLAUDE", "claude-3-5-sonnet-20241022"],
            openai_model=["OPENAI", "gpt-5-2025-08-07"],
            perplexity_model=["PERPLEXITY", "llama-3.1-sonar-large-128k-online"],
            instruction_message=tagging_instruction_message,
            prompt_description="",
        )

    assigned_tags = safe_parse_tags(tag_list_response)
    LOGGER.info("Assigned tags participantId=%s task_number=%s tags=%s raw=%s", participantId, task_number, assigned_tags, tag_list_response)

    related_cwe_list = get_related_cwe_list(tag_list_response,[target_lang])

    instruction_message = INSTRUCTION_MESSAGE_BASE
    # instruction_message += f"6) Give name of the main class in the generated code should be {output_filename}, if any.\n"
    # if req.options.include_tests:
    #     instruction_message += "7) If applicable, include in the generated code a main method with 5 test cases.\n"

    instruction_message += (
        "Write the code of the following prompt description based on the below Chain-of-Thought process:\n"
        f"{req.task.prompt_description}\n\n"
        "Chain-of-Thought process in code generation:\n"
        "1. Problem understanding: clearly define the purpose of the code, what functionality or logic the code needs to implement, and identify any potential inputs, outputs, and operations involved.\n"
        "2. Security requirements: ensure that code generation is free of vulnerability and security weaknesses. List of possible weaknesses to avoid as following:\n"
        f"{related_cwe_list}\n"
        "3. Secure coding generation: write the code step-by-step, ensuring the code is preventing all security weaknesses.\n"
        "4. Code review: conduct a review for the generated code line by line, to ensure there are no security weaknesses.\n"
        "5. Secure code output: produce the final code based on fixing the reviewed code, to ensure all vulnerabilities identified earlier are mitigated.\n"
    )
    LOGGER.info("instruction_message participantId=%s task_number=%s length=%s", participantId, task_number,len(instruction_message))

    if req.options.save_to_disk:
        today = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out_dir = f"./logs/mymethod/{req.participant_id}/{task_number}_{today}"
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{output_filename}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(instruction_message)
        LOGGER.info("Saved output participantId=%s task_number=%s path=%s", participantId, task_number, out_path)

    return RunTaskResponse(
        participantId=participantId,
        task_number=task_number,
        output_filename=output_filename,
        assigned_tags=assigned_tags,
        # related_cwe_list=related_cwe_list,
        instruction_message=instruction_message,
        meta={"provider": provider, "model": model},
    )


# ------------------------------
# FastAPI app
# ------------------------------

app = FastAPI(title="Task Runner API", version="1.0.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/task/run", response_model=RunTaskResponse)
def run_task(req: RunTaskRequest) -> RunTaskResponse:
    try:
        return run_single_task(req)
    except Exception as e:
        LOGGER.exception("Failed to run task_number=%s", getattr(req.task, "task_number", "unknown"))
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------
# Simple Web UI (single-page)
# ------------------------------

@app.get("/", response_class=HTMLResponse)
def ui() -> str:
    return """
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>Task Runner UI</title>
<style>
:root {
  --bg: #0b1020;
  --stroke: rgba(255,255,255,0.14);
  --text: rgba(255,255,255,0.92);
  --muted: rgba(255,255,255,0.70);
  --accent: #7ee787;
  --accent2: #5ea0ff;
  --shadow: 0 16px 40px rgba(0,0,0,0.45);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--text);
  background:
    radial-gradient(900px 600px at 18% 10%, rgba(126,231,135,0.18), transparent 60%),
    radial-gradient(900px 600px at 80% 18%, rgba(94,160,255,0.18), transparent 55%),
    radial-gradient(1200px 800px at 55% 85%, rgba(255,255,255,0.06), transparent 60%),
    var(--bg);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Arial;
}
.wrap { max-width: 1200px; margin: 28px auto; padding: 0 16px; }
.hero {
  padding: 18px 18px 14px 18px;
  border: 1px solid var(--stroke);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.05));
  box-shadow: var(--shadow);
}
.hero h1 { margin: 0; font-size: 20px; letter-spacing: 0.2px; }
.hero p { margin: 8px 0 0 0; color: var(--muted); font-size: 13px; line-height: 1.4; }
.card {
  margin-top: 14px;
  padding: 16px;
  border: 1px solid var(--stroke);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
  box-shadow: var(--shadow);
}
.grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 12px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.label { font-size: 12px; color: var(--muted); letter-spacing: 0.2px; }
input, textarea, select {
  width: 100%;
  padding: 10px 10px;
  border: 1px solid rgba(255,255,255,0.18);
  border-radius: 12px;
  background: rgba(0,0,0,0.25);
  color: var(--text);
  outline: none;
}
textarea {
  min-height: 150px;
  resize: vertical;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}
input:focus, textarea:focus, select:focus {
  border-color: rgba(126,231,135,0.65);
  box-shadow: 0 0 0 4px rgba(126,231,135,0.12);
}
.col-2 { grid-column: span 2; }
.col-3 { grid-column: span 3; }
.col-4 { grid-column: span 4; }
.col-6 { grid-column: span 6; }
.col-12 { grid-column: span 12; }
.rowline {
  grid-column: span 12;
  height: 1px;
  background: rgba(255,255,255,0.12);
  margin: 2px 0 2px 0;
}
.actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
button {
  padding: 10px 14px;
  border: 1px solid rgba(255,255,255,0.18);
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(126,231,135,0.22), rgba(126,231,135,0.10));
  color: var(--text);
  cursor: pointer;
}
button:hover { border-color: rgba(126,231,135,0.50); }
button:disabled { opacity: 0.65; cursor: not-allowed; }
.status { font-size: 12px; color: var(--muted); }
.status.ok { color: rgba(126,231,135,0.95); }
.status.bad { color: rgba(255,107,107,0.95); }
.output { margin-top: 14px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.12); }
.kv { display: grid; grid-template-columns: 160px 1fr; gap: 8px 12px; padding: 10px 0; }
.k { color: var(--muted); font-size: 12px; }
.v { font-size: 13px; }
.tags { display: flex; gap: 8px; flex-wrap: wrap; }
.tag {
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(94,160,255,0.35);
  background: rgba(94,160,255,0.10);
}
pre {
  margin: 10px 0 0 0;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(0,0,0,0.28);
  white-space: pre-wrap;
  word-break: break-word;
  overflow-x: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  line-height: 1.45;
}
details { margin-top: 10px; }
summary { cursor: pointer; color: rgba(255,255,255,0.85); }
@media (max-width: 980px) {
  .col-2, .col-3, .col-4, .col-6 { grid-column: span 12; }
  .kv { grid-template-columns: 1fr; }
}
</style>
</head>

<body>
<div class="wrap">
  <div class="hero">
    <h1>Secure Prompt Generator</h1>
  </div>

  <div class="card">
    <div class="grid">
      <div class="field col-3">
        <div class="label">Participant Id</div>
        <input id="participantId" value="user1" />
      </div>

      <div class="field col-3" style="visibility:hidden">
        <div class="label">Prompt Type</div>
        <select id="promptType">
          <option value="ourMethod" selected>ourMethod</option>
          <option value="Vanilla">Vanilla</option>
          <option value="CoT">CoT</option>
          <option value="ZeroShot">ZeroShot</option>
        </select>
      </div>

      <div class="field col-3" style="visibility:hidden">
        <div class="label">Provider</div>
        <select id="provider">
          <option value="OPENAI" selected>OPENAI</option>
          <option value="GEMINI">GEMINI</option>
          <option value="PERPLEXITY">PERPLEXITY</option>
          <option value="CLAUDE">CLAUDE</option>
          <option value="MISTRAL">MISTRAL</option>
        </select>
      </div>

      <div class="field col-3" style="visibility:hidden">
        <div class="label">Model</div>
        <input id="model" value="gpt-5.2-2025-12-11" />
      </div>

      <div class="rowline"></div>

      <div class="field col-2">
        <div class="label">FR Number</div>
        <input id="taskNumber" type="number" value="1" min="1" />
      </div>

      <div class="field col-4">
        <div class="label">FR Title</div>
        <input id="promptTitle" value="Find Maximum" />
      </div>

      <div class="field col-6" style="visibility:hidden">
        <div class="label">Options</div>
        <div class="actions" style="margin-top:2px;">
          <label style="display:flex; gap:8px; align-items:center; font-size:13px; color: var(--text);" >
            <input id="includeTests" hidden type="checkbox" checked style="width:auto; padding:0; accent-color: var(--accent);" />
          </label>
          <label style="display:flex; gap:8px; align-items:center; font-size:13px; color: var(--text);">
            <input id="saveToDisk" checked type="checkbox" style="width:auto; padding:0; accent-color: var(--accent2);" />
            Save to disk
          </label>
          <div style="display:flex; gap:8px; align-items:center; flex:1 1 280px; min-width:260px;">
            <span style="color: var(--muted); font-size: 12px;">Output dir</span>
            <input id="outputDir" placeholder="./" value="./" />
          </div>
        </div>
      </div>

      <div class="field col-12">
        <div class="label">FR Description</div>
        <textarea id="promptDescription">Example: Write a function that takes two integers as input and returns the maximum of the two numbers.</textarea>
      </div>

      <div class="field col-12">
        <div class="actions">
          <button id="runBtn" onclick="runTask()">Run task</button>
          <div id="status" class="status"></div>
        </div>
      </div>

      <div class="output col-12" id="outputArea" style="display:none;">
        <div class="kv" >
          <div class="k" style="visibility:hidden">Result</div>
          <div class="v" style="visibility:hidden" id="resultSummary"></div>

          <div class="k">Assigned tags</div>
          <div class="v"><div class="tags" id="tags"></div></div>
        </div>

        <div class="label">Instruction message</div>
        <pre id="instruction"></pre>

        <details>
          <summary>Raw API response (JSON)</summary>
          <pre id="rawJson"></pre>
        </details>
      </div>
    </div>
  </div>
</div>

<script>
function setStatus(text, kind) {
  const el = document.getElementById("status");
  el.textContent = text || "";
  el.classList.remove("ok");
  el.classList.remove("bad");
  if (kind === "ok") el.classList.add("ok");
  if (kind === "bad") el.classList.add("bad");
}

function clearOutput() {
  document.getElementById("outputArea").style.display = "none";
  document.getElementById("resultSummary").textContent = "";
  document.getElementById("tags").innerHTML = "";
  document.getElementById("instruction").textContent = "";
  document.getElementById("rawJson").textContent = "";
}

function renderTags(tags) {
  const wrap = document.getElementById("tags");
  wrap.innerHTML = "";
  if (!Array.isArray(tags) || tags.length === 0) return;
  for (const t of tags) {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = String(t);
    wrap.appendChild(span);
  }
}

async function runTask() {
  setStatus("Running...", "");
  clearOutput();
  document.getElementById("runBtn").disabled = true;

  const payload = {
    promptType: document.getElementById("promptType").value,
    participant_id: document.getElementById("participantId").value,
    active_integration: {
      provider: document.getElementById("provider").value,
      model: document.getElementById("model").value
    },
    task: {
      task_number: Number(document.getElementById("taskNumber").value),
      prompt_title: document.getElementById("promptTitle").value,
      prompt_description: document.getElementById("promptDescription").value
    },
    options: {
      include_tests: Boolean(document.getElementById("includeTests").checked),
      save_to_disk: Boolean(document.getElementById("saveToDisk").checked),
      output_directory: (document.getElementById("outputDir").value || null)
    }
  };

  try {
    const res = await fetch("/v1/task/run", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });

    const text = await res.text();
    let data = null;
    try { data = JSON.parse(text); } catch(e) { /* non-json */ }

    if (!res.ok) {
      const detail = (data && (data.detail || data.message)) ? (data.detail || data.message) : text;
      throw new Error(detail);
    }

    document.getElementById("outputArea").style.display = "block";

    const provider = (data && data.meta && data.meta.provider) ? data.meta.provider : payload.active_integration.provider;
    const model = (data && data.meta && data.meta.model) ? data.meta.model : payload.active_integration.model;
    const outFile = (data && data.output_filename) ? data.output_filename : "(unknown)";
    const taskNo = (data && data.task_number) ? data.task_number : payload.task.task_number;

    document.getElementById("resultSummary").textContent =
      "task_number=" + String(taskNo) + ", output_filename=" + String(outFile) + ", provider=" + String(provider) + ", model=" + String(model);

    renderTags((data && data.assigned_tags) ? data.assigned_tags : []);
    document.getElementById("instruction").textContent = (data && data.instruction_message) ? data.instruction_message : "";
    document.getElementById("rawJson").textContent = data ? JSON.stringify(data, null, 2) : text;

    setStatus("Done", "ok");
  }
  catch(err) {
    setStatus("Error: " + (err && err.message ? err.message : String(err)), "bad");
  }
  finally {
    document.getElementById("runBtn").disabled = false;
  }
}
</script>

</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app_my_method:app", host="localhost", port=8000, reload=False)
