async function carregarDetalhesAjuste() {
    const numeroAjuste = window.location.pathname.split('/').pop();
    try {
        const response = await fetch(`/detalhes-ajuste/${numeroAjuste}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Erro ao carregar detalhes do ajuste');
        }

        const ajustes = await response.json();
        if (ajustes.length === 0) {
            throw new Error('Nenhum item encontrado para este ajuste');
        }

        // Preenche as informações gerais (usando o primeiro item)
        const ajuste = ajustes[0];
        document.getElementById('numeroAjuste').textContent = ajuste.numero_ajuste || 'N/A';
        document.getElementById('dataHora').textContent = ajuste.data_hora || 'N/A';
        document.getElementById('matricula').textContent = ajuste.matricula || 'N/A';
        document.getElementById('nomeUsuario').textContent = ajuste.nome_usuario || 'N/A';
        document.getElementById('usuarioLiberou').textContent = ajuste.usuario_liberou || 'N/A';

        // Verifica o status do ajuste (se todos os itens têm status 'LIBERADO')
        const isLiberado = ajustes.every(item => item.status === 'LIBERADO');
        if (isLiberado) {
            document.getElementById('liberarBtn').style.display = 'none';
            document.getElementById('statusMessage').style.display = 'block';
        }

        // Preenche a tabela com todos os itens do ajuste
        const tbody = document.getElementById('itensAjusteBody');
        tbody.innerHTML = '';
        ajustes.forEach(item => {
            const ajusteIcon = item.quantidade > 0 ? 'positive' : 'negative';
            const ajusteSymbol = item.quantidade > 0 ? '+' : '-';
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="ajuste-icon ${ajusteIcon}">${ajusteSymbol}</span></td>
                <td>${item.produto_codigo || 'N/A'}</td>
                <td>${item.descricao || 'N/A'}</td>
                <td>${Math.abs(item.quantidade)}</td>
                <td>${item.custo ? item.custo.toFixed(2) : '0.00'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        alert(`Erro ao carregar detalhes do ajuste: ${err.message}`);
    }
}

async function confirmarLiberacao() {
    const numeroAjuste = document.getElementById('numeroAjuste').textContent;
    if (confirm(`Deseja liberar o ajuste #${numeroAjuste}?`)) {
        try {
            const response = await fetch(`/liberar-ajuste/${numeroAjuste}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Erro ao liberar ajuste');
            }

            const resultado = await response.json();
            if (resultado.success) {
                alert(`Ajuste #${numeroAjuste} liberado com sucesso!`);
                window.location.href = '/liberar-ajustes';
            } else {
                throw new Error('Erro ao liberar ajuste');
            }
        } catch (err) {
            alert(`Erro ao liberar ajuste: ${err.message}`);
        }
    }
}

document.addEventListener('DOMContentLoaded', carregarDetalhesAjuste);