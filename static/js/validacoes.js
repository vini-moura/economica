document.getElementById('conta').addEventListener('blur', function() {
    var conta = this.value;
    fetch('/verificar_conta?conta=' + conta)
        .then(response => response.json())
        .then(data => {
            if (data.exists) {
                alert('A conta informada já está em uso. Por favor, escolha outra.');
            }
        });
});

document.getElementById('cod_bolsa').addEventListener('blur', function() {
    var codBolsa = this.value;
    fetch('/verificar_cod_bolsa?cod_bolsa=' + codBolsa)
        .then(response => response.json())
        .then(data => {
            if (data.exists) {
                alert('O código da bolsa informado já está em uso. Por favor, escolha outro.');
            }
        });
});
