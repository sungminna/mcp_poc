import { p as push, G as attr_class, I as ensure_array_like, E as escape_html, J as stringify, K as attr, n as pop, L as fallback, M as bind_props } from './exports-BKcDwPi0.js';
import './client-B_u6nehf.js';

function ChatMessage($$payload, $$props) {
  push();
  let messageClasses;
  let message = $$props["message"];
  let isLoading = fallback($$props["isLoading"], false);
  messageClasses = {
    base: "message-bubble",
    user: message.sender === "user" ? "user-message" : "",
    ai: message.sender === "ai" ? "ai-message" : "",
    loading: isLoading ? "loading" : ""
  };
  $$payload.out += `<div${attr_class(`message-wrapper ${stringify(message.sender === "user" ? "user" : "ai")}`, "svelte-yc7ucn")}><div${attr_class(`${stringify(messageClasses.base)} ${stringify(messageClasses.user)} ${stringify(messageClasses.ai)} ${stringify(messageClasses.loading)}`, "svelte-yc7ucn")}>`;
  if (isLoading) {
    $$payload.out += "<!--[-->";
    $$payload.out += `<div class="dot-flashing svelte-yc7ucn"></div>`;
  } else {
    $$payload.out += "<!--[!-->";
    $$payload.out += `<div class="message-content svelte-yc7ucn">${escape_html(message.text ?? message.content)}</div>`;
  }
  $$payload.out += `<!--]--></div> `;
  if (!isLoading) {
    $$payload.out += "<!--[-->";
    $$payload.out += `<div class="timestamp svelte-yc7ucn">${escape_html(new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }))}</div>`;
  } else {
    $$payload.out += "<!--[!-->";
  }
  $$payload.out += `<!--]--></div>`;
  bind_props($$props, { message, isLoading });
  pop();
}
function IconSend($$payload, $$props) {
  let size = fallback($$props["size"], 24);
  let color = fallback($$props["color"], "currentColor");
  $$payload.out += `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"${attr("fill", color)}${attr("width", size)}${attr("height", size)}><path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z"></path></svg>`;
  bind_props($$props, { size, color });
}
function IconHamburger($$payload, $$props) {
  let size = fallback($$props["size"], 24);
  let color = fallback($$props["color"], "currentColor");
  $$payload.out += `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"${attr("stroke", color)}${attr("width", size)}${attr("height", size)}><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>`;
  bind_props($$props, { size, color });
}
function _page($$payload, $$props) {
  push();
  let sessions = [];
  let selectedSessionId = null;
  let messages = [];
  let newMessageText = "";
  let loadingAIResponse = false;
  let groupedMessages = [];
  let groupTitle = "새로운 채팅";
  groupTitle = "새로운 채팅";
  {
    let lastDate = "";
    groupedMessages = [];
    for (const m of messages) {
      const dateStr = new Date(m.timestamp).toLocaleDateString();
      if (dateStr !== lastDate) {
        groupedMessages.push({ type: "date", date: dateStr });
        lastDate = dateStr;
      }
      groupedMessages.push({ type: "message", message: m });
    }
  }
  $$payload.out += `<div class="layout svelte-gnpoyf"><aside${attr_class(`sidebar ${stringify("")}`, "svelte-gnpoyf")}><button class="new-chat svelte-gnpoyf">New Chat</button> `;
  {
    $$payload.out += "<!--[!-->";
    const each_array = ensure_array_like(sessions);
    $$payload.out += `<!--[-->`;
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let sess = each_array[$$index];
      $$payload.out += `<div${attr_class(`session-item ${stringify(sess.id === selectedSessionId ? "selected" : "")}`, "svelte-gnpoyf")}><div class="session-info svelte-gnpoyf"><div class="session-name svelte-gnpoyf">${escape_html(sess.first_user_message ? sess.first_user_message.length > 20 ? sess.first_user_message.slice(0, 20) + "..." : sess.first_user_message : "새로운 대화")}</div> <div class="session-time svelte-gnpoyf">${escape_html(sess.first_ai_response ? sess.first_ai_response.length > 20 ? sess.first_ai_response.slice(0, 20) + "..." : sess.first_ai_response : "")}</div></div> <button class="delete-button svelte-gnpoyf" aria-label="Delete session">삭제</button></div>`;
    }
    $$payload.out += `<!--]-->`;
  }
  $$payload.out += `<!--]--></aside> <div class="chat-page-container svelte-gnpoyf"><header class="chat-header svelte-gnpoyf"><div class="header-left svelte-gnpoyf"><button class="icon-button toggle-button svelte-gnpoyf" aria-label="Toggle sidebar">`;
  IconHamburger($$payload, {});
  $$payload.out += `<!----></button> <span class="header-title svelte-gnpoyf">${escape_html(groupTitle)}</span></div> <div class="header-right svelte-gnpoyf">`;
  {
    $$payload.out += "<!--[!-->";
    $$payload.out += `<button class="icon-button login-button svelte-gnpoyf">로그인</button>`;
  }
  $$payload.out += `<!--]--></div></header> `;
  {
    $$payload.out += "<!--[!-->";
  }
  $$payload.out += `<!--]--> <div class="chat-messages-wrapper svelte-gnpoyf">`;
  {
    $$payload.out += "<!--[!-->";
    if (groupedMessages.length === 0) {
      $$payload.out += "<!--[-->";
      $$payload.out += `<div class="empty-state svelte-gnpoyf">새로운 대화를 시작해보세요.</div>`;
    } else {
      $$payload.out += "<!--[!-->";
      const each_array_1 = ensure_array_like(groupedMessages);
      $$payload.out += `<div class="chat-messages svelte-gnpoyf"><!--[-->`;
      for (let idx = 0, $$length = each_array_1.length; idx < $$length; idx++) {
        let item = each_array_1[idx];
        if (item.type === "date") {
          $$payload.out += "<!--[-->";
          $$payload.out += `<div class="date-sep svelte-gnpoyf">${escape_html(item.date)}</div>`;
        } else {
          $$payload.out += "<!--[!-->";
          $$payload.out += `<div>`;
          ChatMessage($$payload, { message: item.message });
          $$payload.out += `<!----></div>`;
        }
        $$payload.out += `<!--]-->`;
      }
      $$payload.out += `<!--]--> `;
      {
        $$payload.out += "<!--[!-->";
      }
      $$payload.out += `<!--]--></div>`;
    }
    $$payload.out += `<!--]-->`;
  }
  $$payload.out += `<!--]--></div> <div class="chat-input-area svelte-gnpoyf"><div class="textarea-container svelte-gnpoyf"><input${attr("value", newMessageText)} placeholder="메시지 입력" class="svelte-gnpoyf"></div> <button class="icon-button action-button svelte-gnpoyf"${attr("disabled", !newMessageText.trim() || loadingAIResponse, true)} aria-label="Send">`;
  IconSend($$payload, {});
  $$payload.out += `<!----></button></div> <footer class="chat-footer svelte-gnpoyf">Velt는 실수를 할 수 있습니다. 중요한 정보는 재차 확인하세요.</footer></div></div>`;
  pop();
}

export { _page as default };
//# sourceMappingURL=_page.svelte-D5Yy6gD0.js.map
