const chatWindow = document.getElementById("chatWindow");
const chatBody = document.getElementById("chatBody");
const chatInput = document.getElementById("chatInput");
const chatSendButton = chatInput?.closest(".chat-input")?.querySelector("button");
const isEnglishPage = document.documentElement.lang === "en";
let landingChatId = readLandingChatId();
let landingChatBusy = false;


function readLandingChatId() {
    try {
        const value = sessionStorage.getItem("vietincare-landing-chat");
        return /^[1-9]\d{0,9}$/.test(value ?? "") ? Number(value) : null;
    } catch {
        return null;
    }
}


function rememberLandingChatId(value) {
    landingChatId = value;
    try {
        sessionStorage.setItem("vietincare-landing-chat", String(value));
    } catch {
        // The chat still works when optional browser storage is unavailable.
    }
}


async function responseJson(response) {
    let data = {};
    try {
        data = await response.json();
    } catch {
        // Convert non-JSON service failures to a stable client error.
    }
    if (!response.ok) throw new Error(data.error || "SERVICE_UNAVAILABLE");
    return data;
}


async function chatGet(path) {
    const response = await fetch(path, { credentials: "same-origin", cache: "no-store" });
    return responseJson(response);
}


async function chatPost(path, body) {
    const fingerprint = JSON.stringify([path, body]);
    const bytes = new TextEncoder().encode(fingerprint);
    const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))]
        .map(value => value.toString(16).padStart(2, "0")).join("");
    const storageKey = `vietincare-landing-request-${digest}`;
    let requestKey;
    try {
        requestKey = sessionStorage.getItem(storageKey);
    } catch {
        // Fall back to an in-memory request when storage is unavailable.
    }
    requestKey ||= crypto.randomUUID();
    try {
        sessionStorage.setItem(storageKey, requestKey);
    } catch {
        // Idempotency is still enforced for this request by the generated key.
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 70000);
    try {
        const response = await fetch(path, {
            method: "POST",
            credentials: "same-origin",
            cache: "no-store",
            signal: controller.signal,
            headers: {
                "Content-Type": "application/json",
                "X-Vietincare-Request": "1",
                "Idempotency-Key": requestKey
            },
            body: JSON.stringify(body)
        });
        if (response.ok || response.status < 500) {
            try { sessionStorage.removeItem(storageKey); } catch { /* Optional storage. */ }
        }
        return await responseJson(response);
    } finally {
        clearTimeout(timer);
    }
}


function openChat() {

    if (!chatWindow) return;

    chatWindow.classList.add("active");

    setTimeout(() => {
        if (chatInput) {
            chatInput.focus();
        }
    }, 200);
}


function closeChat() {

    if (!chatWindow) return;

    chatWindow.classList.remove("active");
}


function handleEnter(event) {

    if (event.key === "Enter" && !event.isComposing) {
        event.preventDefault();
        sendMessage();
    }
}


async function sendMessage(mainScreenMess) {
    if (!chatBody || landingChatBusy) return;
    const text = (typeof mainScreenMess === "string" ? mainScreenMess : chatInput?.value ?? "").trim();
    if (!text) return;
    addMessage(text, "user");
    if (typeof mainScreenMess !== "string" && chatInput) chatInput.value = "";
    const pending = addMessage(
        isEnglishPage ? "Saving your message and asking Gemini…" : "Đang lưu tin nhắn và hỏi Gemini…",
        "bot"
    );
    landingChatBusy = true;
    if (chatInput) chatInput.disabled = true;
    if (chatSendButton) chatSendButton.disabled = true;
    let saved = false;
    try {
        const session = await chatGet("/api/auth/me");
        if (session.user?.role !== "Customer") throw new Error("CUSTOMER_REQUIRED");
        let message;
        if (landingChatId) {
            try {
                message = await chatPost(`/api/chats/${landingChatId}/messages`, { content: text });
            } catch (error) {
                if (error.message !== "CHAT_NOT_FOUND" && error.message !== "CHAT_READ_ONLY") throw error;
                landingChatId = null;
            }
        }
        if (!message) message = await chatPost("/api/chats", { content: text });
        saved = true;
        rememberLandingChatId(message.id);
        if (message.assistantStatus !== "ready") throw new Error("AI_NOT_CONFIGURED");
        const answer = await chatPost(`/api/chats/${message.id}/messages/${message.messageId}/answer`, {
            language: isEnglishPage ? "en" : "vi"
        });
        const detail = await chatGet(`/api/chats/${message.id}`);
        const reply = detail.messages?.find(item => item.id === answer.messageId);
        if (!reply?.content) throw new Error("AI_INVALID_OUTPUT");
        showBotReply(pending, reply.content, reply.sources ?? [], message.id);
    } catch (error) {
        const messages = {
            UNAUTHENTICATED: isEnglishPage
                ? "Please sign in as a Customer to use Gemini chat."
                : "Vui lòng đăng nhập bằng tài khoản Khách hàng để dùng chat Gemini.",
            CUSTOMER_REQUIRED: isEnglishPage
                ? "Gemini chat on this page is available to Customer accounts."
                : "Chat Gemini trên trang này dành cho tài khoản Khách hàng.",
            AI_NOT_CONFIGURED: isEnglishPage
                ? "Your message was saved, but Gemini is not enabled on the backend. Start the server with -EnableAI -AIProvider gemini."
                : "Tin nhắn đã được lưu nhưng Gemini chưa được bật ở backend. Hãy chạy server với -EnableAI -AIProvider gemini.",
            AI_BUSY: isEnglishPage ? "Gemini is busy. Open Conversations and retry this message shortly." : "Gemini đang bận. Hãy mở Lịch sử trò chuyện và thử hỏi lại sau ít phút.",
            AI_RATE_LIMITED: isEnglishPage ? "Gemini has reached its request limit. Please retry later." : "Gemini đã đạt giới hạn yêu cầu. Vui lòng thử lại sau.",
            KNOWLEDGE_LIMIT: isEnglishPage ? "The published knowledge base is too large for this demo." : "Kho tri thức đã xuất bản vượt giới hạn của bản demo."
        };
        pending.textContent = messages[error.message] || (saved
            ? (isEnglishPage ? "Your message was saved, but Gemini could not respond. Open Conversations to retry without sending it again." : "Tin nhắn đã được lưu nhưng Gemini chưa phản hồi. Hãy mở Lịch sử trò chuyện để thử lại mà không gửi trùng.")
            : (isEnglishPage ? "Unable to start Gemini chat. Please sign in and try again." : "Chưa thể bắt đầu chat Gemini. Vui lòng đăng nhập và thử lại."));
        if (!saved && chatInput) chatInput.value = text;
    } finally {
        landingChatBusy = false;
        if (chatInput) chatInput.disabled = false;
        if (chatSendButton) chatSendButton.disabled = false;
        chatInput.value = "";
        chatInput?.focus();
    }
}


