<script lang="ts">
    import ChatMessage from '$lib/components/ChatMessage.svelte';
    import { onMount, afterUpdate, tick } from 'svelte';
    import { slide } from 'svelte/transition';
    import { goto } from '$app/navigation';

    const sendIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z" /></svg>`;
    const hamburgerIcon = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" width="24" height="24" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>`;
    const backIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" width="24" height="24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>`;
    const searchIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" width="24" height="24"><circle cx="10" cy="10" r="7"/><line x1="21" y1="21" x2="15" y2="15"/></svg>`;
    const menuIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><circle cx="12" cy="6" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="18" r="2"/></svg>`;

    type Message = {
        id: number;
        text?: string;
        content?: string;
        sender: 'user' | 'ai';
        timestamp: string;
    };
    type Session = { id: number; first_user_message: string; first_ai_response: string };

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
    let groupTitle = '새로운 채팅';
    let sidebarCollapsed = false;

    // Update header title based on selected session
    $: groupTitle = selectedSessionId != null ? `Session ${selectedSessionId}` : '새로운 채팅';

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
    <aside class="sidebar {sidebarCollapsed ? 'collapsed' : ''}">
        <button class="new-chat" on:click={() => { selectedSessionId = null; messages = []; }}>New Chat</button>
        {#if sessionsLoading}
            <div class="sidebar-spinner"><div class="spinner"></div></div>
        {:else}
        {#each sessions as sess}
            <div class="session-item {sess.id === selectedSessionId ? 'selected' : ''}" on:click={() => { selectedSessionId = sess.id; fetchMessages(sess.id); }}>
                <div class="session-info">
                    <div class="session-name">
                        {sess.first_user_message
                            ? (sess.first_user_message.length > 20
                                ? sess.first_user_message.slice(0,20) + '...'
                                : sess.first_user_message)
                            : '새로운 대화'}
                    </div>
                    <div class="session-time">
                        {sess.first_ai_response
                            ? (sess.first_ai_response.length > 20
                                ? sess.first_ai_response.slice(0,20) + '...'
                                : sess.first_ai_response)
                            : ''}
                    </div>
                </div>
                <button class="delete-button" on:click={(e) => { e.stopPropagation(); deleteChatSession(sess.id); }} aria-label="Delete session">삭제</button>
            </div>
        {/each}
        {/if}
    </aside>
    <div class="chat-page-container">
        <header class="chat-header">
            <div class="header-left">
                <button class="icon-button toggle-button" aria-label="Toggle sidebar" on:click={() => sidebarCollapsed = !sidebarCollapsed}>
                    {@html hamburgerIcon}
                </button>
                <span class="header-title">{groupTitle}</span>
            </div>
            <div class="header-right">
                {#if isAuthenticated}
                    <button class="icon-button login-button" on:click={handleLogout}>로그아웃</button>
                {:else}
                    <button class="icon-button login-button" on:click={() => goto('/login')}>로그인</button>
                {/if}
            </div>
        </header>

        {#if errorMessage}
            <div class="error-banner">{errorMessage}</div>
        {/if}

        <div class="chat-messages-wrapper" bind:this={chatWrapperElement}>
            {#if messagesLoading}
                <div class="messages-loading"><div class="spinner"></div></div>
            {:else}
                {#if groupedMessages.length === 0}
                    <div class="empty-state">새로운 대화를 시작해보세요.</div>
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
            {/if}
        </div>

        <div class="chat-input-area">
            <div class="textarea-container">
                <input
                    bind:this={textareaElement}
                    bind:value={newMessageText}
                    placeholder="메시지 입력"
                    on:keydown={(e) => {
                        if (e.key === 'Enter') {
                            e.preventDefault();
                            sendMessage();
                        }
                    }}
                />
            </div>
            <button class="icon-button action-button" on:click={sendMessage} disabled={!newMessageText.trim() || loadingAIResponse} aria-label="Send">{@html sendIcon}</button>
        </div>
        <footer class="chat-footer">
            Velt는 실수를 할 수 있습니다. 중요한 정보는 재차 확인하세요.
        </footer>
    </div>
</div>

<style>
    .layout { display: flex; height: 100vh; }
    .sidebar {
        width: 240px;
        transition: width 0.3s ease, padding 0.3s ease;
        border-right: 1px solid #222;
        padding: 10px;
        overflow-y: auto;
        flex-shrink: 0;
        background-color: #1E1E1F;
        color: #EEE;
    }
    .sidebar button { width: 100%; margin-bottom: 8px; color: #EEE; background: #2A2A2A; border: none; }
    .sidebar div { padding: 6px; cursor: pointer; border-radius: 4px; color: #EEE; }
    .sidebar div.selected { background-color: #333; }
    .sidebar div:hover { background-color: #2A2A2A; }
    .sidebar.collapsed {
        width: 0;
        padding: 0;
        overflow: hidden;
    }
    .sidebar > * {
        opacity: 1;
        transition: opacity 0.3s ease;
    }
    .sidebar.collapsed > * {
        opacity: 0.1;
        transition: opacity 0.3s ease;
        pointer-events: none;
    }

    .chat-page-container {
        display: flex;
        flex-direction: column;
        height: 100vh;
        margin: 0;
        background-color: #131316;
        overflow: hidden;
        flex: 1;
    }

    .chat-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        background-color: #1E1E1F;
        color: #FFF;
        flex-shrink: 0;
    }
    .header-left,
    .header-right {
        display: flex;
        align-items: center;
    }
    .header-right {
        gap: 12px;
    }
    .icon-button {
        background: transparent;
        border: none;
        color: inherit;
        padding: 4px;
        cursor: pointer;
    }
    .header-title {
        margin-left: 8px;
        font-size: 16px;
        font-weight: 600;
    }

    .auth-buttons {
        display: flex;
        gap: 10px;
    }

    .auth-button {
        padding: 6px 12px;
        border: 1px solid transparent;
        border-radius: 6px;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out, color 0.2s ease-in-out;
    }

    .login-button {
        background-color: #3BD66A;
        color: #131316;
        border: none;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 14px;
        font-weight: 500;
        margin-left: 12px;
        cursor: pointer;
        transition: background-color 0.2s ease;
    }
    .login-button:hover {
        background-color: #2AA05A;
    }

    .signup-button {
        background-color: #007bff;
        color: white;
    }
    .signup-button:hover {
         background-color: #0056b3;
    }

    .logout-button {
        background-color: #f8d7da;
        color: #721c24;
        border-color: #f5c6cb;
    }
    .logout-button:hover {
        background-color: #f5c6cb;
    }

    .chat-messages-wrapper {
        flex-grow: 1;
        overflow-y: auto;
        padding: 20px;
        background-color: #131316;
        position: relative;
    }

    .chat-messages {
        display: flex;
        flex-direction: column;
        gap: 18px;
        height: 100%;
        padding-bottom: 20px;
    }

    .chat-input-area {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        background-color: #1E1E1F;
        flex-shrink: 0;
    }

    .textarea-container {
        flex-grow: 1;
        background-color: #2A2A2A;
        border-radius: 20px;
        margin: 0 8px;
        padding: 0 12px;
        box-sizing: border-box;
        display: flex;
        align-items: center;
    }
    .textarea-container input {
        width: 100%;
        background: transparent;
        border: none;
        color: #FFF;
        font-size: 14px;
        padding: 8px 0;
        box-sizing: border-box;
        outline: none;
        margin: 0;
    }
    .textarea-container input:focus {
        outline: none;
        box-shadow: none;
    }

    .action-button {
        background: transparent;
        border: none;
        color: #999;
        font-size: 20px;
        padding: 4px;
        cursor: pointer;
    }
    .action-button:not(:disabled) {
        color: #3BD66A;
    }
    .action-button:disabled {
        color: #555;
        cursor: not-allowed;
    }

    .chat-footer {
        padding: 8px 20px;
        text-align: center;
        font-size: 0.7rem;
        color: #b0b0b0;
        background-color: #ffffff;
        flex-shrink: 0;
        border-top: 1px solid #f0f0f0;
    }

    .loading-indicator {
        display: flex;
        justify-content: flex-start;
        padding: 0;
        margin-bottom: 18px;
    }

    .error-banner {
        background-color: #fdecea;
        color: #b71c1c;
        padding: 8px 16px;
        margin: 0 20px 10px;
        border-radius: 4px;
        text-align: center;
    }

    .session-item {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        padding: 6px 8px;
        border-radius: 4px;
        cursor: pointer;
        color: #EEE;
        font-size: 0.85rem;
        margin-bottom: 8px;
    }
    .session-item.selected {
        background-color: #333;
    }
    .session-item:hover { background-color: #2A2A2A; }

    .delete-button {
        align-self: flex-end;
        background-color: #333;
        border: none;
        color: #EEE;
        cursor: pointer;
        font-size: 12px;
        padding: 2px 4px;
        border-radius: 4px;
        margin-top: 4px;
    }
    .delete-button:hover {
        background-color: #3BD66A;
        color: #131316;
    }

    .new-chat {
        background-color: #3BD66A;
        color: white;
        border: none;
        padding: 8px;
        border-radius: 4px;
        font-weight: 500;
        cursor: pointer;
        margin-bottom: 12px;
    }
    .new-chat:hover {
        background-color: #2AA05A;
    }

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
        display: inline-block;
        background-color: #2A2A2A;
        color: #CCC;
        padding: 4px 12px;
        border-radius: 12px;
        text-align: center;
        margin: 12px auto;
        font-size: 0.8rem;
    }

    /* Darken chat footer */
    .chat-footer {
        background-color: #1E1E1F;
        color: #888;
        border-top: 1px solid #222;
    }

    /* Login/logout button style */
    .login-button:focus {
        outline: none;
        box-shadow: none;
    }
    .login-button:focus-visible {
        outline: none;
    }

    /* Completely transparent scrollbar track and background */
    .chat-messages-wrapper::-webkit-scrollbar {
        width: 4px;
    }
    .chat-messages-wrapper::-webkit-scrollbar-track,
    .chat-messages-wrapper::-webkit-scrollbar-track-piece,
    .chat-messages-wrapper::-webkit-scrollbar-corner {
        background: none;
        border: none;
    }
    .chat-messages-wrapper::-webkit-scrollbar-thumb {
        background-color: rgba(255, 255, 255, 0.3);
        border-radius: 2px;
        border: none;
    }
    /* Firefox scrollbar styling */
    .chat-messages-wrapper {
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 255, 255, 0.3) transparent;
    }

    .session-info {
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }
    .session-name {
        font-size: 0.85rem;
        font-weight: 500;
        color: #EEE;
    }
    .session-time {
        font-size: 0.75rem;
        color: #AAA;
    }

    .toggle-button {
        background: transparent;
        border: none;
        color: inherit;
        padding: 4px;
        cursor: pointer;
    }

    .empty-state {
        color: #777;
        font-size: 1rem;
        text-align: center;
        margin-top: 40%;
    }

</style>
