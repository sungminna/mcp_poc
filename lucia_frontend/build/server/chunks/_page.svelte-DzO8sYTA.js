import { p as push, K as attr, n as pop } from './exports-BKcDwPi0.js';
import './client-B_u6nehf.js';

function _page($$payload, $$props) {
  push();
  let username = "";
  let password = "";
  let isLoading = false;
  $$payload.out += `<div class="auth-page-container svelte-193izyl"><div class="auth-box svelte-193izyl"><header class="auth-header svelte-193izyl">로그인</header> `;
  {
    $$payload.out += "<!--[!-->";
  }
  $$payload.out += `<!--]--> <form class="auth-form svelte-193izyl"><div class="form-group svelte-193izyl"><label for="username" class="svelte-193izyl">사용자 이름</label> <input type="text" id="username"${attr("value", username)} required placeholder="사용자 이름 입력" class="svelte-193izyl"></div> <div class="form-group svelte-193izyl"><label for="password" class="svelte-193izyl">비밀번호</label> <input type="password" id="password"${attr("value", password)} required placeholder="비밀번호 입력" class="svelte-193izyl"></div> `;
  {
    $$payload.out += "<!--[!-->";
  }
  $$payload.out += `<!--]--> <button type="submit" class="submit-button svelte-193izyl"${attr("disabled", isLoading, true)}>`;
  {
    $$payload.out += "<!--[!-->";
    $$payload.out += `로그인`;
  }
  $$payload.out += `<!--]--></button></form> <div class="link-section svelte-193izyl">계정이 없으신가요? <a href="/signup" class="svelte-193izyl">회원가입</a></div></div> <footer class="auth-footer svelte-193izyl">Velt Chat - 로그인</footer></div>`;
  pop();
}

export { _page as default };
//# sourceMappingURL=_page.svelte-DzO8sYTA.js.map