function sendQuestion(question) {

    if (!chatInput) return;

    chatInput.value = question;

    sendMessage();
}


function addMessage(text, type) {
    if (!chatBody) return;

    const message = document.createElement("div");

    message.className = `message ${type}`;

    message.textContent = text;

    chatBody.appendChild(message);

    chatBody.scrollTop = chatBody.scrollHeight;
    return message;
}


function showBotReply(message, text, sources, chatId) {
    message.replaceChildren(document.createTextNode(text));
    if (sources.length) {
        const details = document.createElement("details");
        const summary = document.createElement("summary");
        summary.textContent = isEnglishPage ? "Sources" : "Nguồn tham khảo";
        details.appendChild(summary);
        for (const source of sources) {
            const item = document.createElement("p");
            item.textContent = `${source.title} · KB-${source.documentId} / #${source.chunkId}`;
            details.appendChild(item);
        }
        message.appendChild(details);
    }
    const link = document.createElement("a");
    link.href = `${isEnglishPage ? "chat-en.html" : "chat-vi.html"}#${chatId}`;
    link.textContent = isEnglishPage ? "Open conversation" : "Mở lịch sử trò chuyện";
    message.appendChild(link);
    chatBody.scrollTop = chatBody.scrollHeight;
}


function toggleMenu() {

    const menu = document.querySelector(".menu");

    if (!menu) return;

    if (getComputedStyle(menu).display === "none") {

        menu.style.display = "flex";

        menu.style.position = "absolute";
        menu.style.top = "68px";
        menu.style.left = "0";
        menu.style.right = "0";

        menu.style.flexDirection = "column";

        menu.style.padding = "20px";

        menu.style.background = "rgba(255,255,255,0.97)";

        menu.style.boxShadow =
            "0 15px 30px rgba(0,50,100,0.1)";

    } else {

        menu.style.display = "none";
    }
}

function sendChatPreview() {
    const input = document.getElementById("chatInputPreview");
    if (!input || !chatBody) return;
    const message = input.value.trim();
    if (!message) return;
    openChat();
    sendMessage(message);
    input.value = "";
}

function localized(vi, en) {
    return document.documentElement.lang === "en" ? en : vi;
}

const previewInput = document.getElementById("chatInputPreview");
previewInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.isComposing) {
        event.preventDefault();
        sendChatPreview();
    }
});

/* =====================================================
   LOGIN
   ===================================================== */

/* =====================================================
   SHOW / HIDE PASSWORD
   ===================================================== */

function togglePassword(inputId, button) {

    const input = document.getElementById(inputId);

    if (!input) return;


    if (input.type === "password") {

        input.type = "text";

        button.textContent = "🙈";

    } else {

        input.type = "password";

        button.textContent = "👁";

    }
}


/* =====================================================
   OTP LOGIN
   ===================================================== */

function loginWithOTP() {
    if (typeof openOTPLogin === "function") openOTPLogin();
}
