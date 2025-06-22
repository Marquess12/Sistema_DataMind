


console.log('Carregando relatorio.js...');

async function buscarRelatorio() {
    console.log('Executando buscarRelatorio()');
    const dataInicio = document.getElementById('dataInicio').value;
    const dataFim = document.getElementById('dataFim').value;
    const matricula = document.getElementById('matricula').value.trim();
    // Adicionar a linha abaixo
    const numeroAjuste = document.getElementById('numeroAjuste').value.trim();

    let url = '/relatorio-dados';
    const params = new URLSearchParams();
    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim) params.append('data_fim', dataFim);
    if (matricula) params.append('matricula', matricula);
    // Adicionar a linha abaixo
    if (numeroAjuste) params.append('numero_ajuste', numeroAjuste);
    if (params.toString()) url += `?${params.toString()}`;

    console.log(`Parâmetros de filtro - dataInicio: ${dataInicio}, dataFim: ${dataFim}, matricula: ${matricula}, numeroAjuste: ${numeroAjuste}`);

    try {
        console.log(`Enviando requisição GET para ${url}`);
        const response = await fetch(url);
        console.log('Resposta recebida do backend:', response);

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Resposta não é JSON:', text);
            throw new Error('Resposta do servidor não é JSON. Verifique se você está autenticado.');
        }

        if (!response.ok) {
            const errorData = await response.json();
            console.error(`Erro na requisição: ${response.status} ${response.statusText} - ${JSON.stringify(errorData)}`);
            throw new Error(errorData.error || `Erro na requisição: ${response.status} ${response.statusText}`);
        }

        const ajustes = await response.json();
        console.log('Ajustes retornados do backend:', ajustes);

        const tbody = document.getElementById('relatorioBody');
        tbody.innerHTML = '';
        // Adicionar variável para calcular o total do custo
        let totalCusto = 0;

        // ajustes.forEach(item => {
        //     const tr = document.createElement('tr');
        //     const ajusteIcon = item.quantidade > 0 ? 'positive' : 'negative';
        //     const ajusteSymbol = item.quantidade > 0 ? '+' : '-';
        //     // Adicionar lógica para custo
        //     const custo = item.custo || 0; // Assume que o custo vem do backend, padrão 0 se nulo
        //     const custoTotalItem = custo * Math.abs(item.quantidade); // Custo total do item
        //     totalCusto += custoTotalItem; // Acumula o custo total
        //     tr.innerHTML = `
        //         <td><span class="ajuste-icon ${ajusteIcon}">${ajusteSymbol}</span></td>
        //         <td>${item.numero_ajuste}</td>
        //         <td>${item.produto_codigo}</td>
        //         <td>${item.descricao || 'N/A'}</td>
        //         <td>${ajusteSymbol}${item.quantidade}</td>
        //         <!-- Adicionar a coluna de custo -->
        //         <td>${custoTotalItem.toFixed(2)}</td>
        //         <td>${item.data_hora}</td>
        //         <td>${item.matricula || 'N/A'}</td>
        //         <td>${item.nome_usuario || 'N/A'}</td>
        //     `;
        //     tbody.appendChild(tr);
        // });

        ajustes.forEach(item => {
            const tr = document.createElement('tr');
            const ajusteIcon = item.quantidade > 0 ? 'positive' : 'negative';
            const ajusteSymbol = item.quantidade > 0 ? '+' : '-'; // Definir o símbolo corretamente
            // Adicionar lógica para custo
            const custo = item.custo || 0; // Assume que o custo vem do backend, padrão 0 se nulo
            const custoTotalItem = custo * Math.abs(item.quantidade); // Custo total do item
            totalCusto += custoTotalItem; // Acumula o custo total
            tr.innerHTML = `
                <td><span class="ajuste-icon ${ajusteIcon}">${ajusteSymbol}</span></td>
                <td>${item.numero_ajuste}</td>
                <td>${item.produto_codigo}</td>
                <td>${item.descricao || 'N/A'}</td>
                <td>${ajusteSymbol}${Math.abs(item.quantidade)}</td>
                <!-- Adicionar a coluna de custo -->
                <td>${custoTotalItem.toFixed(2)}</td>
                <td>${item.data_hora}</td>
                <td>${item.matricula || 'N/A'}</td>
                <td>${item.nome_usuario || 'N/A'}</td>
            `;
            tbody.appendChild(tr);
        });

        if (ajustes.length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td colspan="9" style="text-align: center;">Nenhum ajuste encontrado para os filtros selecionados.</td>';
            tbody.appendChild(tr);
        } else {
            // Adicionar linha de total de custo
            const totalTr = document.createElement('tr');
            totalTr.className = 'total-row';
            totalTr.innerHTML = `
                <td colspan="5" style="text-align: right;">Total Custo:</td>
                <td>R$ ${totalCusto.toFixed(2)}</td>
                <td colspan="3"></td>
            `;
            tbody.appendChild(totalTr);
        }

        window.ajustesFiltrados = ajustes;
    } catch (err) {
        console.error('Erro ao carregar relatório:', err);
        alert(`Erro ao carregar relatório: ${err.message}`);
        const tbody = document.getElementById('relatorioBody');
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">Erro ao carregar os dados.</td></tr>';
    }
}

