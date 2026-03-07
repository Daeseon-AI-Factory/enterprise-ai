<template>
  <div class="ai-widget">
    <!-- Floating bubble button -->
    <button v-if="!isOpen" class="ai-widget-bubble" @click="isOpen = true">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
    </button>

    <!-- Chat panel -->
    <div v-if="isOpen" class="ai-widget-panel">
      <div class="ai-widget-header">
        <span>AI Assistant</span>
        <button class="ai-widget-close" @click="isOpen = false">&times;</button>
      </div>

      <div class="ai-widget-messages" ref="messagesContainer">
        <div
          v-for="(msg, i) in messages"
          :key="i"
          :class="['ai-widget-msg', msg.role === 'user' ? 'ai-widget-msg-user' : 'ai-widget-msg-ai']"
        >
          <div class="ai-widget-msg-content" v-html="renderMarkdown(msg.content)"></div>
        </div>
        <div v-if="loading" class="ai-widget-msg ai-widget-msg-ai">
          <div class="ai-widget-typing">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <div class="ai-widget-input">
        <textarea
          v-model="input"
          placeholder="메시지를 입력하세요..."
          @keydown.enter.exact.prevent="send"
          rows="1"
        ></textarea>
        <button @click="send" :disabled="!input.trim() || loading">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { marked } from "marked";

// Detect API base from script src or default
const API_BASE =
  document.currentScript?.getAttribute("data-api") ||
  window.AI_CHAT_API_BASE ||
  "http://localhost:8080";

export default {
  name: "AIChatWidget",
  data() {
    return {
      isOpen: false,
      input: "",
      messages: [],
      loading: false,
      conversationId: null,
    };
  },
  methods: {
    async send() {
      const text = this.input.trim();
      if (!text || this.loading) return;

      this.messages.push({ role: "user", content: text });
      this.input = "";
      this.loading = true;
      this.scrollToBottom();

      try {
        const { data } = await axios.post(`${API_BASE}/api/chat/with-context`, {
          message: text,
          conversation_id: this.conversationId,
          context: {
            page_url: window.location.href,
            component: document.title,
          },
        });
        this.conversationId = data.conversation_id;
        this.messages.push({ role: "assistant", content: data.reply });
      } catch (err) {
        this.messages.push({
          role: "assistant",
          content: "죄송합니다. 연결에 문제가 발생했습니다.",
        });
      } finally {
        this.loading = false;
        this.scrollToBottom();
      }
    },
    renderMarkdown(text) {
      return marked.parse(text || "");
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer;
        if (container) container.scrollTop = container.scrollHeight;
      });
    },
  },
};
</script>

<style scoped>
.ai-widget {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 99999;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.ai-widget-bubble {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #2563eb;
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s;
}
.ai-widget-bubble:hover {
  transform: scale(1.1);
}

.ai-widget-panel {
  width: 380px;
  height: 520px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ai-widget-header {
  padding: 16px;
  background: #2563eb;
  color: white;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ai-widget-close {
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  line-height: 1;
}

.ai-widget-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-widget-msg {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
}
.ai-widget-msg-user {
  align-self: flex-end;
  background: #2563eb;
  color: white;
  border-bottom-right-radius: 4px;
}
.ai-widget-msg-ai {
  align-self: flex-start;
  background: #f1f5f9;
  color: #1e293b;
  border-bottom-left-radius: 4px;
}

.ai-widget-input {
  padding: 12px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  gap: 8px;
  align-items: flex-end;
}
.ai-widget-input textarea {
  flex: 1;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  resize: none;
  outline: none;
  font-family: inherit;
  max-height: 80px;
}
.ai-widget-input textarea:focus {
  border-color: #2563eb;
}
.ai-widget-input button {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ai-widget-input button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ai-widget-typing span {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  margin: 0 2px;
  animation: ai-typing 1.4s infinite;
}
.ai-widget-typing span:nth-child(2) { animation-delay: 0.2s; }
.ai-widget-typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes ai-typing {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.ai-widget-msg-content :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
}
.ai-widget-msg-content :deep(code) {
  font-family: "Fira Code", monospace;
}
</style>
