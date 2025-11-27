function formatarTelefone(numero) {
    // Remove o código de país +55, se existir
    if (numero.startsWith('+55')) {
        numero = numero.slice(3);  // Remove os primeiros 3 caracteres, ou seja, o +55
    }

    // Remove todos os caracteres que não são dígitos
    numero = numero.replace(/\D/g, '');

    // Verifica se o número tem 10 ou 11 dígitos (fixo ou celular)
    if (numero.length === 10) {
        // Formato para números fixos (XXXX-XXXX)
        numero = numero.replace(/^(\d{2})(\d{4})(\d{4})$/, "($1) $2-$3");
    } else if (numero.length === 11) {
        // Formato para números de celular (XXXXX-XXXX)
        numero = numero.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
    } else {
        // Caso o número não tenha 10 ou 11 dígitos, retorne como está
        return numero;
    }

    return numero;
}



document.addEventListener('DOMContentLoaded', function() {
    // Seleciona todas as células da tabela com a classe 'telefone'
    let telefones = document.querySelectorAll('.contato');
    
    // Itera sobre cada célula de telefone e formata o número
    telefones.forEach(function(celula) {
        let numero = celula.textContent;  // Pega o conteúdo da célula
        let numeroFormatado = formatarTelefone(numero);  // Formata o telefone
        celula.textContent = numeroFormatado;  // Atualiza o valor da célula com o telefone formatado
    });
})

