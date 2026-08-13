/**
 * Групповой чат: AJAX polling (без WebSocket — ограничение виртуального хостинга).
 * Опрашивает сервер каждые 3 секунды на новые сообщения (after_id),
 * отправка сообщений — fetch POST с CSRF-токеном.
 */
(function () {
    'use strict';

    var chatBox = document.getElementById('chat-box');
    if (!chatBox) {
        return;
    }

    var messagesUrl = chatBox.dataset.messagesUrl;
    var currentUser = chatBox.dataset.currentUser;
    var csrfToken = chatBox.dataset.csrfToken;
    var chatForm = document.getElementById('chat-form');
    var chatInput = document.getElementById('chat-input');
    var lastMessageId = 0;
    var pollingTimer = null;
    var POLL_INTERVAL = 3000;

    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    function renderMessage(message) {
        var isOwn = message.username === currentUser;
        var wrapper = document.createElement('div');
        wrapper.className = 'd-flex mb-3' + (isOwn ? ' justify-content-end' : '');
        wrapper.dataset.messageId = message.id;

        var avatarHtml = message.avatar_url
            ? '<img src="' + escapeHtml(message.avatar_url) + '" alt="' + escapeHtml(message.username) + '" ' +
              'class="rounded-circle me-2" style="width: 24px; height: 24px; object-fit: cover;">'
            : '<i class="bi bi-person-circle me-2 text-muted"></i>';

        wrapper.innerHTML =
            '<div class="chat-message">' +
                '<div class="d-flex align-items-center mb-1' + (isOwn ? ' justify-content-end' : '') + '">' +
                    avatarHtml +
                    '<strong class="small">' + escapeHtml(message.username) + '</strong>' +
                    '<span class="text-muted small ms-2">' + escapeHtml(message.created_at) + '</span>' +
                '</div>' +
                '<div class="p-2 rounded ' + (isOwn ? 'bg-primary text-white' : 'bg-light') + '">' +
                    '<span class="chat-text">' + escapeHtml(message.text) + '</span>' +
                '</div>' +
            '</div>';

        var emptyNotice = document.getElementById('chat-empty');
        if (emptyNotice) {
            emptyNotice.remove();
        }
        chatBox.appendChild(wrapper);
    }

    function updateLastMessageId() {
        var nodes = chatBox.querySelectorAll('[data-message-id]');
        if (nodes.length > 0) {
            lastMessageId = parseInt(nodes[nodes.length - 1].dataset.messageId, 10) || 0;
        }
    }

    function fetchNewMessages() {
        fetch(messagesUrl + '?after_id=' + lastMessageId, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                return response.json();
            })
            .then(function (data) {
                if (data.messages && data.messages.length > 0) {
                    var isNearBottom =
                        chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 100;
                    data.messages.forEach(renderMessage);
                    updateLastMessageId();
                    if (isNearBottom) {
                        scrollToBottom();
                    }
                }
            })
            .catch(function () {
                // Сетевая ошибка — повторим на следующем тике polling
            });
    }

    function startPolling() {
        if (pollingTimer === null) {
            pollingTimer = setInterval(fetchNewMessages, POLL_INTERVAL);
        }
    }

    function stopPolling() {
        if (pollingTimer !== null) {
            clearInterval(pollingTimer);
            pollingTimer = null;
        }
    }

    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            stopPolling();
        } else {
            fetchNewMessages();
            startPolling();
        }
    });

    chatForm.addEventListener('submit', function (event) {
        event.preventDefault();
        var text = chatInput.value.trim();
        if (!text) {
            return;
        }

        var formData = new FormData();
        formData.append('text', text);

        fetch(messagesUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                return response.json();
            })
            .then(function (data) {
                if (data.message) {
                    renderMessage(data.message);
                    updateLastMessageId();
                    chatInput.value = '';
                    scrollToBottom();
                }
            })
            .catch(function () {
                alert('Не удалось отправить сообщение. Попробуйте ещё раз.');
            });
    });

    // Ctrl+Enter / Cmd+Enter — отправка
    chatInput.addEventListener('keydown', function (event) {
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
        }
    });

    updateLastMessageId();
    scrollToBottom();
    startPolling();
})();