function imprimirRelatorio() {
    if (!window.ajustesFiltrados || window.ajustesFiltrados.length === 0) {
        alert('Nenhum dado para imprimir. Por favor, aplique os filtros e tente novamente.');
        return;
    }

    let printContent = `
        <html>
        <head>
            <title>Relatório de Ajustes</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { text-align: center; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .positive { color: green; }
                .negative { color: red; }
                .total-row { font-weight: bold; background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h1>Relatório de Ajustes</h1>
            <table>
                <thead>
                    <tr>
                        <th></th>
                        <th>Número do Ajuste</th>
                        <th>Código do Produto</th>
                        <th>Descrição</th>
                        <th>Quantidade</th>
                        <!-- Adicionar a coluna abaixo -->
                        <th>Custo (R$)</th>
                        <th>Data/Hora</th>
                        <th>Matrícula</th>
                        <th>Nome do Usuário</th>
                    </tr>
                </thead>
                <tbody>
    `;

    // Adicionar variável para calcular o total do custo
    let totalCusto = 0;
    window.ajustesFiltrados.forEach(item => {
        const ajusteIcon = item.quantidade > 0 ? 'positive' : 'negative';
        const ajusteSymbol = item.quantidade > 0 ? '+' : '-';
        // Adicionar lógica para custo
        const custo = item.custo || 0;
        const custoTotalItem = custo * Math.abs(item.quantidade);
        totalCusto += custoTotalItem;
        printContent += `
            <tr>
                <td><span class="${ajusteIcon}">${ajusteSymbol}</span></td>
                <td>${item.numero_ajuste}</td>
                <td>${item.produto_codigo}</td>
                <td>${item.descricao || 'N/A'}</td>
                <td>${ajusteSymbol}${item.quantidade}</td>
                <!-- Adicionar a coluna de custo -->
                <td>${custoTotalItem.toFixed(2)}</td>
                <td>${item.data_hora}</td>
                <td>${item.matricula || 'N/A'}</td>
                <td>${item.nome_usuario || 'N/A'}</td>
            </tr>
        `;
    });

    // Adicionar linha de total
    printContent += `
            <tr class="total-row">
                <td colspan="5" style="text-align: right;">Total Custo:</td>
                <td>R$ ${totalCusto.toFixed(2)}</td>
                <td colspan="3"></td>
            </tr>
        </tbody>
        </table>
        <script>
            window.onload = function() { window.print(); };
        </script>
    </body>
    </html>
    `;

    const printWindow = window.open('', '_blank');
    printWindow.document.write(printContent);
    printWindow.document.close();
}

async function exportarExcel() {
    console.log('Executando exportarExcel()');
    const dataInicio = document.getElementById('dataInicio').value;
    const dataFim = document.getElementById('dataFim').value;
    const matricula = document.getElementById('matricula').value.trim();
    // Adicionar a linha abaixo
    const numeroAjuste = document.getElementById('numeroAjuste').value.trim();

    let url = '/exportar-relatorio-excel';
    const params = new URLSearchParams();
    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim) params.append('data_fim', dataFim);
    if (matricula) params.append('matricula', matricula);
    // Adicionar a linha abaixo
    if (numeroAjuste) params.append('numero_ajuste', numeroAjuste);
    if (params.toString()) url += `?${params.toString()}`;

    try {
        console.log(`Enviando requisição GET para ${url}`);
        const response = await fetch(url);
        console.log('Resposta recebida do backend:', response);

        if (!response.ok) {
            const errorData = await response.json();
            console.error(`Erro na requisição: ${response.status} ${response.statusText} - ${JSON.stringify(errorData)}`);
            throw new Error(errorData.error || `Erro na requisição: ${response.status} ${response.statusText}`);
        }

        const blob = await response.blob();
        const urlDownload = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = urlDownload;
        a.download = `relatorio_ajustes_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(urlDownload);
    } catch (err) {
        console.error('Erro ao exportar para Excel:', err);
        alert(`Erro ao exportar para Excel: ${err.message}`);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('Página carregada. Executando buscarRelatorio().');
    buscarRelatorio();
});

console.log('relatorio.js carregado com sucesso.');