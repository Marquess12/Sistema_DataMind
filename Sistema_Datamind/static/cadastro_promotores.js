// static/cadastro_promotores.js

function adicionarHorario(codigoLoja) {
  const container = document.getElementById(`horarios-loja-${codigoLoja}`);
  const div = document.createElement("div");
  div.className = "horario-entry";

  // O atributo 'name' é crucial para o Flask receber os dados corretamente em listas
  div.innerHTML = `
        <select name="loja_${codigoLoja}_dia_semana[]" class="form-control" required>
            <option value="" disabled selected>Selecione o Dia</option>
            <option value="segunda">Segunda-feira</option>
            <option value="terca">Terça-feira</option>
            <option value="quarta">Quarta-feira</option>
            <option value="quinta">Quinta-feira</option>
            <option value="sexta">Sexta-feira</option>
            <option value="sabado">Sábado</option>
            <option value="domingo">Domingo</option>
        </select>
        <input type="time" name="loja_${codigoLoja}_entrada[]" class="form-control" title="Horário de Entrada" required>
        <input type="time" name="loja_${codigoLoja}_saida[]" class="form-control" title="Horário de Saída" required>
        <input type="time" name="loja_${codigoLoja}_intervalo[]" class="form-control" title="Início do Intervalo">
        <button type="button" class="btn-remover" onclick="this.parentElement.remove()" title="Remover Horário">×</button>
    `;
  container.appendChild(div);
}
