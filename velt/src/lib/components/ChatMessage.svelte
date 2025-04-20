<script lang="ts">
    export let message: {
        id: number;
        text?: string;
        content?: string;
        sender: 'user' | 'ai';
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
        padding: 12px 18px; /* Slightly larger padding */
        border-radius: 22px; /* More rounded */
        max-width: 80%; /* Adjusted max width */
        word-wrap: break-word;
        line-height: 1.5;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05); /* Subtle shadow */
        position: relative;
        display: flex; /* Use flex for content and actions */
        flex-direction: column; /* Stack content and actions vertically */
    }

    .user-message {
        background-color: #f0f0f0; /* Light gray for user */
        color: #000000; /* Black text for user */
        /* align-self: flex-end; Already handled by wrapper */
        border-bottom-right-radius: 8px; /* Match image corner */
        /* margin-left: auto; Already handled by wrapper */
    }

    .ai-message {
        background-color: #ffffff; /* White for AI */
        color: #000000; /* Black text for AI */
        /* align-self: flex-start; Already handled by wrapper */
        border: 1px solid #e5e5e5; /* Subtle border for AI bubble */
        border-bottom-left-radius: 8px; /* Match image corner */
        /* margin-right: auto; Already handled by wrapper */
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

</style> 