let currentProduto = null;
let produtosMassivo = []; // Array para armazenar produtos no modo ajuste em massivo
let ultimoCodigoBipado = null; // Armazena o último código bipado para comparação

function focarCampo() {
    const codigoInput = document.getElementById('codigoInput');
    codigoInput.focus();
    console.log('Campo de código interno focado automaticamente.');
}

function atualizarAjusteMassivo() {
    const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
    if (ajusteMassivoCheckbox.checked) {
        console.log('Ajuste em Massivo ativado.');
        produtosMassivo = []; // Reseta a lista de produtos acumulados ao ativar o modo massivo
        ultimoCodigoBipado = null; // Reseta o último código bipado
    } else {
        console.log('Ajuste em Massivo desativado.');
        produtosMassivo = []; // Limpa a lista ao desativar o modo massivo
        document.getElementById('quantidadeInput').value = '0'; // Reseta o campo de quantidade
    }
}

function atualizarAjusteMassa() {
    const ajusteMenosCheckbox = document.getElementById('ajusteMenosCheckbox');
    const ajusteMaisCheckbox = document.getElementById('ajusteMaisCheckbox');
    const btnMenos = document.querySelector('.btn-menos');
    const btnMais = document.querySelector('.btn-mais');

    console.log(`Atualizar Ajuste Massa - Ajuste Menos: ${ajusteMenosCheckbox.checked}, Ajuste Mais: ${ajusteMaisCheckbox.checked}`);

    // Garante que apenas uma caixa de seleção (Mais ou Menos) esteja marcada
    if (ajusteMenosCheckbox.checked && ajusteMaisCheckbox.checked) {
        ajusteMaisCheckbox.checked = false; // Desmarca "Ajuste Mais" se "Ajuste Menos" for marcado
    }

    // Habilita/desabilita os botões com base nas caixas de seleção
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
        codigoInput.setAttribute('inputmode', 'none'); // Impede o teclado virtual
        codigoInput.focus(); // Garante que o campo possa ser selecionado
    } else {
        console.log('Ocultar Teclado desativado.');
        codigoInput.removeAttribute('inputmode'); // Volta ao comportamento normal
        codigoInput.focus(); // Garante que o campo possa ser selecionado
    }
}

function formatarQuantidade() {
    const ajusteMenosCheckbox = document.getElementById('ajusteMenosCheckbox');
    const ajusteMaisCheckbox = document.getElementById('ajusteMaisCheckbox');
    let quantidade = parseInt(document.getElementById('quantidadeInput').value) || 0;

    console.log(`Formatar Quantidade - Quantidade atual: ${quantidade}, Ajuste Menos: ${ajusteMenosCheckbox.checked}, Ajuste Mais: ${ajusteMaisCheckbox.checked}`);

    // Remove qualquer sinal da quantidade digitada (trata como valor absoluto)
    quantidade = Math.abs(quantidade);

    // Aplica o sinal com base na caixa marcada
    if (ajusteMenosCheckbox.checked) {
        document.getElementById('quantidadeInput').value = -quantidade;
    } else {
        document.getElementById('quantidadeInput').value = quantidade;
    }
    console.log(`Quantidade formatada para: ${document.getElementById('quantidadeInput').value}`);
}

