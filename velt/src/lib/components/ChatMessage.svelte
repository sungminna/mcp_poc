<script lang="ts">
    export let message: {
        id: number;
        text?: string;
        content?: string;
        sender: 'user' | 'ai';
        timestamp: number;
    };
    export let isLoading: boolean = false;

    $: messageClasses = {
        base: 'message-bubble',
        user: message.sender === 'user' ? 'user-message' : '',
        ai: message.sender === 'ai' ? 'ai-message' : '',
        loading: isLoading ? 'loading' : ''
    };

</script>

<div class="message-wrapper {message.sender === 'user' ? 'user' : 'ai'}">
    <div class="{messageClasses.base} {messageClasses.user} {messageClasses.ai} {messageClasses.loading}">
        {#if isLoading}
            <div class="dot-flashing"></div>
        {:else}
            <div class="message-content">
                {message.text ?? message.content}
            </div>
            <div class="timestamp">
                {new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}
            </div>
        {/if}
    </div>
</div>

<style>
    /* Add a wrapper for alignment */
    .message-wrapper {
        display: flex;
        width: 100%;
    }
    .message-wrapper.user {
        justify-content: flex-end;
    }
    .message-wrapper.ai {
        justify-content: flex-start;
    }

    .message-bubble {
        padding: 10px 14px;
        border-radius: 16px;
        max-width: 75%;
        word-wrap: break-word;
        line-height: 1.4;
        position: relative;
        display: flex;
        flex-direction: column;
    }

    .user-message {
        background-color: #3BD66A;
        color: #000;
    }

    .ai-message {
        background-color: #3B3B3B;
        color: #fff;
    }

    .message-content {
       /* Basic styling for text content */
       margin-bottom: 5px; /* Space between text and actions */
    }

    .loading {
        min-height: 24px; /* Adjusted loading height */
        min-width: 60px; /* Give loading bubble some width */
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 12px 18px; /* Match bubble padding */
    }

    /* Dot Flashing Animation (keep as is or adjust color if needed) */
    .dot-flashing {
        position: relative;
        width: 8px; /* Slightly smaller dots */
        height: 8px;
        border-radius: 5px;
        background-color: #a0a0a0; /* Adjusted color */
        color: #a0a0a0;
        animation: dotFlashing 1s infinite linear alternate;
        animation-delay: .5s;
        margin: 0 6px; /* Adjust spacing */
    }

    .dot-flashing::before, .dot-flashing::after {
        content: '';
        display: inline-block;
        position: absolute;
        top: 0;
    }

    .dot-flashing::before {
        left: -12px; /* Adjust spacing */
        width: 8px;
        height: 8px;
        border-radius: 5px;
        background-color: #a0a0a0;
        color: #a0a0a0;
        animation: dotFlashing 1s infinite alternate;
        animation-delay: 0s;
    }

    .dot-flashing::after {
        left: 12px; /* Adjust spacing */
        width: 8px;
        height: 8px;
        border-radius: 5px;
        background-color: #a0a0a0;
        color: #a0a0a0;
        animation: dotFlashing 1s infinite alternate;
        animation-delay: 1s;
    }

    @keyframes dotFlashing {
        0% {
            background-color: #a0a0a0;
        }
        50%, 100% {
            background-color: rgba(160, 160, 160, 0.3);
        }
    }

    .timestamp {
        font-size: 0.7rem;
        color: #555; /* user timestamp color */
        margin-top: 4px;
        align-self: flex-end;
    }

    /* AI bubble timestamp color */
    .message-wrapper.ai .timestamp {
        color: #888;
    }

</style> 