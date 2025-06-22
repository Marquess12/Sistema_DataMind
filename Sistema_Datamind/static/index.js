

console.log('Carregando index.js...');

let currentProduto = null;
let produtosMassivo = []; // Array para armazenar produtos no modo ajuste em massivo
let ultimoCodigoBipado = null; // Armazena o último código bipado para comparação
let ajustesPendentes = []; // Array para armazenar ajustes pendentes
let currentNumeroAjuste = null; // Armazena o numero_ajuste atual

function atualizarAjusteMassivo() {
    const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
    if (ajusteMassivoCheckbox.checked) {
        console.log('Ajuste em Massivo ativado.');
        produtosMassivo = []; // Reseta a lista de produtos acumulados
        ultimoCodigoBipado = null; // Reseta o último código bipado
        document.getElementById('ajusteInput').value = '0'; // Quantidade inicial zero
    } else {
        console.log('Ajuste em Massivo desativado.');
        produtosMassivo = []; // Limpa a lista ao desativar o modo massivo
        ultimoCodigoBipado = null; // Reseta o último código bipado
        document.getElementById('ajusteInput').value = '0'; // Reseta o campo de quantidade
    }
}

function atualizarAjusteMassa() {
    const ajusteMenosCheckbox = document.getElementById('ajusteMenosCheckbox');
    const ajusteMaisCheckbox = document.getElementById('ajusteMaisCheckbox');
    const btnMenos = document.querySelector('.btn-menos');
    const btnMais = document.querySelector('.btn-mais');

    console.log(`Atualizar Ajuste Massa - Ajuste Menos: ${ajusteMenosCheckbox.checked}, Ajuste Mais: ${ajusteMaisCheckbox.checked}`);

    if (ajusteMenosCheckbox.checked && ajusteMaisCheckbox.checked) {
        ajusteMaisCheckbox.checked = false;
    }

    if (ajusteMenosCheckbox.checked) {
        btnMenos.disabled = false;
        btnMais.disabled = true;
    } else if (ajusteMaisCheckbox.checked) {
        btnMenos.disabled = true;
        btnMais.disabled = false;
    } else {
        btnMenos.disabled = false;
        btnMais.disabled = false;
    }
}

function atualizarOcultarTeclado() {
    const ocultarTecladoCheckbox = document.getElementById('ocultarTecladoCheckbox');
    const codigoInput = document.getElementById('codigoInput');

    if (ocultarTecladoCheckbox.checked) {
        console.log('Ocultar Teclado ativado.');
        codigoInput.setAttribute('inputmode', 'none');
        codigoInput.focus();
    } else {
        console.log('Ocultar Teclado desativado.');
        codigoInput.removeAttribute('inputmode');
        codigoInput.focus();
    }
}

function formatarQuantidade() {
    const ajusteMenosCheckbox = document.getElementById('ajusteMenosCheckbox');
    const ajusteMaisCheckbox = document.getElementById('ajusteMaisCheckbox');
    let quantidade = parseInt(document.getElementById('ajusteInput').value) || 0;

    console.log(`Formatar Quantidade - Quantidade atual: ${quantidade}, Ajuste Menos: ${ajusteMenosCheckbox.checked}, Ajuste Mais: ${ajusteMaisCheckbox.checked}`);

    quantidade = Math.abs(quantidade);

    if (ajusteMenosCheckbox.checked) {
        document.getElementById('ajusteInput').value = -quantidade;
    } else {
        document.getElementById('ajusteInput').value = quantidade;
    }
    console.log(`Quantidade formatada para: ${document.getElementById('ajusteInput').value}`);
}

// async function buscarProduto() {
//     console.log('Executando buscarProduto()');
//     const codigo = document.getElementById('codigoInput').value.trim();
//     console.log(`Buscando produto com código: ${codigo}`);

//     if (!codigo) {
//         console.log('Código não fornecido.');
//         alert('Por favor, insira o código ou barras do produto.');
//         return;
//     }

//     try {
//         console.log(`Enviando requisição GET para /produto/${codigo}`);
//         const response = await fetch(`/produto/${codigo}`);
//         console.log('Resposta recebida do backend:', response);

