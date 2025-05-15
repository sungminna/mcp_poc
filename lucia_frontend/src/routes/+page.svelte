<script lang="ts">
    import ChatMessage from '$lib/components/ChatMessage.svelte';
    import { onMount, afterUpdate, tick, onDestroy } from 'svelte';
    import { slide } from 'svelte/transition';
    import { goto } from '$app/navigation';
    import IconSend from '$lib/components/IconSend.svelte';
    import IconHamburger from '$lib/components/IconHamburger.svelte';
    import IconBack from '$lib/components/IconBack.svelte';

    type Message = {
        id: number;
        text?: string;
        content?: string;
        sender: 'user' | 'ai';
        timestamp: string;
    };
    type Session = { id: number; name: string; created_at: string };

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
    let socket: WebSocket | null = null;
    let creatingRoom = false;
    let streamingAIResponseId: number | null = null;
    let isSending = false;

    // Update header title based on selected session
    $: groupTitle = selectedSessionId != null
        ? sessions.find(s => s.id === selectedSessionId)?.name ?? `Session ${selectedSessionId}`
        : '새로운 채팅';

    // After each update, if loading, scroll down so the loading bubble is visible
    afterUpdate(() => {
        // if (loadingAIResponse) scrollToBottom(); // Scroll handled more granularly now
    });

    async function fetchSessions() {
        sessionsLoading = true;
        errorMessage = '';
        try {
            const token = localStorage.getItem('authToken');
            const res = await fetch('/api/chats/rooms/', { headers: { 'Authorization': `Bearer ${token}` } });
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
            const res = await fetch(`/api/chats/rooms/${sessionId}/messages/`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (!res.ok) throw new Error('메시지 목록을 가져오는데 실패했습니다.');
            const data = await res.json();
            messages = data.map((m: any, idx: number) => ({
                id: idx,
                text: m.content,
                content: m.content,
                sender: m.role === 'user' ? 'user' : 'ai',
                timestamp: new Date().toISOString()
            }));
        } catch (err: any) {
            errorMessage = err.message;
        } finally {
            messagesLoading = false;
        }
        await tick();
        scrollToBottom();
        // Open WebSocket for the selected session
        await openSocketForSession(sessionId);
    }

    // Function to open a WebSocket connection for a given session
    async function openSocketForSession(sessionId: number) {
        // Close existing socket
        if (socket) {
            socket.onmessage = null;
            socket.onclose = null;
            socket.onerror = null;
            socket.close();
            socket = null;
        }

        const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
        const token = localStorage.getItem('authToken');
        if (!token) {
            console.error('No auth token, cannot open WebSocket');
            errorMessage = '인증 토큰이 없어 연결할 수 없습니다. 다시 로그인해주세요.';
            return;
        }

        // Establish new socket
        socket = new WebSocket(`${protocol}://localhost:8000/ws/chat/${sessionId}/?token=${token}`);
        // Wait for open
        await new Promise<void>((resolve, reject) => {
            socket!.addEventListener('open', () => resolve(), { once: true });
            socket!.addEventListener('error', (e) => reject(e), { once: true });
        });

        // Handle incoming messages
        socket.onmessage = async (event) => {
            // Debug: log incoming raw and parsed data
            console.log('[WS] raw data:', event.data);
            const parsed = JSON.parse(event.data);
            console.log('[WS] parsed WS data:', parsed);
            const { message: incoming } = parsed;
            const { type, token, content } = incoming;

            switch (type) {
                case 'token':
                    if (streamingAIResponseId !== null) {
                        const idx = messages.findIndex(msg => msg.id === streamingAIResponseId);
                        if (idx !== -1) {
                            messages[idx] = {
                                ...messages[idx],
                                text: (messages[idx].text || '') + token,
                                content: (messages[idx].content || '') + token
                            };
                            messages = [...messages];
                            await tick();
                            await scrollToBottom();
                        } else {
                            console.warn('[WS Token] No matching AI message ID:', streamingAIResponseId);
                        }
                    }
                    break;
                case 'done':
                    loadingAIResponse = false;
                    streamingAIResponseId = null;
                    await scrollToBottom();
                    break;
                case 'error':
                    errorMessage = content;
                    loadingAIResponse = false;
                    streamingAIResponseId = null;
                    await tick();
                    break;
                default:
                    // Ignore non-LLM message types (e.g., user echoes)
                    break;
            }
        };

        // Cleanup on close/error
        socket.onclose = () => { socket = null; };
        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            errorMessage = '웹소켓 연결에 오류가 발생했습니다. 새로고침하거나 다시 시도해주세요.';
            if (socket) {
                socket.onmessage = null;
                socket.onclose = null;
                socket.onerror = null;
                socket.close();
                socket = null;
            }
        };
    }

    onDestroy(() => {
        socket?.close();
    });

    // Handle starting a new chat: clear messages and reset socket
    function handleNewChat() {
        socket?.close();
        socket = null;
        selectedSessionId = null;
        messages = [];
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

    // Refactored sendMessage to use WebSocket
    async function sendMessage() {
        // Capture and clear input immediately
        const textToSend = newMessageText.trim();
        if (!textToSend || loadingAIResponse || isSending) return;
        
        isSending = true;

        newMessageText = '';
        adjustTextareaHeight();

        errorMessage = '';
        const token = localStorage.getItem('authToken');
        if (!token) {
            await goto('/login');
            isSending = false;
            return;
        }

        try {
            // Ensure a chat room exists if one isn't selected.
            if (!selectedSessionId) {
                if (creatingRoom) {
                    isSending = false;
                    return;
                }
                creatingRoom = true;
                try {
                    const resRoom = await fetch('/api/chats/rooms/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({ name: textToSend.substring(0, 50) })
                    });
                    if (!resRoom.ok) {
                        errorMessage = '챗 세션 생성에 실패했습니다.';
                        isSending = false;
                        return;
                    }
                    const newRoom = await resRoom.json();
                    selectedSessionId = newRoom.id;
                    await fetchSessions();
                    await openSocketForSession(selectedSessionId);
                } catch (err) {
                    errorMessage = '챗 세션 생성 중 오류가 발생했습니다.';
                    isSending = false;
                    return;
                } finally {
                    creatingRoom = false;
                }
            }

            // Append user message to the local messages array
            const userMessageId = Date.now();
            messages = [...messages, { id: userMessageId, text: textToSend, content: textToSend, sender: 'user', timestamp: new Date().toISOString() }];
            await tick();
            scrollToBottom();

            // Prepare for AI response
            loadingAIResponse = true; // Indicate that an AI response is expected

            // Add a placeholder for the AI's message and store its ID
            const aiMessageId = Date.now() + 1; // Ensure unique ID, slightly offset from user message
            streamingAIResponseId = aiMessageId;
            messages = [
                ...messages,
                {
                    id: aiMessageId,
                    text: '', // Start with empty text
                    content: '',
                    sender: 'ai',
                    timestamp: new Date().toISOString()
                }
            ];
            await tick();
            scrollToBottom(); // Scroll to show the AI placeholder

            // Ensure WebSocket is open and then send the message
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                try {
                    await openSocketForSession(selectedSessionId!);
                    if (!socket || socket.readyState !== WebSocket.OPEN) {
                        errorMessage = '웹소켓 연결을 다시 설정할 수 없습니다. 새로고침 해주세요.';
                        loadingAIResponse = false;
                        streamingAIResponseId = null;
                        messages = messages.filter(m => m.id !== aiMessageId);
                        isSending = false;
                        return;
                    }
                    errorMessage = ''; // Clear previous error if connection succeeds
                } catch (e) {
                    errorMessage = '웹소켓 연결 중 오류가 발생했습니다. 새로고침 해주세요.';
                    loadingAIResponse = false;
                    streamingAIResponseId = null;
                    messages = messages.filter(m => m.id !== aiMessageId);
                    isSending = false;
                    return;
                }
            }
            
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ message: textToSend }));
            } else {
                 errorMessage = '웹소켓이 연결되지 않아 메시지를 보낼 수 없습니다.';
                 loadingAIResponse = false;
                 streamingAIResponseId = null;
                 messages = messages.filter(m => m.id !== aiMessageId);
            }
        
        } catch (error) {
            console.error("Error in sendMessage:", error);
            errorMessage = "메시지 전송 중 오류가 발생했습니다.";
            loadingAIResponse = false;
            streamingAIResponseId = null;
            if (streamingAIResponseId) {
                 messages = messages.filter(m => m.id !== streamingAIResponseId);
            }
        } finally {
            isSending = false;
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
            const res = await fetch(`/api/chats/rooms/${sessionId}/`, {
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
        <button class="new-chat" on:click={handleNewChat}>New Chat</button>
        {#if sessionsLoading}
            <div class="sidebar-spinner"><div class="spinner"></div></div>
        {:else}
        {#each sessions as sess}
            <div class="session-item {sess.id === selectedSessionId ? 'selected' : ''}" on:click={() => { selectedSessionId = sess.id; fetchMessages(sess.id); }}>
                <div class="session-info">
                    <div class="session-name">
                        {sess.name.length > 20 ? sess.name.slice(0,20) + '...' : sess.name}
                    </div>
                    <div class="session-time">
                        {new Date(sess.created_at).toLocaleString()}
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
                    <IconHamburger />
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
                                <ChatMessage
                                    message={item.message}
                                    isLoading={item.message.id === streamingAIResponseId}
                                />
                            </div>
                        {/if}
                    {/each}
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
                        if (e.key === 'Enter' && !e.isComposing) {
                            e.preventDefault();
                            sendMessage();
                        }
                    }}
                />
            </div>
            <button class="icon-button action-button" on:click={sendMessage} disabled={!newMessageText.trim() || loadingAIResponse || isSending} aria-label="Send">
                <IconSend />
            </button>
        </div>
        <footer class="chat-footer">
            lucia는 실수를 할 수 있습니다. 중요한 정보는 재차 확인하세요.
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
