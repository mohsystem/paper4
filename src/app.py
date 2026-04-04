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
DEFAULT_MODEL = "gpt-4o"
DEFAULT_INCLUDE_TESTS = True
DEFAULT_SAVE_TO_DISK = False
DEFAULT_OUTPUT_DIRECTORY = None
target_lang = "Java"

def build_logger() -> logging.Logger:
    os.makedirs("./logs", exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logging.basicConfig(
        filename=f"./logs/api_processing_{today}.log",
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
    model: str = Field(..., examples=["gpt-4o", "gemini-1.5-pro-002", "codestral-latest"])


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
    LOGGER.info("Tagging prompt created for task_number=%s provider=%s model=%s", task_number, provider, model)

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
    LOGGER.info("Assigned tags task_number=%s tags=%s raw=%s", task_number, assigned_tags, tag_list_response)

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
    LOGGER.info("instruction_message length=%s", len(instruction_message))

    if req.options.save_to_disk:
        today = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out_dir = f"./logs/{req.participant_id}/{task_number}_{today}"
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{output_filename}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(instruction_message)
        LOGGER.info("Saved output task_number=%s path=%s", task_number, out_path)

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
body { font-family: Arial; margin: 24px; background:#fafafa; }
.wrap { max-width: 1200px; margin:auto; }
.row { display:grid; grid-template-columns: 1fr 1fr; gap:16px; }
.card { background:white; padding:16px; border-radius:12px; border:1px solid #e5e7eb; }
label { font-weight:bold; display:block; margin-top:10px; }
input, textarea { width:100%; padding:8px; margin-top:6px; border:1px solid #ccc; border-radius:6px; }
textarea { min-height:160px; resize:vertical; font-family:monospace; }
#instruction { min-height:360px; }
button { margin-top:12px; padding:10px 14px; background:#2563eb; color:white; border:none; border-radius:8px; cursor:pointer; }
.status { margin-top:10px; font-size:13px; }
</style>
</head>

<body>
<div class="wrap">
<h2>Secure Prompt Generator</h2>

<div class="row">

<!-- LEFT: INPUT -->
<div class="card">
<label>Participant Id</label>
<input id="participantId" value="user1">

<label>FR Number</label>
<input id="taskNumber" type="number" value="1">

<label>FR Title</label>
<input id="promptTitle" value="Find Maximum">

<label>FR Description</label>
<textarea id="promptDescription">Example: Write a function that takes two integers as input and returns the maximum of the two numbers.</textarea>

<button onclick="runTask()">Run</button>
<div id="status" class="status"></div>
</div>

<!-- RIGHT: OUTPUT -->
<div class="card">
<label>Instruction Message</label>
<textarea id="instruction" readonly></textarea>

<label>Full API Response</label>
<textarea id="output" readonly></textarea>
</div>

</div>
</div>

<script>
async function runTask() {

  document.getElementById("status").textContent = "Running...";
  document.getElementById("instruction").value = "";
  document.getElementById("output").value = "";

  const payload = {
    promptType: "ourMethod",
    participant_id: document.getElementById("participantId").value,
    active_integration: {
      provider: "OPENAI",
      model: "gpt-4o"
    },
    task: {
      task_number: Number(document.getElementById("taskNumber").value),
      prompt_title: document.getElementById("promptTitle").value,
      prompt_description: document.getElementById("promptDescription").value
    },
    options: {
      include_tests: true,
      save_to_disk: true,
      output_directory: "./"
    }
  };

  try {
    const res = await fetch("/v1/task/run", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    // ⭐ Put instruction_message in separate area
    document.getElementById("instruction").value =
      data.instruction_message || "";

    // ⭐ Full JSON response
    document.getElementById("output").value =
      JSON.stringify(data, null, 2);

    document.getElementById("status").textContent = "Done";
  }
  catch(err) {
    document.getElementById("status").textContent = "Error";
    document.getElementById("output").value = err;
  }
}
</script>

</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)