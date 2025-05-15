<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { goto } from '$app/navigation';
    import ChatInput from '$lib/components/ChatInput.svelte';
    import Sidebar from '$lib/components/Sidebar.svelte';
    import ChatWindow from '$lib/components/ChatWindow.svelte';
    import Header from '$lib/components/Header.svelte';
    import {
        sessions,
        sessionsLoading,
        selectedSessionId,
        messages,
        messagesLoading,
        loadingAIResponse,
        streamingAIResponseId,
        isSending,
        errorMessage,
        loadSessions,
        initChat,
        sendMessage,
        deleteSessionId,
        newChat,
        logout
    } from '$lib/stores/chat';

    let sidebarCollapsed = false;
    let newMessageText = '';
    let isAuthenticated = false;
    let groupTitle = '새로운 채팅';

    $: groupTitle = $selectedSessionId != null
        ? $sessions.find(s => s.id === $selectedSessionId)?.name ?? `Session ${$selectedSessionId}`
        : '새로운 채팅';

    onMount(() => {
        isAuthenticated = !!localStorage.getItem('authToken');
        loadSessions();
    });

    onDestroy(() => {
        newChat();
    });
</script>

<div class="layout">
    <Sidebar
        sessions={$sessions}
        selectedSessionId={$selectedSessionId}
        sessionsLoading={$sessionsLoading}
        bind:sidebarCollapsed
        on:newChat={() => { newChat(); newMessageText = ''; }}
        on:selectSession={(e) => { newMessageText = ''; initChat(e.detail); }}
        on:deleteSession={(e) => { deleteSessionId(e.detail); newMessageText = ''; }}
    />
    <div class="chat-page-container">
        <Header
          {groupTitle}
          {isAuthenticated}
          errorMessage={$errorMessage}
          on:toggleSidebar={() => sidebarCollapsed = !sidebarCollapsed}
          on:logout={logout}
          on:login={() => goto('/login')}
        />

        <ChatWindow messages={$messages} messagesLoading={$messagesLoading} streamingAIResponseId={$streamingAIResponseId} />

        <ChatInput bind:value={newMessageText} loading={$loadingAIResponse} sending={$isSending} on:send={() => { const text=newMessageText; newMessageText=''; sendMessage(text); }} />
    </div>
</div>

<style>
    .layout { display: flex; height: 100vh; }
    .chat-page-container {
        display: flex;
        flex-direction: column;
        height: 100vh;
        margin: 0;
        background-color: #131316;
        overflow: hidden;
        flex: 1;
    }
</style>
