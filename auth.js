const authEnglish = document.documentElement.lang === 'en';
const authText = (vi, en) => authEnglish ? en : vi;
const errors = {
  INVALID_INPUT: ['Kiểm tra email, số điện thoại, họ tên, mật khẩu 8–128 ký tự và điều khoản.', 'Check your email, phone, name, 8–128 character password and terms.'],
  INVALID_CREDENTIALS: ['Email hoặc mật khẩu không đúng, hoặc tài khoản chưa được kích hoạt.', 'Incorrect email or password, or inactive account.'],
  EMAIL_EXISTS: ['Email đã được sử dụng.', 'This email is already registered.'],
  RATE_LIMITED: ['Bạn đã thử quá nhiều lần. Vui lòng thử lại sau 15 phút.', 'Too many attempts. Please try again in 15 minutes.'],
  UNAUTHENTICATED: ['Phiên đã hết hạn. Vui lòng đăng nhập lại.', 'Your session expired. Please sign in again.'],
  ORIGIN_REJECTED: ['Hãy mở trang bằng địa chỉ APP_ORIGIN của backend.', 'Open the page using the backend APP_ORIGIN address.']
};
function authStatus(form, message, success = false) {
  let status = form.querySelector('[role="status"]');
  if (!status) { status = document.createElement('p'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite'); form.prepend(status); }
  status.textContent = message;
  status.style.color = success ? '#087443' : '#b42318';
}
async function authRequest(path, body) {
  const response = await fetch(path, { method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-Vietincare-Request': '1' }, body: JSON.stringify(body) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'SERVICE_UNAVAILABLE');
  return data;
}
async function submitAuth(event, type) {
  event.preventDefault();
  const form = event.currentTarget;
  if (form.dataset.submitting) return;
  if (!form.reportValidity()) return;
  if (location.protocol === 'file:') { authStatus(form, authText('Hãy chạy npm start và mở http://localhost:3000.', 'Run npm start and open http://localhost:3000.')); return; }
  const password = document.getElementById(type === 'login' ? 'loginPassword' : 'registerPassword').value;
  if (type === 'register' && password !== document.getElementById('confirmPassword').value) { authStatus(form, authText('Mật khẩu xác nhận không khớp.', 'Passwords do not match.')); return; }
  const payload = { email: document.getElementById(type === 'login' ? 'loginEmail' : 'registerEmail').value.trim(), password };
  if (type === 'register') Object.assign(payload, { fullName: document.getElementById('fullName').value.trim(), phone: document.getElementById('phone').value.trim(), acceptTerms: form.querySelector('.terms input').checked });
  const button = form.querySelector('[type="submit"]');
  form.dataset.submitting = 'true'; button.disabled = true;
  authStatus(form, authText('Đang xử lý…', 'Please wait…'), true);
  try {
    await authRequest(`/api/auth/${type}`, payload);
    form.reset();
    location.assign(type === 'login' ? `account-${authEnglish ? 'en' : 'vi'}.html` : `login-${authEnglish ? 'en' : 'vi'}.html?registered=1`);
  } catch(e) {
    const pair = errors[e.message] || ['Không kết nối được dịch vụ. Vui lòng thử lại.', 'Service unavailable. Please try again.'];
    authStatus(form, pair[authEnglish ? 1 : 0]);
  } finally { delete form.dataset.submitting; button.disabled = false; }
}
function login(event) { return submitAuth(event, 'login'); }
function register(event) { return submitAuth(event, 'register'); }
if (new URLSearchParams(location.search).get('registered') === '1') {
  const form = document.querySelector('form');
  if (form) authStatus(form, authText('Đã tạo tài khoản. Bạn có thể đăng nhập.', 'Account created. You can sign in now.'), true);
}