async function buscarProduto() {
    const codigo = document.getElementById('codigoInput').value.trim();
    if (!codigo) {
        console.log('Nenhum código fornecido para busca.');
        alert('Por favor, digite um código para buscar.');
        return;
    }

    try {
        console.log(`Buscando produto com código: ${codigo}`);
        const response = await fetch(`/produto/${codigo}`);
        const produto = await response.json();
        if (produto.error) {
            throw new Error(produto.error);
        }
        currentProduto = produto;

        console.log('Produto retornado do backend:', produto);
        console.log('Descrição do produto:', produto.descricao);

        // Atualiza os detalhes do produto na interface
        document.getElementById('codigoInterno').textContent = produto.codigo || 'N/A';
        document.getElementById('codigoBarras').textContent = produto.barras || 'N/A';
        document.getElementById('descricao').textContent = produto.descricao || 'Descrição não disponível';
        document.getElementById('saldo').textContent = produto.saldo_atual || '0';
        document.getElementById('detalhes-produto').style.display = 'block';

        // Confirma que a seção detalhes-produto está visível
        console.log('Seção detalhes-produto visível:', document.getElementById('detalhes-produto').style.display);

        // Confirma que o botão Confirmar está presente
        const btnConfirmar = document.querySelector('.btn-confirmar');
        console.log('Botão Confirmar encontrado:', btnConfirmar);
        if (btnConfirmar) {
            console.log('Botão Confirmar visível:', window.getComputedStyle(btnConfirmar).display !== 'none');
        }

        // Se não estiver em modo massivo, reseta a quantidade
        const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
        if (!ajusteMassivoCheckbox.checked) {
            document.getElementById('quantidadeInput').value = '0';
        }

        // Limpa o campo de entrada após a busca
        document.getElementById('codigoInput').value = '';
        carregarHistorico();
    } catch (err) {
        console.error('Erro ao buscar produto:', err);
        alert('Erro ao buscar produto: ' + err.message);
        // Limpa os campos e esconde a seção de detalhes
        document.getElementById('codigoInterno').textContent = '';
        document.getElementById('codigoBarras').textContent = '';
        document.getElementById('descricao').textContent = '';
        document.getElementById('saldo').textContent = '';
        document.getElementById('detalhes-produto').style.display = 'none';
        currentProduto = null;
        // Limpa o campo de entrada
        document.getElementById('codigoInput').value = '';
    }
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

        // Atualiza o currentProduto para o último produto bipado
        currentProduto = produto;

        // Lógica de ajuste em massivo
        const ajusteMassivoCheckbox = document.getElementById('ajusteMassivoCheckbox');
        if (ajusteMassivoCheckbox.checked) {
            const ajusteMenosCheckbox = document.getElementById('ajusteMenosCheckbox');
            const ajusteMaisCheckbox = document.getElementById('ajusteMaisCheckbox');

            console.log('Ajuste em Massivo ativo. Ajuste Menos:', ajusteMenosCheckbox.checked, 'Ajuste Mais:', ajusteMaisCheckbox.checked);

            // Verifica se o produto já foi bipado
            const produtoExistente = produtosMassivo.find(p => p.codigo === produto.codigo);
            if (produtoExistente) {
                // Incrementa a quantidade se for o mesmo produto
                produtoExistente.quantidade += 1;
            } else {
                // Adiciona o novo produto à lista
                produtosMassivo.push({ codigo: produto.codigo, quantidade: 1 });
            }

            // Calcula a quantidade total acumulada
            const quantidadeTotal = produtosMassivo.reduce((total, p) => total + p.quantidade, 0);
            console.log('Produtos acumulados:', produtosMassivo);
            console.log('Quantidade total acumulada:', quantidadeTotal);

            // Aplica a direção do ajuste (mais ou menos)
            if (ajusteMenosCheckbox.checked) {
                document.getElementById('quantidadeInput').value = -quantidadeTotal;
            } else {
                document.getElementById('quantidadeInput').value = quantidadeTotal;
            }
            console.log('Quantidade atualizada no campo:', document.getElementById('quantidadeInput').value);

            // Atualiza o último código bipado
            ultimoCodigoBipado = codigo;
        }

        // Limpa o campo de entrada após processar
        document.getElementById('codigoInput').value = '';
    } catch (err) {
        console.error('Erro ao processar código de barras:', err);
        alert('Erro ao processar código de barras: ' + err.message);
        // Limpa o campo de entrada
        document.getElementById('codigoInput').value = '';
    }
}

function alterarQuantidade(operacao) {
    const ajusteMenosCheckbox = document.getElementById('ajusteMenosCheckbox');
    const ajusteMaisCheckbox = document.getElementById('ajusteMaisCheckbox');
    let quantidade = parseInt(document.getElementById('quantidadeInput').value) || 0;

    console.log(`Alterar quantidade - Operação: ${operacao}, Quantidade atual: ${quantidade}, Ajuste Menos: ${ajusteMenosCheckbox.checked}, Ajuste Mais: ${ajusteMaisCheckbox.checked}`);

    // Verifica se a operação é permitida com base nas caixas de seleção
    if (ajusteMenosCheckbox.checked && operacao !== 'menos') {
        alert('Apenas ajustes de diminuição são permitidos com "Ajuste Menos" marcado.');
        return;
    }
    if (ajusteMaisCheckbox.checked && operacao !== 'mais') {
        alert('Apenas ajustes de aumento são permitidos com "Ajuste Mais" marcado.');
        return;
    }

    // Ajusta a quantidade com base na operação
    if (operacao === 'mais') {
        // Incrementa a quantidade (sempre positiva ou zero)
        quantidade += 1;
    } else if (operacao === 'menos') {
        // Diminui a quantidade, permitindo valores negativos em qualquer caso
        quantidade -= 1; // Permite -1, -2, -3, etc., independentemente de "Ajuste Menos"
    }

    // Atualiza o campo de quantidade
    document.getElementById('quantidadeInput').value = quantidade;
    console.log(`Quantidade atualizada para: ${quantidade}`);
}

