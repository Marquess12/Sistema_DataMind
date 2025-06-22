

async function carregarAjustesPendentes() {
    try {
        const response = await fetch('/ajustes-pendentes');
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Erro ao carregar ajustes');
        }

        const ajustes = await response.json();
        const tbody = document.getElementById('ajustesBody');
        tbody.innerHTML = '';
        ajustes.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.numero_ajuste}</td>
                <td>${item.data_hora}</td>
                <td>${item.matricula || 'N/A'}</td>
                <td>${item.nome_usuario || 'N/A'}</td>
            `;
            tr.addEventListener('click', () => {
                window.location.href = `/detalhes-ajuste/${item.numero_ajuste}`;
            });
            tbody.appendChild(tr);
        });

        if (ajustes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">Nenhum ajuste pendente encontrado.</td></tr>';
        }
    } catch (err) {
        alert(`Erro ao carregar ajustes pendentes: ${err.message}`);
        const tbody = document.getElementById('ajustesBody');
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">Erro ao carregar os dados.</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', carregarAjustesPendentes);