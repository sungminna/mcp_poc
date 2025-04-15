<script lang="ts">
    import ChatMessage from '$lib/components/ChatMessage.svelte';
    import { onMount, tick } from 'svelte';
    import { slide } from 'svelte/transition';
    import { goto } from '$app/navigation';

    const sendIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z" /></svg>`;

    type Message = {
        id: number;
        text: string;
        sender: 'user' | 'ai';
    };

    let messages: Message[] = [];
    let newMessageText: string = '';
    let loadingAIResponse = false;
    let textareaElement: HTMLTextAreaElement;
    let chatWrapperElement: HTMLDivElement;
    let isAuthenticated = false;

    async function getAIResponse(inputText: string): Promise<string> {
        loadingAIResponse = true;
        const token = localStorage.getItem('authToken');
        let aiResponse = '오류: AI 응답을 가져올 수 없습니다.'; // Default error response

        // If not authenticated, provide a specific message or handle as needed
        if (!token) {
             loadingAIResponse = false;
            // Option 1: Return an error message
            // return '오류: 채팅 기능을 사용하려면 로그인이 필요합니다.';
            // Option 2: Redirect to login (more user-friendly)
            await goto('/login?redirectTo=/'); // Add redirectTo query param if needed
            return ''; // Prevent further processing
        }

        try {
            // Replace '/api/chat/' with your actual FastAPI chat endpoint
            const response = await fetch('/api/chat/', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // Include the JWT token in the Authorization header
                    'Authorization': `Bearer ${token}`,
                },
                // Send the user message in the expected format
                body: JSON.stringify({ user_message: inputText }), 
            });

            if (response.status === 401) {
                // Handle unauthorized access (e.g., token expired)
                localStorage.removeItem('authToken'); // Clear invalid token
                isAuthenticated = false;
                await goto('/login?sessionExpired=true'); // Redirect to login with a message
                return ''; // Stop processing
            }

            if (!response.ok) {
                // Handle other API errors
                let errorData = { detail: 'API 오류가 발생했습니다.' };
                try {
                  errorData = await response.json();
                } catch (jsonError) { /* Ignore if response is not JSON */ }
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Extract the AI response from the expected field ('ai_response')
            if (data && data.ai_response) {
                 aiResponse = data.ai_response;
            } else {
                console.error('Unexpected API response format:', data);
                throw new Error('수신된 데이터 형식이 올바르지 않습니다.');
            }

        } catch (error: any) {
            console.error('Failed to get AI response:', error);
            // Use the error message caught or a default one
            aiResponse = error.message || 'AI 응답 처리 중 오류 발생'; 
        } finally {
            loadingAIResponse = false;
        }
        return aiResponse;
    }

    // Function to scroll the chat wrapper to the bottom smoothly
    async function scrollToBottom() {
        await tick(); // Wait for DOM updates after message added
        if (chatWrapperElement) {
            // Smooth scroll to bottom
            chatWrapperElement.scrollTo({
                top: chatWrapperElement.scrollHeight,
                behavior: 'smooth'
            });
            
            // Also set a timeout to ensure scroll happens after animation
            setTimeout(() => {
                chatWrapperElement.scrollTo({
                    top: chatWrapperElement.scrollHeight,
                    behavior: 'smooth'
                });
            }, 300);
        }
    }

    async function sendMessage() {
        const text = newMessageText.trim();
        if (!text || loadingAIResponse) return;

        // Add user message and scroll
        messages = [...messages, { id: Date.now(), text, sender: 'user' }];
        await tick(); // Ensure DOM updates before scrolling
        scrollToBottom(); // <-- Scroll after user message

        newMessageText = '';
        await tick();
        adjustTextareaHeight();

        // Get AI response, add it, and scroll
        const aiResponseText = await getAIResponse(text); // This now calls the real API
        // Only add AI message if the response is not empty (e.g., not redirected)
        if (aiResponseText) {
            messages = [...messages, { id: Date.now() + 1, text: aiResponseText, sender: 'ai' }];
            await tick(); // Wait for DOM to update with the new message
            
            // Give extra time for transition animation to start
            setTimeout(() => {
                scrollToBottom(); // <-- Scroll after AI message
            }, 100);
        }
    }

    function adjustTextareaHeight() {
        if (!textareaElement) return;

        const minHeight = 40;
        const maxHeight = 120;

        textareaElement.style.height = 'auto';

        const requiredHeight = Math.max(minHeight, Math.min(textareaElement.scrollHeight, maxHeight));

        textareaElement.style.height = `${requiredHeight}px`;
    }

    async function handleLogout() {
        localStorage.removeItem('authToken');
        isAuthenticated = false;
        await goto('/login');
    }

    onMount(() => {
        const token = localStorage.getItem('authToken');
        isAuthenticated = !!token;

        messages = [
            { id: 1, text: 'ㅎㅇㅎㅇ! 궁금한거 물어봐줘? 😊', sender: 'ai' },
        ];
        adjustTextareaHeight();
        scrollToBottom(); // <-- Scroll on initial load
    });

</script>

