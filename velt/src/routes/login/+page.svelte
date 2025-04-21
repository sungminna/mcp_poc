<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/stores'; // Import page store to read query params
    import { onMount } from 'svelte';

    let username = ''; // Changed from email to username
    let password = '';
    let errorMessage = '';
    let successMessage = ''; // For showing signup success
    let isLoading = false;
    let formElement: HTMLFormElement;

    // Removed emailRegex

    async function handleLogin(event: SubmitEvent) {
        event.preventDefault();
        if (!username || !password) { // Check username instead of email
            errorMessage = '사용자 이름과 비밀번호를 입력해주세요.';
            successMessage = ''; // Clear success message on new attempt
            return;
        }
        // Removed email validation

        errorMessage = '';
        successMessage = '';
        isLoading = true;

        try {
            const formData = new URLSearchParams();
            formData.append('username', username); // Use username directly
            formData.append('password', password);

            // Replace with your actual API endpoint if different
            const response = await fetch('/api/auth/token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData,
            });

            if (!response.ok) {
                let errorData = { detail: '로그인 실패. 사용자 이름 또는 비밀번호를 확인하세요.' }; // Updated default error
                try {
                  errorData = await response.json();
                } catch (jsonError) { /* Ignore */ }
                errorMessage = errorData.detail || `오류 발생: ${response.status}`;
                throw new Error(errorMessage);
            }

            const data = await response.json();

            if (data.access_token) {
                localStorage.setItem('authToken', data.access_token);
                await goto('/'); // Redirect to chat page
            } else {
                throw new Error('토큰이 수신되지 않았습니다.');
            }

        } catch (error: any) {
            console.error('Login failed:', error);
            errorMessage = error.message || '로그인 중 오류가 발생했습니다.';
        } finally {
            isLoading = false;
        }
    }

    onMount(() => {
        // Check for signup success message
        const signedUp = $page.url.searchParams.get('signedUp');
        if (signedUp) {
            successMessage = '회원가입이 완료되었습니다! 이제 로그인하세요.';
        }

        const firstInput = formElement.querySelector('input');
        firstInput?.focus();
    });

</script>

<div class="auth-page-container">
    <div class="auth-box">
        <header class="auth-header">
            로그인
        </header>

        {#if successMessage}
            <p class="success-message">{successMessage}</p>
        {/if}

        <form on:submit={handleLogin} bind:this={formElement} class="auth-form">
            <div class="form-group">
                <label for="username">사용자 이름</label>
                <input type="text" id="username" bind:value={username} required placeholder="사용자 이름 입력">
            </div>
            <div class="form-group">
                <label for="password">비밀번호</label>
                <input type="password" id="password" bind:value={password} required placeholder="비밀번호 입력">
            </div>

            {#if errorMessage}
                <p class="error-message">{errorMessage}</p>
            {/if}

            <button type="submit" class="submit-button" disabled={isLoading}>
                {#if isLoading}처리 중...{:else}로그인{/if}
            </button>
        </form>

        <div class="link-section">
            계정이 없으신가요? <a href="/signup">회원가입</a>
        </div>
    </div>
     <footer class="auth-footer">
        Velt Chat - 로그인
    </footer>
</div>

<style>
    :global(body) {
        background-color: #131316;
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
        margin-bottom: 50px; 
    }

    .auth-header {
        text-align: center;
        font-size: 1.6rem;
        font-weight: 600;
        color: #FFF;
        margin-bottom: 30px;
    }

     .success-message {
        color: #28a745;
        background-color: #1E1E1F;
        border: none;
        padding: 10px 15px;
        border-radius: 6px;
        font-size: 0.9rem;
        text-align: center;
        margin-bottom: 20px;
    }

    .auth-form {
        display: flex;
        flex-direction: column;
        gap: 20px;
    }

    .form-group {
        display: flex;
        flex-direction: column;
    }

    .form-group label {
        margin-bottom: 6px;
        font-size: 0.85rem;
        font-weight: 500;
        color: #606770;
    }

    .form-group input {
        padding: 12px 16px;
        border: 1px solid #333;
        border-radius: 6px;
        font-size: 1rem;
        background-color: #232328;
        color: #EEE;
        transition: border-color 0.2s ease-in-out, box-shadow 0 0 0 0;
    }

    .form-group input::placeholder {
        color: #888;
    }

    .form-group input:focus {
        outline: none;
        border-color: #FFD66E;
        box-shadow: none;
    }

    .submit-button {
        padding: 14px 20px;
        border: none;
        background-color: #FFD66E;
        color: #131316;
        border-radius: 6px;
        cursor: pointer;
        font-size: 1.05rem;
        font-weight: 600;
        transition: background-color 0.2s ease-in-out;
        margin-top: 10px;
        width: 100%;
    }

    .submit-button:hover:not(:disabled) {
        background-color: #e6c850;
    }

    .submit-button:disabled {
        background-color: #333;
        cursor: not-allowed;
    }

    .error-message {
        color: #fa383e;
        font-size: 0.85rem;
        text-align: center;
        margin-top: 5px;
        margin-bottom: 0;
        font-weight: 500;
    }

    .link-section {
        text-align: center;
        margin-top: 30px;
        padding-top: 20px;
        border-top: 1px solid #333;
        font-size: 0.95rem;
        color: #AAA;
    }

    .link-section a {
        color: #FFD66E;
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