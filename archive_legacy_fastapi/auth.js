const authEnglish = document.documentElement.lang === 'en';
const authText = (vi, en) => authEnglish ? en : vi;
const errors = {
  INVALID_INPUT: ['Kiểm tra email, số điện thoại, họ tên, mật khẩu 8–128 ký tự và điều khoản.', 'Check your email, phone, name, 8–128 character password and terms.'],
  INVALID_CREDENTIALS: ['Email hoặc mật khẩu không đúng, hoặc tài khoản chưa được kích hoạt.', 'Incorrect email or password, or inactive account.'],
  EMAIL_EXISTS: ['Email đã được sử dụng.', 'This email is already registered.'],
  RATE_LIMITED: ['Bạn đã thử quá nhiều lần. Vui lòng thử lại sau 15 phút.', 'Too many attempts. Please try again in 15 minutes.'],
  OTP_INVALID: ['Mã OTP không đúng hoặc đã hết hạn. Vui lòng yêu cầu mã mới.', 'The code is incorrect or expired. Request a new code.'],
  OTP_UNAVAILABLE: ['Dịch vụ gửi SMS chưa được cấu hình hoặc đang gián đoạn.', 'SMS delivery is not configured or is temporarily unavailable.'],
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
function openOTPLogin() {
  const button = document.querySelector('.otp-button');
  if (!button) return;
  let panel = document.getElementById('otpLoginPanel');
  if (panel) { panel.hidden = !panel.hidden; if (!panel.hidden) panel.querySelector('#otpPhone').focus(); return; }

  panel = document.createElement('section');
  panel.id = 'otpLoginPanel';
  panel.className = 'otp-panel';
  panel.setAttribute('aria-label', authText('Đăng nhập bằng mã OTP', 'Sign in with OTP'));
  const heading = document.createElement('h3');
  heading.textContent = authText('Đăng nhập bằng số điện thoại', 'Sign in with your phone');
  const description = document.createElement('p');
  description.textContent = authText('Nhập số điện thoại đã đăng ký để nhận mã xác minh.', 'Enter your registered phone number to receive a verification code.');
  const phoneGroup = document.createElement('div');
  phoneGroup.className = 'form-group';
  const phoneLabel = document.createElement('label');
  phoneLabel.htmlFor = 'otpPhone';
  phoneLabel.textContent = authText('Số điện thoại', 'Phone number');
  const phoneInput = document.createElement('input');
  phoneInput.id = 'otpPhone'; phoneInput.type = 'tel'; phoneInput.autocomplete = 'tel';
  phoneInput.inputMode = 'tel'; phoneInput.placeholder = '+84 9xx xxx xxx'; phoneInput.required = true;
  phoneGroup.append(phoneLabel, phoneInput);
  const requestButton = document.createElement('button');
  requestButton.type = 'button'; requestButton.className = 'otp-action';
  requestButton.textContent = authText('Gửi mã OTP', 'Send OTP');
  const codeGroup = document.createElement('div');
  codeGroup.className = 'form-group'; codeGroup.hidden = true;
  const codeLabel = document.createElement('label');
  codeLabel.htmlFor = 'otpCode'; codeLabel.textContent = authText('Mã xác minh', 'Verification code');
  const codeInput = document.createElement('input');
  codeInput.id = 'otpCode'; codeInput.type = 'text'; codeInput.inputMode = 'numeric';
  codeInput.autocomplete = 'one-time-code'; codeInput.pattern = '[0-9]{6}'; codeInput.maxLength = 6;
  codeInput.placeholder = '000000'; codeInput.required = true;
  codeGroup.append(codeLabel, codeInput);
  const verifyButton = document.createElement('button');
  verifyButton.type = 'button'; verifyButton.className = 'auth-submit otp-verify';
  verifyButton.textContent = authText('Xác minh và đăng nhập', 'Verify and sign in');
  verifyButton.hidden = true;
  const status = document.createElement('p');
  status.className = 'otp-status'; status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
  panel.append(heading, description, phoneGroup, requestButton, codeGroup, verifyButton, status);
  button.insertAdjacentElement('afterend', panel);

  requestButton.addEventListener('click', async () => {
    if (!phoneInput.reportValidity() || panel.dataset.submitting) return;
    panel.dataset.submitting = 'true'; requestButton.disabled = true;
    status.textContent = authText('Đang gửi mã…', 'Sending code…');
    try {
      await authRequest('/api/auth/otp/request', { phone: phoneInput.value.trim() });
      codeGroup.hidden = false; verifyButton.hidden = false;
      status.textContent = authText('Nếu số điện thoại thuộc tài khoản, mã xác minh đã được gửi.', 'If the number belongs to an account, a verification code has been sent.');
      codeInput.focus();
    } catch (error) {
      const pair = errors[error.message] || ['Không gửi được mã. Vui lòng thử lại sau.', 'Could not send the code. Please try again later.'];
      status.textContent = pair[authEnglish ? 1 : 0];
    } finally { delete panel.dataset.submitting; requestButton.disabled = false; }
  });

  verifyButton.addEventListener('click', async () => {
    if (!codeInput.reportValidity() || panel.dataset.submitting) return;
    panel.dataset.submitting = 'true'; verifyButton.disabled = true;
    status.textContent = authText('Đang xác minh…', 'Verifying…');
    try {
      await authRequest('/api/auth/otp/verify', { phone: phoneInput.value.trim(), code: codeInput.value.trim() });
      location.assign(`account-${authEnglish ? 'en' : 'vi'}.html`);
    } catch (error) {
      const pair = errors[error.message] || ['Không xác minh được mã. Vui lòng thử lại.', 'Could not verify the code. Please try again.'];
      status.textContent = pair[authEnglish ? 1 : 0];
    } finally { delete panel.dataset.submitting; verifyButton.disabled = false; }
  });
  phoneInput.focus();
}
async function submitAuth(event, type) {
  event.preventDefault();
  const form = event.currentTarget;
  if (form.dataset.submitting) return;
  if (!form.reportValidity()) return;
  if (location.protocol === 'file:') { authStatus(form, authText('Hãy chạy scripts/start-local.ps1 và mở http://localhost:3000.', 'Run scripts/start-local.ps1 and open http://localhost:3000.')); return; }
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
