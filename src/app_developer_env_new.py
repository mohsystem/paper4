"""
Task Runner UI - Single file Flask app for LLM interaction and conversation tracking
"""
import json
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session
from openai import OpenAI
import uuid
import logging
import os
# import datetime

app = Flask(__name__)


# Configuration
DEFAULT_PROVIDER = "OPENAI"
DEFAULT_MODEL = "gpt-5.2-2025-12-11"
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# In-memory storage: {participant_id: {conversation_id: {messages: [...], metadata: {...}}}}
conversations_db = {}



def build_logger() -> logging.Logger:
    os.makedirs("./logs/developer", exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    logging.basicConfig(
        filename=f"./logs/developer/api_processing_{today}.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return logging.getLogger("task_api")

LOGGER = build_logger()

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Runner UI</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1a2a3a 0%, #0f1419 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 20px;
        }

        .panel {
            background: rgba(30, 45, 60, 0.8);
            border: 1px solid rgba(100, 150, 200, 0.3);
            border-radius: 12px;
            padding: 24px;
            backdrop-filter: blur(10px);
        }

        .title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #ffffff;
        }

        .subtitle {
            font-size: 14px;
            color: #a0a0a0;
            margin-bottom: 24px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 8px;
            color: #b0b0b0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 12px;
            background: rgba(20, 30, 45, 0.6);
            border: 1px solid rgba(100, 150, 200, 0.2);
            border-radius: 8px;
            color: #ffffff;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 13px;
            transition: all 0.3s ease;
        }

        .form-group input:focus,
        .form-group textarea:focus,
        .form-group select:focus {
            outline: none;
            border-color: rgba(100, 180, 255, 0.6);
            background: rgba(20, 30, 45, 0.9);
            box-shadow: 0 0 12px rgba(100, 180, 255, 0.2);
        }

        .form-group textarea {
            min-height: 140px;
            resize: vertical;
            font-size: 13px;
        }

        .button-group {
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }

        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #4a9d6f 0%, #3a7d5f 100%);
            color: white;
            flex: 1;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(74, 157, 111, 0.3);
        }

        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .btn-secondary {
            background: rgba(100, 120, 140, 0.3);
            color: #a0a0a0;
            flex: 1;
        }

        .btn-secondary:hover {
            background: rgba(100, 120, 140, 0.5);
        }

        .conversation-list {
            margin-bottom: 20px;
            max-height: 300px;
            overflow-y: auto;
        }

        .conversation-item {
            padding: 12px;
            background: rgba(20, 30, 45, 0.6);
            border: 1px solid rgba(100, 150, 200, 0.2);
            border-radius: 6px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 12px;
        }

        .conversation-item:hover {
            background: rgba(20, 30, 45, 0.9);
            border-color: rgba(100, 180, 255, 0.4);
        }

        .conversation-item.active {
            background: rgba(100, 180, 255, 0.2);
            border-color: rgba(100, 180, 255, 0.6);
        }

        .conversation-item-time {
            color: #707070;
            font-size: 11px;
        }

        .history-panel {
            max-height: 600px;
            overflow-y: auto;
        }

        .message {
            margin-bottom: 16px;
            padding: 12px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.6;
        }

        .message.user {
            background: rgba(74, 157, 111, 0.15);
            border-left: 3px solid #4a9d6f;
            margin-left: 20px;
        }

        .message.assistant {
            background: rgba(100, 150, 200, 0.15);
            border-left: 3px solid #6496c8;
            margin-right: 20px;
        }

        .message-role {
            font-weight: 600;
            color: #c0c0c0;
            font-size: 11px;
            text-transform: uppercase;
            margin-bottom: 6px;
        }

        .message-content {
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .loading {
            display: inline-block;
            width: 12px;
            height: 12px;
            background: #4a9d6f;
            border-radius: 50%;
            animation: pulse 1s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .error-message {
            padding: 12px;
            background: rgba(200, 50, 50, 0.2);
            border: 1px solid rgba(200, 50, 50, 0.5);
            border-radius: 6px;
            color: #ff8080;
            font-size: 13px;
            margin-bottom: 12px;
        }

        .info-message {
            padding: 12px;
            background: rgba(100, 180, 255, 0.15);
            border: 1px solid rgba(100, 180, 255, 0.3);
            border-radius: 6px;
            color: #a0d8ff;
            font-size: 13px;
            margin-bottom: 12px;
        }

        .model-info {
            font-size: 11px;
            color: #707070;
            margin-top: 12px;
            padding: 8px;
            background: rgba(20, 30, 45, 0.6);
            border-radius: 4px;
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }

        .copy-btn {
            background: rgba(100, 180, 255, 0.2);
            border: 1px solid rgba(100, 180, 255, 0.4);
            color: #a0d8ff;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: none;
        }

        .message:hover .copy-btn {
            display: inline-block;
        }

        .copy-btn:hover {
            background: rgba(100, 180, 255, 0.4);
            border-color: rgba(100, 180, 255, 0.6);
        }

        .copy-btn.copied {
            background: rgba(74, 157, 111, 0.3);
            border-color: rgba(74, 157, 111, 0.6);
            color: #7fd49f;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Input Panel -->
        <div class="panel">
            <div class="title">LLM Code Generation</div>
            <div class="subtitle">Developer environment for LLM code generation. Fill the prompt and review the generated response below.</div>

            <div id="error-container"></div>

            <div class="form-group">
                <label>Participant Id</label>
                <input type="text" id="participantId" placeholder="user1" value="user1">
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                <div class="form-group">
                    <label>FR Number</label>
                    <input type="text" id="frNumber" placeholder="">
                </div>
                <div class="form-group">
                    <label>FR Title</label>
                    <input type="text" id="frTitle" placeholder="Find Maximum">
                </div>
            </div>

            <div class="form-group">
                <label>FR Description</label>
                <textarea id="frDescription" placeholder="Give me all input that I gave to you in this conversation"></textarea>
            </div>

            <div class="button-group">
                <button class="btn-primary" onclick="runTask()" id="runBtn">Run task</button>
                <button class="btn-secondary" onclick="clearForm()">Clear</button>
            </div>
            
            <div class="form-group">
                <label></label>
                <label>Conversation</label>
                <div class="conversation-list" id="conversationList">
                    <div class="info-message">No conversations yet. Create one with a prompt.</div>
                </div>
                <button class="btn-secondary" onclick="newConversation()">+ New Conversation</button>
            </div>

        </div>

        <!-- History Panel -->
        <div class="panel">
            <div class="title">Conversation History</div>
            <div class="subtitle">Current conversation messages</div>

            <div class="history-panel" id="history">
                <div class="info-message">Messages will appear here. Start a new conversation or select an existing one.</div>
            </div>
        </div>
    </div>

    <script>
        let currentParticipantId = 'user1';
        let currentConversationId = null;
        let allConversations = {};

        // Load conversations on page load
        document.addEventListener('DOMContentLoaded', () => {
            const savedParticipantId = localStorage.getItem('participantId');
            if (savedParticipantId) {
                currentParticipantId = savedParticipantId;
                document.getElementById('participantId').value = savedParticipantId;
            }
            loadConversations();
        });

        // Update participant ID on change
        document.getElementById('participantId').addEventListener('change', (e) => {
            currentParticipantId = e.target.value || 'user1';
            localStorage.setItem('participantId', currentParticipantId);
            currentConversationId = null;
            loadConversations();
        });

        function loadConversations() {
            fetch(`/api/conversations?participant_id=${encodeURIComponent(currentParticipantId)}`)
                .then(r => r.json())
                .then(data => {
                    allConversations = data.conversations || {};
                    renderConversationList();
                })
                .catch(err => showError('Failed to load conversations: ' + err));
        }

        function renderConversationList() {
            const list = document.getElementById('conversationList');
            const conversations = Object.values(allConversations);

            if (conversations.length === 0) {
                list.innerHTML = '<div class="info-message">No conversations yet. Create one with a prompt.</div>';
                return;
            }

            list.innerHTML = conversations.map(conv => `
                <div class="conversation-item ${conv.id === currentConversationId ? 'active' : ''}" onclick="selectConversation('${conv.id}')">
                    <div><strong>${conv.metadata?.title || 'Untitled'}</strong></div>
                    <div class="conversation-item-time">${new Date(conv.metadata?.created_at).toLocaleString()}</div>
                    <div style="color: #707070; font-size: 11px;">${conv.messages?.length || 0} messages</div>
                </div>
            `).join('');
        }

        function selectConversation(conversationId) {
            currentConversationId = conversationId;
            renderConversationList();
            displayHistory();
        }

        function newConversation() {
            currentConversationId = null;
            clearForm();
            displayHistory();
        }

        function displayHistory() {
            const historyDiv = document.getElementById('history');

            if (!currentConversationId || !allConversations[currentConversationId]) {
                historyDiv.innerHTML = '<div class="info-message">No conversation selected. Create or select a conversation to view history.</div>';
                return;
            }

            const messages = allConversations[currentConversationId].messages || [];

            if (messages.length === 0) {
                historyDiv.innerHTML = '<div class="info-message">No messages yet. Send a prompt to start.</div>';
                return;
            }

            historyDiv.innerHTML = messages.map((msg, idx) => `
                <div class="message ${msg.role}">
                    <div class="message-header">
                        <div class="message-role">${msg.role}</div>
                        <button class="copy-btn" onclick="copyToClipboard(${idx}, this)">Copy</button>
                    </div>
                    <div class="message-content">${escapeHtml(msg.content)}</div>
                </div>
            `).join('');

            historyDiv.scrollTop = historyDiv.scrollHeight;
        }

        function runTask() {
            const participantId = document.getElementById('participantId').value || 'user1';
            const frNumber = document.getElementById('frNumber').value;
            const frTitle = document.getElementById('frTitle').value;
            const frDescription = document.getElementById('frDescription').value;

            if (!frDescription.trim()) {
                showError('Please enter a prompt in FR Description');
                return;
            }

            const btn = document.getElementById('runBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Running...';
            clearError();

            const payload = {
                participant_id: participantId,
                conversation_id: currentConversationId,
                fr_number: frNumber,
                fr_title: frTitle,
                prompt: frDescription
            };

            fetch('/api/run-task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
                .then(r => r.json())
                .then(data => {
                    if (data.error) {
                        showError(data.error);
                    } else {
                        currentConversationId = data.conversation_id;
                        allConversations[currentConversationId] = data.conversation;
                        renderConversationList();
                        displayHistory();
                        document.getElementById('frDescription').value = '';
                    }
                })
                .catch(err => showError('Error: ' + err))
                .finally(() => {
                    btn.disabled = false;
                    btn.innerHTML = 'Run task';
                });
        }

        function clearForm() {
            document.getElementById('frNumber').value = '';
            document.getElementById('frTitle').value = '';
            document.getElementById('frDescription').value = '';
            clearError();
        }

        function showError(msg) {
            const container = document.getElementById('error-container');
            container.innerHTML = `<div class="error-message">${escapeHtml(msg)}</div>`;
        }

        function clearError() {
            document.getElementById('error-container').innerHTML = '';
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function copyToClipboard(messageIdx, btn) {
            const messages = allConversations[currentConversationId].messages || [];
            const message = messages[messageIdx];

            if (!message) return;

            navigator.clipboard.writeText(message.content).then(() => {
                const originalText = btn.textContent;
                btn.textContent = 'Copied!';
                btn.classList.add('copied');

                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.classList.remove('copied');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
                showError('Failed to copy to clipboard');
            });
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the main UI"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for a participant"""
    participant_id = request.args.get('participant_id', 'default')

    if participant_id not in conversations_db:
        return jsonify({'conversations': {}})

    conversations = conversations_db[participant_id]
    return jsonify({
        'conversations': {
            conv_id: {
                'id': conv_id,
                'metadata': conv.get('metadata', {}),
                'messages': conv.get('messages', [])
            }
            for conv_id, conv in conversations.items()
        }
    })


@app.route('/api/run-task', methods=['POST'])
def run_task():
    """Process a task: add message to conversation and get LLM response"""
    data = request.get_json()

    if not client:
        return jsonify({
            'error': 'OpenAI API key not configured. Set OPENAI_API_KEY environment variable.'
        }), 400

    participant_id = data.get('participant_id', 'default')
    conversation_id = data.get('conversation_id')
    prompt = data.get('prompt', '')
    fr_number = data.get('fr_number', '')
    fr_title = data.get('fr_title', '')
    LOGGER.info(
        "Request - conversation_id=%s;  participantId=%s; task_number=%s;  fr_title=%s;  task=%s",
        conversation_id,
        participant_id,
        fr_number,
        fr_title,
        prompt
    )
    if not prompt.strip():
        return jsonify({'error': 'Prompt cannot be empty'}), 400

    # Initialize participant if needed
    if participant_id not in conversations_db:
        conversations_db[participant_id] = {}

    # Create new conversation if needed
    if not conversation_id or conversation_id not in conversations_db[participant_id]:
        conversation_id = str(uuid.uuid4())
        conversations_db[participant_id][conversation_id] = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'title': fr_title or 'Untitled',
                'fr_number': fr_number
            },
            'messages': [
                {
                    'role': 'user',
                    'content':                 """
                You are code assistant for writing code for Spring boot application.
                Consider to give all necessary code for a new application, and use Gradle build tool.
                Include the package name, file location considering the following project source code packages under the main package com.um.springbootprojstructure: config, controller, dto, entity, mapper, repository, service. with application.properties file.
                """
                }
            ]
        }

    conversation = conversations_db[participant_id][conversation_id]

    # Add user message
    conversation['messages'].append({
        'role': 'user',
        'content': prompt
    })

    # Get LLM response
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=conversation['messages'],
            temperature=1,
            max_completion_tokens=32000
        )

        assistant_message = response.choices[0].message.content
        LOGGER.info(
            "Request - conversation_id=%s;  participantId=%s; task_number=%s;  fr_title=%s;  task=%s;  assistant_message=%s",
            conversation_id,
            participant_id,
            fr_number,
            fr_title,
            prompt,
            assistant_message
        )
        conversation['messages'].append({
            'role': 'assistant',
            'content': assistant_message
        })

    except Exception as e:
        # Remove user message if LLM call fails
        conversation['messages'].pop()

        LOGGER.info(
            "Request - conversation_id=%s;  participantId=%s; task_number=%s;  fr_title=%s;  Exception=%s",
            conversation_id,
            participant_id,
            fr_number,
            fr_title,
            str(e)
        )
        return jsonify({
            'error': f'LLM Error: {str(e)}'
        }), 500

    return jsonify({
        'conversation_id': conversation_id,
        'conversation': {
            'id': conversation_id,
            'metadata': conversation['metadata'],
            'messages': conversation['messages']
        }
    })


if __name__ == '__main__':
    print("Starting Task Runner UI...")
    print("\nConfiguration:")
    print(f"  Provider: {DEFAULT_PROVIDER}")
    print(f"  Model: {DEFAULT_MODEL}")
    print(f"  API Key configured: {bool(OPENAI_API_KEY)}")
    print("\nOpen http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000) # Listen on all public IPs
