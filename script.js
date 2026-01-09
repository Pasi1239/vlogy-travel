// --- 1. CONFIGURATION ---
// I added your actual Client ID here so it works immediately!
const CLIENT_ID = "680315039276-ve78nmktah6kkvjlrur48v8kkbq5a1h8.apps.googleusercontent.com";

// --- 2. GOOGLE LOGIN LOGIC ---
window.onload = function () {
    google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: handleCredentialResponse,
        auto_select: false,
        locale: "en" 
    });

    renderGoogleButton();
    displayPosts(); // Load existing posts
};

function renderGoogleButton() {
    const btnDiv = document.getElementById("google-login-btn");
    if (btnDiv) {
        google.accounts.id.renderButton(btnDiv, { 
            theme: "filled_blue", size: "large", shape: "pill" 
        });
    }
}

function handleCredentialResponse(response) {
    const payload = JSON.parse(atob(response.credential.split('.')[1]));
    sessionStorage.setItem('vlogUser', payload.email);
    
    // Switch from Login Screen to App
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app-content').style.display = 'block';
    document.getElementById('user-email').textContent = payload.email;
}

// --- 3. TRAVEL POST LOGIC ---
function addPost() {
    const title = document.getElementById('postTitle').value;
    const desc = document.getElementById('postDesc').value;

    if (!title || !desc) return alert("Please fill everything!");

    const newPost = { title, desc, id: Date.now() };

    // Save to browser memory
    let posts = JSON.parse(localStorage.getItem('vlogPosts')) || [];
    posts.unshift(newPost);
    localStorage.setItem('vlogPosts', JSON.stringify(posts));

    document.getElementById('postTitle').value = '';
    document.getElementById('postDesc').value = '';
    displayPosts();
}

function displayPosts() {
    const container = document.getElementById('vlog-container');
    const posts = JSON.parse(localStorage.getItem('vlogPosts')) || [];
    
    container.innerHTML = posts.map(p => `
        <div class="card">
            <h3>${p.title}</h3>
            <p>${p.desc}</p>
        </div>
    `).join('');
}

function logout() {
    sessionStorage.removeItem('vlogUser');
    location.reload();
}