<script lang="ts">
    import ChatMessage from '$lib/components/ChatMessage.svelte';
    import { onMount, afterUpdate, tick } from 'svelte';
    import { slide } from 'svelte/transition';
    import { goto } from '$app/navigation';

    const sendIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z" /></svg>`;

    type Message = {
        id: number;
        text?: string;
        content?: string;
        sender: 'user' | 'ai';
        timestamp: string;
    };
    type Session = { id: number; created_at: string };

    let sessions: Session[] = [];
    let selectedSessionId: number | null = null;
    let messages: Message[] = [];
    let newMessageText: string = '';
    let loadingAIResponse = false;
    let textareaElement: HTMLTextAreaElement;
    let chatWrapperElement: HTMLDivElement;
    let isAuthenticated = false;
    let errorMessage: string = '';
    let sessionsLoading: boolean = false;
    let messagesLoading: boolean = false;
    let groupedMessages: Array<{ type: 'date'; date: string } | { type: 'message'; message: Message }> = [];

    // After each update, if loading, scroll down so the loading bubble is visible
    afterUpdate(() => {
        if (loadingAIResponse) scrollToBottom();
    });

    async function fetchSessions() {
        sessionsLoading = true;
        errorMessage = '';
        try {
            const token = localStorage.getItem('authToken');
            const res = await fetch('/api/chat/sessions', { headers: { 'Authorization': `Bearer ${token}` } });
            if (!res.ok) throw new Error('세션 목록을 가져오는데 실패했습니다.');
            sessions = await res.json();
        } catch (err: any) {
            errorMessage = err.message;
        } finally {
            sessionsLoading = false;
        }
    }

    async function fetchMessages(sessionId: number) {
        messagesLoading = true;
        errorMessage = '';
        try {
            const token = localStorage.getItem('authToken');
            const res = await fetch(`/api/chat/${sessionId}/messages`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (!res.ok) throw new Error('메시지 목록을 가져오는데 실패했습니다.');
            const data = await res.json();
            messages = data.map((m: any) => ({
                id: m.id,
                text: m.content,
                content: m.content,
                sender: m.sender === 'human' ? 'user' : 'ai',
                timestamp: m.created_at
            }));
        } catch (err: any) {
            errorMessage = err.message;
        } finally {
            messagesLoading = false;
        }
        await tick();
        scrollToBottom();
    }

    async function getAIResponse(inputText: string): Promise<string> {
        loadingAIResponse = true;
        await tick();
        scrollToBottom();
        const token = localStorage.getItem('authToken');
        let aiResponse = '오류: AI 응답을 가져올 수 없습니다.';

        if (!token) {
            loadingAIResponse = false;
            await goto('/login?redirectTo=/');
            return '';
        }

        try {
            const body: any = { user_message: inputText };
            if (selectedSessionId) body.session_id = selectedSessionId;
            const response = await fetch('/api/chat/', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(body), 
            });

            if (response.status === 401) {
                localStorage.removeItem('authToken');
                isAuthenticated = false;
                await goto('/login?sessionExpired=true');
                return '';
            }

            if (!response.ok) {
                let errorData = { detail: 'API 오류가 발생했습니다.' };
                try {
                  errorData = await response.json();
                } catch (jsonError) { /* Ignore if response is not JSON */ }
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data && data.ai_response) {
                if (!selectedSessionId && data.session_id) {
                    selectedSessionId = data.session_id;
                    await fetchSessions();
                }
                aiResponse = data.ai_response;
            } else {
                console.error('Unexpected API response format:', data);
                throw new Error('수신된 데이터 형식이 올바르지 않습니다.');
            }

        } catch (error: any) {
            console.error('Failed to get AI response:', error);
            errorMessage = error.message || 'AI 응답 처리 중 오류 발생';
            aiResponse = errorMessage; 
        } finally {
            loadingAIResponse = false;
        }
        return aiResponse;
    }

    async function scrollToBottom() {
        await tick();
        if (chatWrapperElement) {
            chatWrapperElement.scrollTo({
                top: chatWrapperElement.scrollHeight,
                behavior: 'smooth'
            });
            
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

        messages = [...messages, { id: Date.now(), text, content: text, sender: 'user', timestamp: new Date().toISOString() }];
        await tick();
        scrollToBottom();

        newMessageText = '';
        await tick();
        adjustTextareaHeight();

        const aiResponseText = await getAIResponse(text);
        if (aiResponseText) {
            messages = [...messages, { id: Date.now() + 1, text: aiResponseText, content: aiResponseText, sender: 'ai', timestamp: new Date().toISOString() }];
            await tick();
            
            setTimeout(() => {
                scrollToBottom();
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

    async function deleteChatSession(sessionId: number) {
        const token = localStorage.getItem('authToken');
        try {
            const res = await fetch(`/api/chat/${sessionId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('세션 삭제에 실패했습니다.');
            sessions = sessions.filter(s => s.id !== sessionId);
            if (selectedSessionId === sessionId) {
                selectedSessionId = null;
                messages = [];
            }
        } catch (err: any) {
            errorMessage = err.message;
        }
    }

    $: {
        let lastDate = '';
        groupedMessages = [];
        for (const m of messages) {
            const dateStr = new Date(m.timestamp).toLocaleDateString();
            if (dateStr !== lastDate) {
                groupedMessages.push({ type: 'date', date: dateStr });
                lastDate = dateStr;
            }
            groupedMessages.push({ type: 'message', message: m });
        }
    }

    onMount(async () => {
        const token = localStorage.getItem('authToken');
        isAuthenticated = !!token;
        await fetchSessions();
        if (textareaElement) textareaElement.focus();
    });

</script>

<div class="layout">
    <aside class="sidebar">
        <button class="new-chat" on:click={() => { selectedSessionId = null; messages = []; }}>New Chat</button>
        {#if sessionsLoading}
            <div class="sidebar-spinner"><div class="spinner"></div></div>
        {:else}
        {#each sessions as sess}
            <div class="session-item {sess.id === selectedSessionId ? 'selected' : ''}" on:click={() => { selectedSessionId = sess.id; fetchMessages(sess.id); }}>
                <span class="session-title">Session {sess.id} — {new Date(sess.created_at).toLocaleString()}</span>
                <button class="delete-button" on:click={(e) => { e.stopPropagation(); deleteChatSession(sess.id); }} aria-label="Delete session">삭제</button>
            </div>
        {/each}
        {/if}
    </aside>
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

        {#if errorMessage}
            <div class="error-banner">{errorMessage}</div>
        {/if}

        <div class="chat-messages-wrapper" bind:this={chatWrapperElement}>
            {#if messagesLoading}
                <div class="messages-loading"><div class="spinner"></div></div>
            {:else}
            <div class="chat-messages">
                {#each groupedMessages as item, idx}
                    {#if item.type === 'date'}
                        <div class="date-sep">{item.date}</div>
                    {:else}
                        <div transition:slide={{ duration: 300 }}>
                            <ChatMessage message={item.message} />
                        </div>
                    {/if}
                {/each}
                {#if loadingAIResponse}
                    <ChatMessage message={{ id: -1, text: '...', sender: 'ai', timestamp: new Date().toISOString() }} isLoading={true}/>
                {/if}
            </div>
            {/if}
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
</div>

<style>
    .layout { display: flex; height: 100vh; }
    .sidebar {
        width: 240px;
        border-right: 1px solid #e5e5e5;
        padding: 10px;
        overflow-y: auto;
        flex-shrink: 0;
        background-color: #fafafa;
    }
    .sidebar button { width: 100%; margin-bottom: 8px; }
    .sidebar div { padding: 6px; cursor: pointer; border-radius: 4px; }
    .sidebar div.selected { background-color: #f0f0f0; }

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

    /* Align loading bubble like AI messages */
    .loading-indicator {
        display: flex;
        justify-content: flex-start;
        padding: 0;
        margin-bottom: 18px; /* match gap between messages */
    }

    /* Error banner and sidebar session styles */
    .error-banner {
        background-color: #fdecea;
        color: #b71c1c;
        padding: 8px 16px;
        margin: 0 20px 10px;
        border-radius: 4px;
        text-align: center;
    }

    .session-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 8px;
        border-radius: 4px;
        cursor: pointer;
    }

    .session-item.selected {
        background-color: #e0e0e0;
    }

    .session-item:hover {
        background-color: #f5f5f5;
    }

    .delete-button {
        background: transparent;
        border: none;
        color: #888;
        cursor: pointer;
        font-size: 14px;
        padding: 4px;
    }

    .delete-button:hover {
        color: #e53935;
    }

    .new-chat {
        background-color: #007bff;
        color: white;
        border: none;
        padding: 8px;
        border-radius: 4px;
        font-weight: 500;
        cursor: pointer;
        margin-bottom: 12px;
    }
    .new-chat:hover {
        background-color: #0056b3;
    }

    /* Spinner styles */
    .spinner {
        border: 4px solid rgba(0,0,0,0.1);
        border-top-color: #007bff;
        border-radius: 50%;
        width: 24px;
        height: 24px;
        animation: spin 1s linear infinite;
        margin: auto;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .sidebar-spinner, .messages-loading {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 20px;
    }

    .date-sep {
        text-align: center;
        margin: 12px 0;
        font-size: 0.8rem;
        color: #888;
    }

</style>
