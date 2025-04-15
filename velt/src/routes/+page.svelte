<script lang="ts">
    import ChatMessage from '$lib/components/ChatMessage.svelte';
    import { onMount, tick } from 'svelte';
    import { slide } from 'svelte/transition';

    const sendIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z" /></svg>`;

    type Message = {
        id: number;
        text: string;
        sender: 'user' | 'ai';
    };

    let messages: Message[] = [];
    let newMessageText: string = '';
    let chatContainer: HTMLDivElement;
    let loadingAIResponse = false;
    let textareaElement: HTMLTextAreaElement;

    async function getAIResponse(inputText: string): Promise<string> {
        loadingAIResponse = true;
        await new Promise(resolve => setTimeout(resolve, 1500));
        loadingAIResponse = false;
        return `흠... "${inputText}"라고 하셨군요. 흥미롭네요!`;
    }

    async function sendMessage() {
        const text = newMessageText.trim();
        if (!text || loadingAIResponse) return;

        messages = [...messages, { id: Date.now(), text, sender: 'user' }];
        tick().then(scrollToBottom);

        newMessageText = '';
        await tick();
        adjustTextareaHeight();

        const aiResponseText = await getAIResponse(text);
        messages = [...messages, { id: Date.now() + 1, text: aiResponseText, sender: 'ai' }];
        tick().then(scrollToBottom);
    }

    function scrollToBottom() {
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
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

    onMount(() => {
        messages = [
            { id: 1, text: 'ㅎㅇㅎㅇ! 뭐 하고 있었어? ��', sender: 'ai' },
        ];
        adjustTextareaHeight();
        tick().then(scrollToBottom);
    });

</script>

<div class="chat-page-container">
    <header class="chat-header">
        ㅎㅇ
    </header>

    <div class="chat-messages-wrapper">
        <div class="chat-messages" bind:this={chatContainer}>
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
        text-align: center;
        font-size: 1rem;
        color: #8e8e8e; /* Grayish color */
        border-bottom: 1px solid #f0f0f0; /* Subtle border */
        flex-shrink: 0; /* Prevent header from shrinking */
        background-color: #ffffff;
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
