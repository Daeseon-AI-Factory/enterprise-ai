import Vue from "vue";
import ChatWidget from "./ChatWidget.vue";

// Auto-mount widget when script is loaded
const mountPoint = document.createElement("div");
mountPoint.id = "ai-chat-widget-root";
document.body.appendChild(mountPoint);

new Vue({
  render: (h) => h(ChatWidget),
}).$mount("#ai-chat-widget-root");