//         if (!response.ok) {
//             const errorData = await response.json();
//             console.error(`Erro na requisição: ${response.status} ${response.statusText} - ${JSON.stringify(errorData)}`);
//             throw new Error(errorData.error || `Erro na requisição: ${response.status} ${response.statusText}`);
//         }

//         const produto = await response.json();
//         console.log('Produto retornado do backend:', produto);
//         currentProduto = produto;

//         document.getElementById('produtoInfo').innerHTML = `
//             <p>Código: ${produto.codigo}</p>
//             <p>Descrição: ${produto.descricao || 'Descrição não disponível'}</p>
//             <p>Saldo Atual: ${produto.saldo_atual !== undefined ? produto.saldo_atual : 'N/A'}</p>
//             <p>Barras: ${produto.barras || 'N/A'}</p>
//         `;
//         document.getElementById('ajusteForm').style.display = 'block';

//         const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
//         if (!ajusteMassivoCheckbox.checked) {
//             document.getElementById('ajusteInput').value = '0';
//         } else if (ultimoCodigoBipado !== codigo) {
//             document.getElementById('ajusteInput').value = '1'; // Quantidade padrão para novo código
//         }

//         document.getElementById('codigoInput').value = '';
//         ultimoCodigoBipado = codigo;
//         carregarHistorico();
//     } catch (err) {
//         console.error('Erro ao buscar produto:', err);
//         alert(`Erro ao buscar produto: ${err.message}`);
//         document.getElementById('produtoInfo').innerHTML = '';
//         document.getElementById('ajusteForm').style.display = 'none';
//         currentProduto = null;
//         document.getElementById('codigoInput').value = '';
//     }
// }