<div class="chat-page-container">
    <header class="chat-header">
        <span class="header-title">Velt Chat</span>
        {#if isAuthenticated}
            <button on:click={handleLogout} class="auth-button logout-button">로그아웃</button>
        {:else}
            <div class="auth-buttons">
                <a href="/login" class="auth-button login-button">로그인</a>
                <a href="/signup" class="auth-button signup-button">회원가입</a>
            </div>
        {/if}
    </header>

    <div class="chat-messages-wrapper" bind:this={chatWrapperElement}>
        <div class="chat-messages">
            {#each messages as message (message.id)}
                <div transition:slide={{ duration: 300 }}>
                     <ChatMessage {message} />
                </div>
            {/each}
            {#if loadingAIResponse}
                <div class="loading-indicator" transition:slide={{ duration: 300 }}>
                    <ChatMessage message={{ id: -1, text: '...', sender: 'ai' }} isLoading={true}/>
                </div>
            {/if}
        </div>
    </div>

    <div class="chat-input-area">
        <textarea
            bind:this={textareaElement}
            bind:value={newMessageText}
            placeholder="무엇이든 물어보세요"
            on:input={adjustTextareaHeight}
            on:keydown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            }}
            rows="1"
        />
        <button
            class="send-button"
            on:click={sendMessage}
            disabled={!newMessageText.trim() || loadingAIResponse}
            aria-label="Send message"
        >
            {@html sendIcon}
        </button>
    </div>
    <footer class="chat-footer">
        ChatGPT는 실수를 할 수 있습니다. 중요한 정보는 재차 확인하세요.
    </footer>
</div>

<style>
    .chat-page-container {
        display: flex;
        flex-direction: column;
        height: 100vh; /* Full viewport height */
        width: 100%; /* Full width */
        margin: 0; /* Remove margin */
        background-color: #ffffff; /* White background like image */
        overflow: hidden; /* Prevent content spill */
    }

    .chat-header {
        padding: 10px 20px;
        display: flex; /* Use flexbox for layout */
        justify-content: space-between; /* Space out title and buttons */
        align-items: center; /* Vertically align items */
        font-size: 1rem;
        color: #333; /* Darker header text */
        border-bottom: 1px solid #e5e5e5; /* Slightly darker border */
        background-color: #ffffff;
        flex-shrink: 0; /* Prevent header from shrinking */
        position: relative; /* Needed for potential absolute positioning inside */
    }

    .header-title {
        font-weight: 600;
    }

    .auth-buttons {
        display: flex;
        gap: 10px; /* Space between buttons */
    }

    .auth-button {
        padding: 6px 12px;
        border: 1px solid transparent; /* Base border */
        border-radius: 6px;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out, color 0.2s ease-in-out;
    }

    .login-button {
        background-color: #e7f3ff; /* Light blue background */
        color: #007bff; /* Blue text */
        border-color: #cfe2ff; /* Subtle blue border */
    }
    .login-button:hover {
        background-color: #cfe2ff;
    }

    .signup-button {
        background-color: #007bff; /* Blue background */
        color: white;
    }
    .signup-button:hover {
         background-color: #0056b3;
    }

    .logout-button {
        background-color: #f8d7da; /* Light red background */
        color: #721c24; /* Dark red text */
        border-color: #f5c6cb; /* Subtle red border */
    }
    .logout-button:hover {
        background-color: #f5c6cb;
    }

    /* Added wrapper for messages padding */
    .chat-messages-wrapper {
        flex-grow: 1;
        overflow-y: auto;
        padding: 20px 20px 0 20px; /* Add padding top/sides, no bottom */
    }

    .chat-messages {
        display: flex;
        flex-direction: column;
        gap: 18px; /* Slightly increased gap */
        height: 100%; /* Ensure it tries to fill wrapper */
        padding-bottom: 20px; /* Padding at the very bottom */
    }

    .chat-input-area {
        display: flex;
        align-items: flex-end; /* Align items to bottom for multi-line */
        padding: 12px 15px; /* Adjusted padding */
        border-top: 1px solid #f0f0f0; /* Subtle border */
        background-color: #ffffff; /* White background */
        flex-shrink: 0; /* Prevent input area from shrinking */
    }

    textarea {
        flex-grow: 1;
        padding: 10px 15px;
        border: 1px solid #e0e0e0; /* Lighter border */
        border-radius: 18px; /* More rounded */
        resize: none;
        min-height: 40px; /* Adjusted minimum height */
        max-height: 120px;
        line-height: 1.4;
        font-size: 0.95rem;
        margin-right: 10px;
        overflow-y: hidden; /* Hide vertical scrollbar */
        background-color: #f7f7f7; /* Light gray background for textarea */
        transition: border-color 0.2s ease-in-out, background-color 0.2s ease-in-out;
        box-sizing: border-box; /* Include padding/border in height */
    }

    textarea:focus {
        outline: none;
        border-color: #c0c0c0;
        background-color: #ffffff;
        box-shadow: none; /* Remove default blue shadow */
    }

    /* Send button styling */
    .send-button {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0; /* Remove padding, control size with width/height */
        border: none;
        background-color: #e0e0e0; /* Default gray background */
        color: #8e8e8e; /* Icon color */
        border-radius: 50%; /* Make it circular */
        width: 38px; /* Fixed size */
        height: 38px; /* Fixed size */
        cursor: pointer;
        transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out;
        flex-shrink: 0; /* Prevent shrinking */
    }

    .send-button:not(:disabled) {
        background-color: #000000; /* Black background when active */
        color: #ffffff; /* White icon */
    }

    .send-button:disabled {
        background-color: #f0f0f0; /* Lighter gray when disabled */
        color: #b0b0b0;
        cursor: not-allowed;
    }

    .send-button svg {
        width: 20px; /* Icon size */
        height: 20px;
    }

    .chat-footer {
        padding: 8px 20px;
        text-align: center;
        font-size: 0.7rem;
        color: #b0b0b0; /* Lighter gray */
        background-color: #ffffff;
        flex-shrink: 0; /* Prevent footer from shrinking */
        border-top: 1px solid #f0f0f0; /* Subtle border */
    }

    .loading-indicator {
      opacity: 0.7;
      align-self: flex-start; /* Align loading indicator like AI messages */
      margin-right: auto; /* Push to the left */
    }

</style>
