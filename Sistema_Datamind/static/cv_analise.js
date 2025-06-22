console.log('Carregando cv_analise.js...');

async function carregarVagas() {
    try {
        console.log('Buscando vagas...');
        const response = await fetch('/listar_vagas');
        if (!response.ok) {
            throw new Error('Erro ao carregar vagas');
        }
        const vagas = await response.json();
        const select = document.getElementById('vagaSelect');
        vagas.forEach(vaga => {
            const option = document.createElement('option');
            option.value = vaga.id;
            option.textContent = vaga.titulo;
            select.appendChild(option);
        });
    } catch (err) {
        console.error('Erro ao carregar vagas:', err);
        alert('Erro ao carregar vagas: ' + err.message);
    }
}

async function buscarCandidato() {
    const nome = document.getElementById('nomeCandidato').value.trim();
    const vaga = document.getElementById('vagaSelect').value;

    console.log(`Buscando candidato: Nome=${nome}, Vaga=${vaga}`);

    if (!nome) {
        console.log('Nome do candidato não fornecido.');
        alert('Por favor, insira o nome do candidato.');
        return;
    }

    try {
        const response = await fetch(`/buscar-candidato?nome=${encodeURIComponent(nome)}&vaga=${encodeURIComponent(vaga)}`);
        console.log('Resposta recebida do backend:', response);

        if (!response.ok) {
            const errorData = await response.json();
            console.error(`Erro na requisição: ${response.status} ${response.statusText} - ${JSON.stringify(errorData)}`);
            throw new Error(errorData.error || `Erro na requisição: ${response.status} ${response.statusText}`);
        }

        const candidato = await response.json();
        console.log('Candidato retornado:', candidato);

        document.getElementById('nomeResultado').textContent = `Nome: ${candidato.nome || 'N/A'}`;
        document.getElementById('pontuacaoResultado').textContent = `Pontuação: ${candidato.pontuacao || 'N/A'}`;
    } catch (err) {
        console.error('Erro ao buscar candidato:', err);
        alert(`Erro ao buscar candidato: ${err.message}`);
        document.getElementById('nomeResultado').textContent = 'Nome';
        document.getElementById('pontuacaoResultado').textContent = 'Pontuação';
    }
}
async function buscarCurriculos() {
    const nome = document.getElementById('nomeCandidato').value.trim();
    try {
        console.log(`Buscando currículos com nome: ${nome}`);
        const response = await fetch(`/buscar_curriculos?nome=${encodeURIComponent(nome)}`);
        if (!response.ok) {
            throw new Error('Erro ao buscar currículos');
        }
        const curriculos = await response.json();
        console.log('Currículos encontrados:', curriculos);
        // Pode ser usado para autocomplete futuro
    } catch (err) {
        console.error('Erro ao buscar currículos:', err);
    }
}

function voltar() {
    console.log("Botão Voltar clicado.");
    history.back();
}

async function analisarCurriculos() {
    const vagaId = document.getElementById('vagaSelect').value;
    if (!vagaId) {
        alert('Por favor, selecione uma vaga.');
        return;
    }
    
    try {
        console.log(`Analisando currículos para vaga ID: ${vagaId}`);
        const response = await fetch('/analisar_curriculos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ vaga_id: vagaId })
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Erro ao analisar currículos');
        }
        const resultados = await response.json();
        console.log('Resultados da análise:', resultados);
        
        const tbody = document.getElementById('curriculosBody');
        tbody.innerHTML = '';
        resultados.forEach(resultado => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${resultado.nome}</td>
                <td>${resultado.pontuacao.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });
        
        if (resultados.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" style="text-align: center;">Nenhum currículo encontrado.</td></tr>';
        }
    } catch (err) {
        console.error('Erro ao analisar currículos:', err);
        alert('Erro ao analisar currículos: ' + err.message);
    }
}

document.getElementById('nomeCandidato').addEventListener('input', () => {
    buscarCurriculos();
});

document.addEventListener('DOMContentLoaded', () => {
    console.log('Página carregada. Carregando vagas...');
    carregarVagas();
});

console.log('cv_analise.js carregado com sucesso.');