async function buscarProduto(autoAdicionar = false) {
    const codigoInput = document.getElementById('codigoInput');
    const produtoInfo = document.getElementById('produtoInfo');
    const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
    const ajusteAutomaticoCheckbox = document.getElementById('ajusteAutomaticoCheckbox');

    if (!codigoInput) {
        console.error('Elemento codigoInput não encontrado.');
        return;
    }

    const ajusteMassa = ajusteMassivoCheckbox ? ajusteMassivoCheckbox.checked : false;
    const ajusteAutomatico = ajusteAutomaticoCheckbox ? ajusteAutomaticoCheckbox.checked : false;
    console.log('Ajuste em Massa ativo:', ajusteMassa, 'Ajuste Automático ativo:', ajusteAutomatico);

    const codigo = codigoInput.value.trim();

    if (!codigo) {
        if (produtoInfo) {
            exibirMensagem('Por favor, insira um código ou barras.', 'error');
        }
        manterFoco();
        return;
    }

    try {
        console.log('Iniciando busca para o código/barras:', codigo);
        const response = await fetch(`/produto/${encodeURIComponent(codigo)}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            credentials: 'include'
        });

        console.log('Status da resposta:', response.status);
        console.log('Resposta OK:', response.ok);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Erro na resposta (status:', response.status, '):', errorText);
            if (produtoInfo) {
                exibirMensagem(`Erro ao buscar o produto: ${response.status} - ${errorText}`, 'error');
            }
            produtoSelecionado = null;
            currentProduto = null;
            manterFoco();
            return;
        }

        const data = await response.json();
        console.log('Dados recebidos do backend:', data);

        if (data && typeof data === 'object' && 'codigo' in data && Object.keys(data).length > 0) {
            console.log('Produto encontrado:', data);
            produtoSelecionado = data;
            currentProduto = {
                codigo: data.codigo,
                descricao: data.descricao || 'N/A',
                saldo_atual: data.saldo_atual != null ? String(data.saldo_atual) : 'N/A',
                barras: data.barras || 'N/A',
                Local1: data.Local1 || 'N/A', // Garantindo que Local1 seja incluído
                Local2: data.Local2 || 'N/A', // Garantindo que Local2 seja incluído
                Grupo: data.Grupo || 'N/A'    // Garantindo que Grupo seja incluído
            };

            const codigoProduto = currentProduto.codigo != null ? String(currentProduto.codigo) : 'N/A';
            const descricaoProduto = currentProduto.descricao || 'N/A';
            const saldoAtual = currentProduto.saldo_atual != null ? String(currentProduto.saldo_atual) : 'N/A';
            const barrasProduto = currentProduto.barras || 'N/A';
            const local1 = currentProduto.Local1 || 'N/A';
            const local2 = currentProduto.Local2 || 'N/A';
            const grupo = currentProduto.Grupo || 'N/A';

            const htmlContent = `
                <p><strong>Código:</strong> ${codigoProduto}</p>
                <p><strong>Descrição:</strong> ${descricaoProduto}</p>
                <p><strong>Saldo Atual:</strong> ${saldoAtual}</p>
                <p><strong>Barras:</strong> ${barrasProduto}</p>
                <p><strong>Local 1:</strong> ${local1}</p>
                <p><strong>Local 2:</strong> ${local2}</p>
                <p><strong>Grupo:</strong> ${grupo}</p>
            `;
            console.log('Conteúdo HTML a ser exibido em produtoInfo:', htmlContent);

            if (produtoInfo) {
                produtoInfo.innerHTML = htmlContent;
            } else {
                console.error('Elemento produtoInfo não encontrado ao tentar exibir informações do produto.');
            }

            if (autoAdicionar || ajusteAutomatico) {
                console.log('Ajuste Automático ativo, adicionando ajuste automaticamente.');
                await adicionarAjuste();
            }
        } else {
            let errorMessage = 'Produto não encontrado.';
            if (data && 'error' in data) {
                errorMessage = data.error || 'Erro desconhecido ao buscar o produto.';
                console.log('Erro retornado pelo backend:', errorMessage);
            } else if (data && 'success' in data && !data.success) {
                errorMessage = 'Produto não encontrado no servidor.';
                console.log('Backend retornou success: false:', data);
            } else if (data && Object.keys(data).length === 0) {
                errorMessage = 'Resposta vazia do servidor.';
                console.log('Backend retornou um objeto vazio:', data);
            } else {
                errorMessage = 'Formato de resposta inválido do servidor.';
                console.log('Formato de resposta inesperado:', data);
            }

            if (produtoInfo) {
                exibirMensagem(errorMessage, 'error');
            }
            produtoSelecionado = null;
            currentProduto = null;
        }
    } catch (error) {
        console.error('Erro ao fazer a requisição:', error.message);
        if (produtoInfo) {
            exibirMensagem(`Erro ao buscar o produto: ${error.message}`, 'error');
        }
        produtoSelecionado = null;
        currentProduto = null;
    }

    codigoInput.value = '';
    manterFoco();
}

async function processarCodigoBarras(codigo) {
    if (!codigo) {
        console.log('Nenhum código fornecido para processar.');
        return;
    }

    try {
        console.log(`Processando código de barras: ${codigo}`);
        const response = await fetch(`/produto/${codigo}`);
        const produto = await response.json();
        if (produto.error) {
            throw new Error(produto.error);
        }

        currentProduto = produto;

        const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
        if (ajusteMassivoCheckbox.checked) {
            const ajusteMenosCheckbox = document.getElementById('ajusteMenosCheckbox');
            const ajusteMaisCheckbox = document.getElementById('ajusteMaisCheckbox');

            console.log('Ajuste em Massivo ativo. Ajuste Menos:', ajusteMenosCheckbox.checked, 'Ajuste Mais:', ajusteMaisCheckbox.checked);

            // Verifica se o produto já está na lista de produtos massivos
            let produtoExistente = produtosMassivo.find(p => p.codigo === produto.codigo);

            if (!produtoExistente || ultimoCodigoBipado !== codigo) {
                // Novo produto ou novo bip após mudança de código
                produtoExistente = { codigo: produto.codigo, quantidade: 0 };
                if (!produtosMassivo.find(p => p.codigo === produto.codigo)) {
                    produtosMassivo.push(produtoExistente);
                }
            }

            // Incrementa a quantidade para o bip atual
            produtoExistente.quantidade += 1;

            // Calcula a quantidade total para exibição
            const quantidadeTotal = produtoExistente.quantidade;
            document.getElementById('ajusteInput').value = ajusteMenosCheckbox.checked ? -quantidadeTotal : quantidadeTotal;

            console.log('Produtos acumulados:', produtosMassivo);
            console.log('Quantidade atualizada no campo:', document.getElementById('ajusteInput').value);

            ultimoCodigoBipado = codigo;

            document.getElementById('produtoInfo').innerHTML = `
                <p>Código: ${produto.codigo}</p>
                <p>Descrição: ${produto.descricao || 'Descrição não disponível'}</p>
                <p>Saldo Atual: ${produto.saldo_atual !== undefined ? produto.saldo_atual : 'N/A'}</p>
                <p>Barras: ${produto.barras || 'N/A'}</p>
            `;
            document.getElementById('ajusteForm').style.display = 'block';
        }

        document.getElementById('codigoInput').value = '';
    } catch (err) {
        console.error('Erro ao processar código de barras:', err);
        alert('Erro ao processar código de barras: ' + err.message);
        document.getElementById('codigoInput').value = '';
    }
}

function alterarQuantidade(operacao) {
    const ajusteMenosCheckbox = document.getElementById('ajusteMenosCheckbox');
    const ajusteMaisCheckbox = document.getElementById('ajusteMaisCheckbox');
    let quantidade = parseInt(document.getElementById('ajusteInput').value) || 0;

    console.log(`Alterar quantidade - Operação: ${operacao}, Quantidade atual: ${quantidade}, Ajuste Menos: ${ajusteMenosCheckbox.checked}, Ajuste Mais: ${ajusteMaisCheckbox.checked}`);

    if (ajusteMenosCheckbox.checked && operacao !== 'menos') {
        alert('Apenas ajustes de diminuição são permitidos com "Ajuste Menos" marcado.');
        return;
    }
    if (ajusteMaisCheckbox.checked && operacao !== 'mais') {
        alert('Apenas ajustes de aumento são permitidos com "Ajuste Mais" marcado.');
        return;
    }

    if (operacao === 'mais') {
        quantidade += 1;
    } else if (operacao === 'menos') {
        quantidade -= 1;
    }

    document.getElementById('ajusteInput').value = quantidade;
    console.log(`Quantidade atualizada para: ${quantidade}`);
}

async function adicionarAjuste() {
    console.log('Iniciando função adicionarAjuste...');

    // Verifica se há um produto selecionado
    if (!currentProduto) {
        console.log('Erro: Nenhum produto selecionado para adicionar ao ajuste.');
        alert('Nenhum produto selecionado para adicionar ao ajuste. Por favor, escaneie ou busque um produto primeiro.');
        return;
    }
    console.log('Produto selecionado:', currentProduto);

    // Verifica a quantidade
    let quantidade = parseInt(document.getElementById('ajusteInput').value);
    console.log('Quantidade digitada:', quantidade);
    if (isNaN(quantidade) || quantidade === 0) {
        console.log('Erro: Quantidade inválida:', quantidade);
        alert('Por favor, digite uma quantidade válida (diferente de 0).');
        return;
    }

    try {
        // Se não houver numero_ajuste, obtém um novo do backend
        if (!currentNumeroAjuste) {
            console.log('Obtendo novo número de ajuste do backend...');
            const response = await fetch('/proximo-numero-ajuste', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });
            console.log('Resposta do backend para /proximo-numero-ajuste:', response);

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Erro ao buscar número de ajuste:', errorData);
                alert(`Erro ao obter número de ajuste: ${errorData.error || 'Erro desconhecido'}`);
                throw new Error(errorData.error || 'Erro ao obter número de ajuste');
            }

            const data = await response.json();
            if (!data.success || !data.numero_ajuste) {
                console.error('Erro: Resposta do backend não contém numero_ajuste:', data);
                alert('Erro: Não foi possível obter o número de ajuste do servidor.');
                throw new Error('Resposta do backend inválida');
            }

            currentNumeroAjuste = data.numero_ajuste;
            console.log(`Novo número de ajuste gerado: ${currentNumeroAjuste}`);
            // Exibe o número de ajuste para o usuário
            alert(`Número de ajuste gerado: ${currentNumeroAjuste}`);
        } else {
            console.log(`Número de ajuste já existe: ${currentNumeroAjuste}`);
            alert(`Usando número de ajuste existente: ${currentNumeroAjuste}`);
        }

        // Adiciona o ajuste ao backend (tabela ajustes_pendentes)
        const ajuste = {
            numero_ajuste: currentNumeroAjuste,
            codigo: currentProduto.codigo,
            descricao: currentProduto.descricao || 'Descrição não disponível',
            quantidade: quantidade
        };
        console.log('Enviando ajuste para o backend:', ajuste);

        const response = await fetch('/adicionar-ajuste-pendente', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ajuste)
        });
        console.log('Resposta do backend para /adicionar-ajuste-pendente:', response);

        const result = await response.json();
        if (!response.ok) {
            console.error('Erro ao adicionar ajuste pendente:', result);
            alert(`Erro ao adicionar ajuste pendente: ${result.error || 'Erro desconhecido'}`);
            throw new Error(result.error || 'Erro ao adicionar ajuste pendente');
        }

        if (result.success) {
            console.log('Ajuste adicionado com sucesso no backend!');
            alert('Ajuste adicionado com sucesso! Verifique a tabela de ajustes pendentes.');
            // Atualiza a lista de ajustes pendentes localmente
            const ajusteExistente = ajustesPendentes.find(a => a.codigo === currentProduto.codigo && a.numero_ajuste === currentNumeroAjuste);
            if (ajusteExistente) {
                ajusteExistente.quantidade += quantidade;
                console.log(`Produto ${currentProduto.codigo} já existe na lista. Nova quantidade: ${ajusteExistente.quantidade}`);
            } else {
                ajustesPendentes.push({
                    numero_ajuste: currentNumeroAjuste,
                    codigo: currentProduto.codigo,
                    descricao: currentProduto.descricao || 'Descrição não disponível',
                    quantidade: quantidade
                });
                console.log(`Produto ${currentProduto.codigo} adicionado à lista com quantidade: ${quantidade}`);
            }

            // Reseta o estado do modo massivo para o produto atual
            const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
            if (ajusteMassivoCheckbox.checked) {
                produtosMassivo = produtosMassivo.filter(p => p.codigo !== currentProduto.codigo); // Remove o produto ajustado
                document.getElementById('ajusteInput').value = '0'; // Reseta a quantidade exibida
                ultimoCodigoBipado = null; // Permite que o próximo bip reinicie a contagem
            } else {
                document.getElementById('ajusteInput').value = '0'; // Reseta para modo normal
            }

            atualizarListaPendentes();
        } else {
            console.error('Erro: Backend não confirmou sucesso:', result);
            alert('Erro ao adicionar ajuste pendente: resposta do backend não confirmou sucesso');
            throw new Error('Erro ao adicionar ajuste pendente: resposta do backend não confirmou sucesso');
        }
    } catch (err) {
        console.error('Erro ao adicionar ajuste:', err);
        alert(`Erro ao adicionar ajuste: ${err.message}`);
    }
}

function atualizarListaPendentes() {
    const tbody = document.getElementById('pendentesBody');
    tbody.innerHTML = '';
    ajustesPendentes.forEach(ajuste => {
        const tr = document.createElement('tr');
        const ajusteSymbol = ajuste.quantidade > 0 ? '+' : '-';
        tr.innerHTML = `
            <td>${ajuste.codigo}</td>
            <td>${ajuste.descricao}</td>
            <td>${ajusteSymbol}${ajuste.quantidade}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function confirmarAjuste() {
    if (ajustesPendentes.length === 0) {
        console.log('Nenhum ajuste pendente para confirmar.');
        alert('Nenhum ajuste pendente para confirmar.');
        return;
    }

    try {
        console.log('Enviando requisição POST para /confirmar-ajuste');
        console.log('Ajustes pendentes enviados:', JSON.stringify(ajustesPendentes, null, 2));
        const response = await fetch('/confirmar-ajuste', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ajustes: ajustesPendentes, numero_ajuste: currentNumeroAjuste })
        });
        console.log('Resposta recebida do backend:', response);

        if (!response.ok) {
            const errorData = await response.json();
            console.error(`Erro na requisição: ${response.status} ${response.statusText} - ${JSON.stringify(errorData)}`);
            throw new Error(errorData.error || `Erro na requisição: ${response.status} ${response.statusText}`);
        }

        const resultado = await response.json();
        console.log('Resultado retornado do backend:', resultado);

        if (resultado.success) {
            let mensagem = `Ajuste #${currentNumeroAjuste} realizado com sucesso!\n`;
            resultado.resultados.forEach(res => {
                mensagem += `Código: ${res.codigo}, Novo Saldo: ${res.saldo_atual}\n`;
            });
            alert(mensagem);

            ajustesPendentes = [];
            currentNumeroAjuste = null; // Reseta o numero_ajuste para criar um novo na próxima vez
            atualizarListaPendentes();
            document.getElementById('produtoInfo').innerHTML = '';
            document.getElementById('ajusteForm').style.display = 'none';
            currentProduto = null;
            produtosMassivo = [];
            ultimoCodigoBipado = null;
            carregarHistorico();
        } else {
            throw new Error('Erro ao realizar ajustes');
        }
    } catch (err) {
        console.error('Erro ao ajustar estoque:', err);
        alert(`Erro ao ajustar estoque: ${err.message}`);
    }
}

