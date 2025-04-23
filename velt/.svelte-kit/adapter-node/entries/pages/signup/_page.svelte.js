import { y as attr, n as pop, p as push } from "../../../chunks/index.js";
import "../../../chunks/client.js";
function _page($$payload, $$props) {
  push();
  let email = "";
  let username = "";
  let password = "";
  let confirmPassword = "";
  let isLoading = false;
  $$payload.out += `<div class="auth-page-container svelte-1lp09ig"><div class="auth-box svelte-1lp09ig"><header class="auth-header svelte-1lp09ig">회원가입</header> <form class="auth-form svelte-1lp09ig"><div class="form-group svelte-1lp09ig"><label for="email" class="svelte-1lp09ig">이메일</label> <input type="email" id="email"${attr("value", email)} required placeholder="your@email.com" class="svelte-1lp09ig"></div> <div class="form-group svelte-1lp09ig"><label for="username" class="svelte-1lp09ig">사용자 이름</label> <input type="text" id="username"${attr("value", username)} required placeholder="공백 없이 입력" class="svelte-1lp09ig"></div> <div class="form-group svelte-1lp09ig"><label for="password" class="svelte-1lp09ig">비밀번호</label> <input type="password" id="password"${attr("value", password)} required placeholder="6자 이상" class="svelte-1lp09ig"></div> <div class="form-group svelte-1lp09ig"><label for="confirmPassword" class="svelte-1lp09ig">비밀번호 확인</label> <input type="password" id="confirmPassword"${attr("value", confirmPassword)} required placeholder="비밀번호 다시 입력" class="svelte-1lp09ig"></div> `;
  {
    $$payload.out += "<!--[!-->";
  }
  $$payload.out += `<!--]--> <button type="submit" class="submit-button svelte-1lp09ig"${attr("disabled", isLoading, true)}>`;
  {
    $$payload.out += "<!--[!-->";
    $$payload.out += `가입하기`;
  }
  $$payload.out += `<!--]--></button></form> <div class="link-section svelte-1lp09ig">이미 계정이 있으신가요? <a href="/login" class="svelte-1lp09ig">로그인</a></div></div> <footer class="auth-footer svelte-1lp09ig">Velt Chat - 계정 생성</footer></div>`;
  pop();
}
export {
  _page as default
};
