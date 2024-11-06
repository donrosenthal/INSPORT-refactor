document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed");
    
    const greeting = document.getElementById('greeting');
    const policySidebar = document.getElementById('policySidebar');
    const conversationDisplay = document.getElementById('conversationDisplay');
    const queryInput = document.getElementById('queryInput');
    const submitQuery = document.getElementById('submitQuery');
    const clearConversation = document.getElementById('clearConversation');
    
    console.log("submitQuery:", submitQuery);
    console.log("clearConversation:", clearConversation);
    console.log("queryInput:", queryInput);   

    // Configure the marked library for converting markdown in the botresponse.
    marked.setOptions({ 
        breaks: true,
        gfm: true,
        headerIds: false,
        langPrefix: 'language-',
    });

    let userData = {};
    let eventSource;

    function initUI() {
        console.log("Entering initUI");
        console.log("Attempting to fetch from /api/init");
        let currentlySelectedPolicy = 'None';  
        console.log("Currently selected policy before init:", currentlySelectedPolicy);
    
        fetch('/api/init')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Received data from /api/init:", data);
                userData = data;
                updateGreeting();
                updatePolicySidebar(currentlySelectedPolicy);
                loadConversationHistory();
                
                // Add a small delay before showing content
                setTimeout(() => {
                    document.querySelector('.container').classList.add('loaded');
                }, 100);
            })
            .catch(error => {
                console.error('Error:', error);
                greeting.textContent = 'Error loading user data. Please refresh the page.';
            });
    
        // Call handle_focus
        fetch('/api/handle_focus')
            .then(response => response.json())
            .then(data => {
                console.log('Focus handled, received data:', data);
                if (data.success) {
                    userData = data; // Store the entire data object
                    if (data.selectedPolicy) {
                        console.log('currentlySelectedPolicy = ', data.selectedPolicy.print_name);
                        currentlySelectedPolicy = data.selectedPolicy.print_name;
                    } else {
                        console.log('No policy currently selected');
                        currentlySelectedPolicy ='None';                        
                    }
                    updatePolicySidebar(currentlySelectedPolicy);
                    
                }
                loadConversationHistory();
            })
            .catch(error => console.error('Error handling focus:', error));
    }

    function updateGreeting() {
        const greeting = document.getElementById('greeting');
        greeting.textContent = `Hi ${userData.firstName}! Ask a question about any of your uploaded policies or insurance in general`;
    }

    function updatePolicySidebar(selectedPolicy) {
        if (!policySidebar) {
            console.error("policySidebar element not found");
            return;
        }
        
        // If no policy is selected, default to 'None'
        selectedPolicy = selectedPolicy || 'None';

        // Clear existing content
        policySidebar.innerHTML = '';
        
        // Create and add the header
        const header = document.createElement('h3');
        header.textContent = "Select a policy to discuss, or 'None' to reset";
        policySidebar.appendChild(header);
        
        if (!userData.policies || userData.policies.length === 0) {
            const noPoliciesMessage = document.createElement('p');
            noPoliciesMessage.textContent = 'No policies uploaded yet.';
            policySidebar.appendChild(noPoliciesMessage);
        } else { 
            // Create a container for radio buttons
            const radioButtonsContainer = document.createElement('div');

            const noneRadio = createRadioButton('None', 'None', selectedPolicy === 'None');
            radioButtonsContainer.appendChild(noneRadio);

            userData.policies.forEach(policy => {
                const policyRadio = createRadioButton(policy.print_name, policy.print_name,policy.print_name === selectedPolicy);
                radioButtonsContainer.appendChild(policyRadio);
            });

            policySidebar.appendChild(radioButtonsContainer);
        }
        console.log('Updated policy sidebar. Selected policy:', selectedPolicy);
    }

    function createRadioButton(value, label, checked = false) {
        const container = document.createElement('div');
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.id = label;
        radio.name = 'policy';
        radio.value = label;
        radio.checked = checked;
        
        const labelElement = document.createElement('label');
        labelElement.htmlFor = label;
        labelElement.textContent = label;
        
        container.appendChild(radio);
        container.appendChild(labelElement);

        radio.addEventListener('change', handlePolicySelection);

        return container;
    }

    function handlePolicySelection(event) {
        const selectedPolicy = event.target.value;
        console.log(`Selected policy: ${selectedPolicy}`);
        console.log(`Selected element:`, event.target);
        console.log(`Selected element value:`, event.target.value);
        console.log(`Selected element id:`, event.target.id);

        // Update the selected policy in userData
        currentlySelectedPolicy = selectedPolicy;

        // Simulate sending the selection to the server
        // In the real implementation, this will be an API call
        fetch('/api/select_policy?policy=' + encodeURIComponent(selectedPolicy))
            .then(response => response.json())
            .then(data => {
                console.log('Policy selection updated:', data);
                // Update the UI to reflect the new selection
                updatePolicySidebar(selectedPolicy);
             })
            .catch(error => console.error('Error:', error));
    }


    function handleQuerySubmit() {
        if (!queryInput) {
            console.error("Query input element not found");
            return;
        }
        const query = queryInput.value.trim();
        if (query) {
            addMessageToConversation('User', query);
            queryInput.value = '';
            
            if (eventSource) {
                eventSource.close();
            }
            
            eventSource = new EventSource('/api/chat?message=' + encodeURIComponent(query));
            
            let botMessage = document.createElement('div');
            botMessage.className = 'message bot-message';
            conversationDisplay.appendChild(botMessage);
    
            let accumulatedMarkdown = '';
            let renderBuffer = '';
            let lastRenderLength = 0;
            
            eventSource.onmessage = function(event) {
                console.log("Received data:", event.data);
                if (event.data === "DONE") {
                    eventSource.close();
                    console.log("Final markdown:", accumulatedMarkdown);
                    
                    // Render the complete markdown when all chunks are received
                    const finalMarkdown = accumulatedMarkdown.replace(/\\n/g, '\n');
                    botMessage.innerHTML = DOMPurify.sanitize(marked.parse(finalMarkdown));
                } else {
                    // Accumulate response data
                    let chunk = event.data.replace(/\\n/g, '\n');
                    accumulatedMarkdown += chunk;
            
                    // Render markdown only if a certain threshold is reached
                    if (accumulatedMarkdown.length > 100 || chunk.includes('\n\n')) {
                        let renderedNewContent = DOMPurify.sanitize(marked.parse(accumulatedMarkdown));
                        botMessage.innerHTML = renderedNewContent;
                    } else {
                        // If not rendering yet, provide a placeholder to indicate typing
                        if (!botMessage.innerHTML.includes('Bot is typing...')) {
                            botMessage.innerHTML = 'Bot is typing...';
                        }
                    }
                }
            
                // Scroll to the bottom
                conversationDisplay.scrollTop = conversationDisplay.scrollHeight;
            };
            
            
            eventSource.onerror = function(error) {
                console.error('EventSource failed:', error);
                eventSource.close();
            };
        }
    }
    
    function addMessageToConversation(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender.toLowerCase()}-message`;
        if (sender === 'User') {
            messageElement.textContent = `${sender}: ${message}`;
        } else {
            messageElement.innerHTML = `${sender}: ${DOMPurify.sanitize(marked.parse(message))}`;
        }
        conversationDisplay.appendChild(messageElement);
        conversationDisplay.scrollTop = conversationDisplay.scrollHeight;
    }

    function loadConversationHistory() {
        fetch('/api/get_conversation_history')
            .then(response => response.json())
            .then(data => {
                conversationDisplay.innerHTML = ''; // Clear existing conversation
                data.history.forEach(message => {
                    const messageElement = document.createElement('div');
                    messageElement.className = `message ${message.type}-message`;
                    if (message.type == 'human') {
                        messageElement.textContent = `User: ${message.content}`;
                    } else {
                        messageElement.innerHTML = `Bot: ${DOMPurify.sanitize(marked.parse(message.content))}`;
                    }
                    conversationDisplay.appendChild(messageElement);
                });
                conversationDisplay.scrollTop = conversationDisplay.scrollHeight;
            })
            .catch(error => console.error('Error loading conversation history:', error));
    }

    function handleClearConversation() {
        fetch('/api/clear')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Clear the conversation display
                    conversationDisplay.innerHTML = '';
                    
                    // Reset the policy selection to "None" if radio buttons exist
                    const noneRadio = document.querySelector('input[name="policy"][value="None"]');
                    if (noneRadio) {
                        noneRadio.checked = true;
                    }

                    // If there's no policy sidebar (i.e., no policies uploaded), we don't need to do anything extra

                    // Close the EventSource if it exists
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;  // Reset the eventSource variable
                    }
                    
                    console.log("Conversation cleared");
                } else {
                    console.error("Failed to clear conversation");
                }
            })
            .catch(error => console.error('Error:', error));
    }

    // Event listeners
    if (submitQuery) submitQuery.addEventListener('click', handleQuerySubmit);
    if (clearConversation) clearConversation.addEventListener('click', handleClearConversation);
    if (queryInput) {
        queryInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleQuerySubmit();
            }
        });
    }

    // Initialize the UI when the page loads
    initUI();
});