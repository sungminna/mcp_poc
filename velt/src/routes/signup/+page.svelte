<script lang="ts">
    import { goto } from '$app/navigation';
    import { onMount } from 'svelte';

    let email = '';
    let username = '';
    let password = '';
    let confirmPassword = '';
    let errorMessage = '';
    let isLoading = false;
    let formElement: HTMLFormElement;

    // Basic email validation regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    async function handleSignup(event: SubmitEvent) {
        event.preventDefault();
        if (!email || !username || !password || !confirmPassword) {
            errorMessage = '모든 필드를 입력해주세요.';
            return;
        }
        if (username.includes(' ')) {
            errorMessage = '사용자 이름에는 공백을 포함할 수 없습니다.';
            return;
        }
        if (!emailRegex.test(email)) {
            errorMessage = '유효한 이메일 주소를 입력해주세요.';
            return;
        }
        if (password !== confirmPassword) {
            errorMessage = '비밀번호가 일치하지 않습니다.';
            return;
        }
        if (password.length < 6) { // Basic password length check
            errorMessage = '비밀번호는 6자 이상이어야 합니다.';
            return;
        }

        errorMessage = '';
        isLoading = true;

        try {
            // Replace with your actual API endpoint if different
            const response = await fetch('/api/users/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, username, password }),
            });

            if (!response.ok) {
                let errorData = { detail: '알 수 없는 오류가 발생했습니다.' };
                try {
                  errorData = await response.json();
                } catch (jsonError) {
                  // Ignore if response is not JSON
                }
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            // Handle successful signup (redirect to login)
            await goto('/login?signedUp=true'); // Add query param for potential success message on login page

        } catch (error: any) {
            console.error('Signup failed:', error);
            errorMessage = error.message || '회원가입 중 오류가 발생했습니다.';
        } finally {
            isLoading = false;
        }
    }

    onMount(() => {
      // Optional: focus the first input on mount
      const firstInput = formElement.querySelector('input');
      firstInput?.focus();
    });

</script>

<div class="auth-page-container">
    <div class="auth-box">
        <header class="auth-header">
            회원가입
        </header>

        <form on:submit={handleSignup} bind:this={formElement} class="auth-form">
            <div class="form-group">
                <label for="email">이메일</label>
                <input type="email" id="email" bind:value={email} required placeholder="your@email.com">
            </div>
            <div class="form-group">
                <label for="username">사용자 이름</label>
                <input type="text" id="username" bind:value={username} required placeholder="공백 없이 입력">
            </div>
            <div class="form-group">
                <label for="password">비밀번호</label>
                <input type="password" id="password" bind:value={password} required placeholder="6자 이상">
            </div>
            <div class="form-group">
                <label for="confirmPassword">비밀번호 확인</label>
                <input type="password" id="confirmPassword" bind:value={confirmPassword} required placeholder="비밀번호 다시 입력">
            </div>

            {#if errorMessage}
                <p class="error-message">{errorMessage}</p>
            {/if}

            <button type="submit" class="submit-button" disabled={isLoading}>
                {#if isLoading}처리 중...{:else}가입하기{/if}
            </button>
        </form>

        <div class="link-section">
            이미 계정이 있으신가요? <a href="/login">로그인</a>
        </div>
    </div>
     <footer class="auth-footer">
        Velt Chat - 계정 생성
    </footer>
</div>

<style>
    :global(body) { /* Apply to body for full page background */
        background-color: #131316; /* Dark background */
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    }

    .auth-page-container {
        display: flex;
        flex-direction: column;
        min-height: 100vh;
        width: 100%;
        justify-content: center;
        align-items: center;
        padding: 20px;
        box-sizing: border-box;
        background-color: #131316;
    }

    .auth-box {
      width: 100%;
      max-width: 400px;
      background-color: #1E1E1F;
      padding: 35px 40px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
      margin-bottom: 50px; /* Space before footer */
    }

    .auth-header {
        text-align: center;
        font-size: 1.6rem; /* Larger header */
        font-weight: 600;
        color: #FFF;
        margin-bottom: 30px; /* Space below header */
    }

    .auth-form {
        display: flex;
        flex-direction: column;
        gap: 20px; /* Increased gap */
    }

    .form-group {
        display: flex;
        flex-direction: column;
    }

    .form-group label {
        margin-bottom: 6px;
        font-size: 0.85rem; /* Smaller label */
        font-weight: 500;
        color: #606770; /* Grayish label text */
    }

    .form-group input {
        padding: 12px 16px;
        border: 1px solid #333;
        background-color: #232328;
        color: #EEE;
        border-radius: 6px;
        font-size: 1rem;
        transition: border-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }

    .form-group input::placeholder {
        color: #888;
    }

    .form-group input:focus {
        outline: none;
        border-color: #3BD66A;
        box-shadow: none;
    }

    .submit-button {
        padding: 14px 20px; /* Match input padding */
        border: none;
        background-color: #3BD66A;
        color: #131316;
        border-radius: 6px;
        cursor: pointer;
        font-size: 1.05rem; /* Slightly larger font */
        font-weight: 600;
        transition: background-color 0.2s ease-in-out;
        margin-top: 10px; /* Space above button */
        width: 100%; /* Full width */
    }

    .submit-button:hover {
        background-color: #2AA05A;
    }

    .submit-button:disabled {
        background-color: #333;
        cursor: not-allowed;
    }

    .error-message {
        color: #fa383e; /* Brighter red for errors */
        font-size: 0.85rem;
        text-align: center;
        margin-top: 5px;
        margin-bottom: 0;
        font-weight: 500;
    }

    .link-section {
        text-align: center;
        margin-top: 30px; /* More space */
        padding-top: 20px; /* Space above link */
        border-top: 1px solid #333;
        font-size: 0.95rem;
        color: #AAA;
    }

    .link-section a {
        color: #3BD66A;
        text-decoration: none;
        font-weight: 500;
    }

    .link-section a:hover {
        text-decoration: underline;
    }

    .auth-footer {
       width: 100%;
       padding: 15px 20px;
       text-align: center;
       font-size: 0.8rem;
       color: #888;
       background-color: #1E1E1F;
       margin-top: auto;
    }
</style> 