async function adicionarAjuste() {
    if (!currentProduto) {
        console.log('Nenhum produto selecionado para adicionar ao ajuste.');
        alert('Nenhum produto selecionado para adicionar ao ajuste.');
        return;
    }

    let quantidade = parseInt(document.getElementById('ajusteInput').value);
    console.log('Quantidade digitada:', quantidade);
    if (isNaN(quantidade) || quantidade === 0) {
        console.log('Quantidade inválida:', quantidade);
        alert('Por favor, digite uma quantidade válida.');
        return;
    }

    try {
        // Se não houver numero_ajuste, obtém um novo do backend
        if (!currentNumeroAjuste) {
            const response = await fetch('/proximo-numero-ajuste', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao obter número de ajuste');
            }
            currentNumeroAjuste = data.numero_ajuste;
            console.log(`Novo numero_ajuste obtido: ${currentNumeroAjuste}`);
        }

        // Adiciona o ajuste ao backend (tabela ajustes_pendentes)
        const ajuste = {
            numero_ajuste: currentNumeroAjuste,
            codigo: currentProduto.codigo,
            descricao: currentProduto.descricao || 'Descrição não disponível',
            quantidade: quantidade
        };

        const response = await fetch('/adicionar-ajuste-pendente', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ajuste)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Erro ao adicionar ajuste pendente');
        }

        const result = await response.json();
        if (result.success) {
            // Atualiza a lista de ajustes pendentes localmente
            const ajusteExistente = ajustesPendentes.find(a => a.codigo === currentProduto.codigo && a.numero_ajuste === currentNumeroAjuste);
            if (ajusteExistente) {
                ajusteExistente.quantidade += quantidade;
                console.log(`Produto ${currentProduto.codigo} já existe na lista. Nova quantidade: ${ajusteExistente.quantidade}`);
            } else {
                ajustesPendentes.push({
                    numero_ajuste: currentNumeroAjuste,
                    codigo: currentProduto.codigo,
                    descricao: currentProduto.descricao || 'Descrição não disponível',
                    quantidade: quantidade
                });
                console.log(`Produto ${currentProduto.codigo} adicionado à lista com quantidade: ${quantidade}`);
            }

            // Reseta o estado do modo massivo para o produto atual
            const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
            if (ajusteMassivoCheckbox.checked) {
                produtosMassivo = produtosMassivo.filter(p => p.codigo !== currentProduto.codigo); // Remove o produto ajustado
                document.getElementById('ajusteInput').value = '0'; // Reseta a quantidade exibida
                ultimoCodigoBipado = null; // Permite que o próximo bip reinicie a contagem
            } else {
                document.getElementById('ajusteInput').value = '0'; // Reseta para modo normal
            }

            atualizarListaPendentes();
        } else {
            throw new Error('Erro ao adicionar ajuste pendente');
        }
    } catch (err) {
        console.error('Erro ao adicionar ajuste:', err);
        alert(`Erro ao adicionar ajuste: ${err.message}`);
    }
}


