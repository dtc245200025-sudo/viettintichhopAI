const chatWindow = document.getElementById("chatWindow");
const chatBody = document.getElementById("chatBody");
const chatInput = document.getElementById("chatInput");


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


function sendMessage(mainScreenMess) {
    if (!chatBody) return;
    const text = (typeof mainScreenMess === "string" ? mainScreenMess : chatInput?.value ?? "").trim();
    if (!text) return;
    addMessage(text, "user");
    if (typeof mainScreenMess !== "string" && chatInput) chatInput.value = "";

    setTimeout(() => {

        const response = getAIResponse(text);

        addMessage(response, "bot");

    }, 700);
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
}


function getAIResponse(text) {

    const lowerText = text.toLowerCase();

    const isEnglish =
        document.documentElement.lang === "en";


    if (
        lowerText.includes("lãi suất") ||
        lowerText.includes("interest")
    ) {

        return isEnglish
            ? "I can help you check VietinBank's deposit interest rates. For the latest official information, please select the deposit service or contact a customer service agent."
            : "Tôi có thể hỗ trợ bạn tra cứu thông tin lãi suất tiền gửi VietinBank. Để có thông tin mới nhất, bạn có thể chọn dịch vụ Tiền gửi hoặc kết nối với tổng đài viên.";
    }


    if (
        lowerText.includes("atm") ||
        lowerText.includes("chi nhánh") ||
        lowerText.includes("branch")
    ) {

        return isEnglish
            ? "I can help you find a VietinBank ATM or branch near you."
            : "Tôi có thể hỗ trợ bạn tìm ATM hoặc chi nhánh VietinBank gần bạn.";
    }


    if (
        lowerText.includes("thẻ") ||
        lowerText.includes("card")
    ) {

        return isEnglish
            ? "I can help with card-related questions such as card opening, card locking and transaction issues."
            : "Tôi có thể hỗ trợ các vấn đề về thẻ như mở thẻ, khóa thẻ và xử lý sự cố giao dịch.";
    }


    if (
        lowerText.includes("ipay") ||
        lowerText.includes("e-fast")
    ) {

        return isEnglish
            ? "I can guide you through common VietinBank iPay issues and usage instructions."
            : "Tôi có thể hướng dẫn bạn sử dụng VietinBank iPay và xử lý một số sự cố thường gặp.";
    }


    return isEnglish
        ? "I understand your request. Let me analyze it and find the most appropriate information. If I cannot resolve the issue, I can connect you with a customer service agent."
        : "Tôi đã tiếp nhận yêu cầu của bạn. VietinCare AI sẽ phân tích nội dung và tìm thông tin phù hợp. Nếu AI không thể xử lý, tôi có thể chuyển bạn đến tổng đài viên để được hỗ trợ trực tiếp.";
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

    alert(
        localized("Chức năng đăng nhập OTP chưa được tích hợp.", "OTP sign-in is not available in this demo.")
    );
}