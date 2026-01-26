const apiBaseUrl = "https://rssfilter.sgn.space/api";

// Handles RSS Feed URL validation and display of custom feed link
async function validateFeedURL() {
    const userId = await registerUser();
    const feedUrl = document.getElementById('rssFeedUrl').value;
    
    if (!feedUrl) {
        alert('Please enter a feed URL.');
        return;
    }
    
    const response = await fetch(`${apiBaseUrl}/v1/feed/${userId}/${encodeURIComponent(feedUrl)}`);
    if (response.status === 200) {
        const customFeedUrl = document.getElementById('customFeedUrl');
        customFeedUrl.innerText = `${response.url}`;
    } else {
        alert('Failed to validate URL or generate custom feed.');
    }
}

// Handles OPML file upload and processing
async function handleOpmlUpload() {
    const userId = await registerUser();
    const fileInput = document.getElementById('opmlFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select an OPML file.');
        return;
    }
    
    const formData = new FormData();
    formData.append('opml', file);
    formData.append('user_id', userId);
    
    const response = await fetch(`${apiBaseUrl}/v1/signup/process_opml`, {
        method: 'POST',
        headers: {
            'accept': 'application/json',
        },

        body: formData,
    });
    
    if (response.status === 200) {
        const customOpmlUrl = document.createElement('a');
        customOpmlUrl.href = URL.createObjectURL(await response.blob());
        customOpmlUrl.download = 'rssfilter.opml';
        customOpmlUrl.innerText = 'Download your processed OPML file';
        
        const customOpmlDownloadDiv = document.getElementById('customOpmlDownload');
        customOpmlDownloadDiv.appendChild(customOpmlUrl);
    } else {
        alert('Failed to process OPML file.');
    }
}

// Helper function to register user and return user ID
async function registerUser() {
    const response = await fetch(`${apiBaseUrl}/v1/signup/user`, { method: 'POST' });
    const data = await response.json();
    return data.user_id; // Assuming 'user_id' is provided in the response
}

document.getElementById('opmlFile').addEventListener('change', function(event) {
    let fileName = event.target.files[0].name;
    document.getElementById('select-button').innerText = `File selected: ${fileName}`;
});

let dropArea = document.getElementById('select-button');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false);
});

function highlight() {
    let borderColor = getComputedStyle(document.documentElement).getPropertyValue('--transparentPrimaryBlue').trim();
    dropArea.style.backgroundColor = borderColor; // Use the fetched CSS variable value
}

function unhighlight() {
    dropArea.style.backgroundColor = "#FFF";
}
