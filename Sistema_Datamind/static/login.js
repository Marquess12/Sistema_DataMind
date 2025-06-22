// console.log('Carregando login.js...');

// async function login() {
//     console.log('Executando login()');
//     const matricula = document.getElementById('matriculaInput').value.trim();
//     const senha = document.getElementById('senhaInput').value.trim();

//     console.log(`Tentativa de login - Matrícula: ${matricula}, Senha: ${senha}`);

//     if (!matricula || !senha) {
//         console.log('Matrícula ou senha não fornecidos.');
//         alert('Por favor, preencha todos os campos.');
//         return;
//     }

//     try {
//         console.log('Enviando requisição POST para /login');
//         const response = await fetch('/login', {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify({ matricula, senha })
//         });
//         console.log('Resposta recebida do backend:', response);

//         if (!response.ok) {
//             const errorData = await response.json();
//             console.error(`Erro na requisição: ${response.status} ${response.statusText} - ${JSON.stringify(errorData)}`);
//             throw new Error(errorData.message || `Erro na requisição: ${response.status} ${response.statusText}`);
//         }

//         const data = await response.json();
//         console.log('Dados retornados do backend:', data);

//         if (data.success) {
//             console.log('Login bem-sucedido. Redirecionando para:', data.redirect);
//             window.location.href = data.redirect;
//         } else {
//             console.error('Erro ao fazer login:', data.message);
//             alert(data.message);
//         }
//     } catch (err) {
//         console.error('Erro ao fazer login:', err);
//         alert(`Erro ao fazer login: ${err.message}`);
//     }
// }

// document.addEventListener('keypress', (event) => {
//     console.log('Tecla pressionada (keypress global):', event.key, 'Código:', event.keyCode);
//     if (event.keyCode === 13 || event.key === 'Enter') {
//         event.preventDefault();
//         event.stopPropagation();
//         console.log('Enter detectado. Executando login().');
//         login();
//     }
// });

// document.addEventListener('keydown', (event) => {
//     console.log('Evento keydown global detectado. Tecla:', event.key, 'Código:', event.keyCode);
//     if (event.keyCode === 13 || event.key === 'Enter') {
//         event.preventDefault();
//         event.stopPropagation();
//         console.log('Enter bloqueado globalmente via keydown.');
//     }
// });

// document.addEventListener('submit', (event) => {
//     event.preventDefault();
//     event.stopPropagation();
//     console.log('Submissão de formulário bloqueada globalmente.');
// });

// console.log('login.js carregado com sucesso.');

// console.log('Carregando login.js...');

// async function login() {
//     const matricula = document.getElementById('matriculaInput').value.trim();
//     const senha = document.getElementById('senhaInput').value.trim();
//     const deviceType = document.getElementById('deviceType').value;

//     console.log(`Tentativa de login - Matrícula: ${matricula}, Dispositivo: ${deviceType}`);

//     if (!matricula || !senha) {
//         alert('Por favor, preencha todos os campos.');
//         return;
//     }

//     try {
//         const response = await fetch('/login', {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//             },
//             body: JSON.stringify({ matricula, senha, deviceType }),
//         });

//         const data = await response.json();

//         if (data.success) {
//             console.log('Login bem-sucedido, redirecionando para:', data.redirect);
//             if (deviceType === 'PDA') {
//                 window.location.href = '/pda_principal';
//             } else {
//                 window.location.href = data.redirect;
//             }
//         } else {
//             console.error('Erro no login:', data.message);
//             alert(data.message || 'Erro ao fazer login. Verifique suas credenciais.');
//         }
//     } catch (error) {
//         console.error('Erro na requisição:', error);
//         alert('Erro ao conectar com o servidor. Tente novamente.');
//     }
// }



// document.addEventListener('keypress', (event) => {
//     console.log('Tecla pressionada (keypress global):', event.key, 'Código:', event.keyCode);
//     if (event.keyCode === 13 || event.key === 'Enter') {
//         event.preventDefault();
//         event.stopPropagation();
//         console.log('Enter detectado. Executando login().');
//         login();
//     }
// });

// document.addEventListener('keydown', (event) => {
//     console.log('Evento keydown global detectado. Tecla:', event.key, 'Código:', event.keyCode);
//     if (event.keyCode === 13 || event.key === 'Enter') {
//         event.preventDefault();
//         event.stopPropagation();
//         console.log('Enter bloqueado globalmente via keydown.');
//     }
// });

// document.addEventListener('submit', (event) => {
//     event.preventDefault();
//     event.stopPropagation();
//     console.log('Submissão de formulário bloqueada globalmente.');
// });

// console.log('login.js carregado com sucesso.');


console.log('Carregando login.js...');

async function login() {
    const matricula = document.getElementById('matriculaInput').value.trim();
    const senha = document.getElementById('senhaInput').value.trim();
    const deviceType = document.getElementById('deviceType').value;

    console.log(`Tentativa de login - Matrícula: ${matricula}, Dispositivo: ${deviceType}`);

    if (!matricula || !senha) {
        alert('Por favor, preencha todos os campos.');
        return;
    }

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ matricula, senha, deviceType }),
        });

        const data = await response.json();

        if (data.success) {
            console.log('Login bem-sucedido, redirecionando para:', data.redirect);
            window.location.href = data.redirect || '/default';
        } else {
            console.error('Erro no login:', data.message);
            alert(data.message || 'Erro ao fazer login. Verifique suas credenciais.');
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        alert('Erro ao conectar com o servidor. Tente novamente.');
    }
}

document.addEventListener('keypress', (event) => {
    console.log('Tecla pressionada (keypress global):', event.key, 'Código:', event.keyCode);
    if (event.keyCode === 13 || event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        console.log('Enter detectado. Executando login().');
        login();
    }
});

document.addEventListener('keydown', (event) => {
    console.log('Evento keydown global detectado. Tecla:', event.key, 'Código:', event.keyCode);
    if (event.keyCode === 13 || event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        console.log('Enter bloqueado globalmente via keydown.');
    }
});

document.addEventListener('submit', (event) => {
    event.preventDefault();
    event.stopPropagation();
    console.log('Submissão de formulário bloqueada globalmente.');
});

console.log('login.js carregado com sucesso.');