async function confirmarAjuste() {
    if (!currentProduto) {
        console.log('Nenhum produto selecionado para ajuste.');
        alert('Nenhum produto selecionado para ajuste.');
        return;
    }

    let ajuste = parseInt(document.getElementById('quantidadeInput').value);
    console.log('Quantidade digitada:', ajuste);
    if (isNaN(ajuste) || ajuste === 0) {
        console.log('Quantidade inválida:', ajuste);
        alert('Por favor, digite uma quantidade válida.');
        return;
    }

    try {
        const payload = { codigo: currentProduto.codigo, ajuste };
        console.log('Enviando requisição para /ajustar-estoque com payload:', payload);
        const response = await fetch('/ajustar-estoque', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`Erro na requisição: ${response.status} ${response.statusText}`);
        }

        const updatedProduto = await response.json();
        console.log('Resposta do backend:', updatedProduto);
        console.log('Descrição do produto atualizado:', updatedProduto.descricao);
        if (updatedProduto.error) {
            throw new Error(updatedProduto.error);
        }
        currentProduto = updatedProduto;

        // Atualiza os detalhes do produto após o ajuste
        document.getElementById('codigoInterno').textContent = updatedProduto.codigo || 'N/A';
        document.getElementById('codigoBarras').textContent = updatedProduto.barras || 'N/A';
        document.getElementById('descricao').textContent = updatedProduto.descricao || 'Descrição não disponível';
        document.getElementById('saldo').textContent = updatedProduto.saldo_atual || '0';
        document.getElementById('detalhes-produto').style.display = 'block';

        document.getElementById('quantidadeInput').value = '0'; // Reseta o campo

        // Reseta a lista de produtos acumulados
        produtosMassivo = [];
        ultimoCodigoBipado = null;

        carregarHistorico();
    } catch (err) {
        console.error('Erro ao ajustar estoque:', err);
        alert('Erro ao ajustar estoque: ' + err.message);
    }
}

async function carregarHistorico() {
    try {
        const response = await fetch('/historico');
        const historico = await response.json();
        const lista = document.getElementById('historico-lista');
        lista.innerHTML = '';

        historico.forEach(item => {
            const li = document.createElement('li');
            const ajusteIcon = item.ajuste > 0 ? 'positive' : 'negative';
            const ajusteSymbol = item.ajuste > 0 ? '+' : '';
            li.innerHTML = `
                <span class="ajuste-icon ${ajusteIcon}">${ajusteSymbol}</span>
                Produto - Código Interno: ${item.produto_codigo}<br>
                Ajuste: ${ajusteSymbol}${item.ajuste} unidades<br>
                Usuário: ${item.nome_usuario} (Matrícula: ${item.matricula})<br>
                ${item.data_hora}
            `;
            lista.appendChild(li);
        });
    } catch (err) {
        console.error('Erro ao carregar histórico:', err);
    }
}

async function logout() {
    try {
        const response = await fetch('/logout');
        if (response.ok) {
            console.log('Logout bem-sucedido. Redirecionando para login.');
            window.location.href = '/login';
        } else {
            console.error('Erro ao fazer logout.');
            alert('Erro ao fazer logout. Tente novamente.');
        }
    } catch (err) {
        console.error('Erro ao fazer logout:', err);
        alert('Erro ao fazer logout. Tente novamente.');
    }
}

// Adiciona eventos ao campo codigoInput
const codigoInput = document.getElementById('codigoInput');

// Evento keydown para capturar o Enter
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

// Evento keypress para capturar o Enter
codigoInput.addEventListener('keypress', (event) => {
    console.log('Evento keypress detectado no codigoInput. Tecla:', event.key, 'Código:', event.keyCode);
    if (event.keyCode === 13 || event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        console.log('Enter bloqueado no codigoInput via keypress.');
    }
});

// Adiciona um evento de input para capturar o código de barras no codigoInput
codigoInput.addEventListener('input', (event) => {
    const codigo = event.target.value.trim();
    console.log('Evento input detectado no codigoInput. Código no campo:', codigo);
    // Ajusta a condição para ser mais flexível (aceita códigos de qualquer tamanho >= 8 dígitos ou com \n)
    if (codigo && (codigo.endsWith('\n') || codigo.length >= 8)) {
        console.log('Código de barras detectado via input no codigoInput:', codigo);
        event.target.value = codigo.replace(/\n/g, ''); // Remove caracteres de nova linha
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

// Adiciona um evento change como alternativa para capturar o código no codigoInput
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

// Adiciona um evento input no campo quantidadeInput para formatar a quantidade
document.getElementById('quantidadeInput').addEventListener('input', () => {
    formatarQuantidade();
});

// Adiciona um evento keypress global para depuração e prevenção
document.addEventListener('keypress', (event) => {
    console.log('Tecla pressionada (keypress global):', event.key, 'Código:', event.keyCode);
    if (event.keyCode === 13 || event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        console.log('Enter bloqueado globalmente via keypress.');
    }
});

// Adiciona um evento keydown global para capturar o Enter e evitar recarregamento
document.addEventListener('keydown', (event) => {
    console.log('Evento keydown global detectado. Tecla:', event.key, 'Código:', event.keyCode);
    if (event.keyCode === 13 || event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        console.log('Enter bloqueado globalmente via keydown.');
    }
});

// Adiciona um evento submit global para evitar qualquer submissão
document.addEventListener('submit', (event) => {
    event.preventDefault();
    event.stopPropagation();
    console.log('Submissão de formulário bloqueada globalmente.');
});

// Adiciona um evento beforeunload para depurar recarregamentos
window.addEventListener('beforeunload', (event) => {
    console.log('Página está sendo recarregada ou fechada.');
    // Para depuração, não bloqueamos o recarregamento aqui, apenas logamos
});