async function carregarHistorico() {
    console.log('Executando carregarHistorico()');
    try {
        console.log('Enviando requisição GET para /historico');
        const response = await fetch('/historico');
        console.log('Resposta recebida do backend:', response);

        if (!response.ok) {
            const errorData = await response.json();
            console.error(`Erro na requisição: ${response.status} ${response.statusText} - ${JSON.stringify(errorData)}`);
            throw new Error(errorData.error || `Erro na requisição: ${response.status} ${response.statusText}`);
        }

        const historico = await response.json();
        console.log('Histórico retornado do backend:', historico);

        const tbody = document.getElementById('historicoBody');
        tbody.innerHTML = '';
        historico.forEach(item => {
            const tr = document.createElement('tr');
            const ajusteIcon = item.ajuste > 0 ? 'positive' : 'negative';
            const ajusteSymbol = item.ajuste > 0 ? '+' : '-';
            tr.innerHTML = `
                <td><span class="ajuste-icon ${ajusteIcon}">${ajusteSymbol}</span></td>
                <td>${item.id}</td>
                <td>${item.produto_codigo}</td>
                <td>${item.descricao || 'N/A'}</td>
                <td>${ajusteSymbol}${item.ajuste}</td>
                <td>${item.data_hora}</td>
                <td>${item.matricula || 'N/A'}</td>
                <td>${item.nome_usuario || 'N/A'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Erro ao carregar histórico:', err);
        alert(`Erro ao carregar histórico: ${err.message}`);
    }
}

const codigoInput = document.getElementById('codigoInput');

codigoInput.addEventListener('keydown', (event) => {
    console.log('Evento keydown detectado no codigoInput. Tecla:', event.key, 'Código:', event.keyCode);
    if (event.keyCode === 13 || event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        console.log('Enter bloqueado no codigoInput via keydown.');
        const codigo = event.target.value.trim();
        if (codigo) {
            console.log('Código detectado via Enter:', codigo);
            const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
            if (ajusteMassivoCheckbox.checked) {
                processarCodigoBarras(codigo);
            } else {
                buscarProduto();
            }
        }
    }
});

codigoInput.addEventListener('keypress', (event) => {
    console.log('Evento keypress detectado no codigoInput. Tecla:', event.key, 'Código:', event.keyCode);
    if (event.keyCode === 13 || event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        console.log('Enter bloqueado no codigoInput via keypress.');
    }
});

codigoInput.addEventListener('input', (event) => {
    const codigo = event.target.value.trim();
    console.log('Evento input detectado no codigoInput. Código no campo:', codigo);
    if (codigo && (codigo.endsWith('\n') || codigo.length >= 8)) {
        console.log('Código de barras detectado via input no codigoInput:', codigo);
        event.target.value = codigo.replace(/\n/g, '');
        const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
        setTimeout(() => {
            if (ajusteMassivoCheckbox.checked) {
                processarCodigoBarras(codigo);
            } else {
                buscarProduto();
            }
        }, 0);
    }
});

codigoInput.addEventListener('change', (event) => {
    const codigo = event.target.value.trim();
    console.log('Evento change detectado no codigoInput. Código no campo:', codigo);
    if (codigo) {
        console.log('Código de barras detectado via change no codigoInput:', codigo);
        event.target.value = codigo.replace(/\n/g, '');
        const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
        setTimeout(() => {
            if (ajusteMassivoCheckbox.checked) {
                processarCodigoBarras(codigo);
            } else {
                buscarProduto();
            }
        }, 0);
    }
});

document.getElementById('ajusteInput').addEventListener('input', () => {
    formatarQuantidade();
});

document.addEventListener('DOMContentLoaded', () => {
    console.log('Página carregada. Executando carregarHistorico().');
    carregarHistorico();
    document.getElementById('codigoInput').focus();
});

console.log('index.js carregado com sucesso.');





