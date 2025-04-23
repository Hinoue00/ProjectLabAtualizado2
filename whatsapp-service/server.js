const { create, Client } = require('@open-wa/wa-automate');
const express = require('express');
const cors = require('cors');

// Configuração do Express
const app = express();
app.use(cors());
app.use(express.json());
const PORT = 3000;

// Cliente WhatsApp
let whatsappClient = null;

// Iniciar o cliente WhatsApp
const startWhatsApp = async () => {
    const client = await create({
        sessionId: 'labconnect',
        multiDevice: true, // Suporte a multi-dispositivos
        authTimeout: 60, // Tempo para escanear o QR code
        headless: true, // Executa o navegador sem interface gráfica
        useChrome: true,
        qrTimeout: 0 // Sem timeout para o QR code
    });
    
    whatsappClient = client;
    console.log('Cliente WhatsApp iniciado!');
    
    // Gera QR Code para autenticação
    client.onStateChanged(state => {
        if (state === 'CONFLICT' || state === 'UNLAUNCHED') client.forceRefocus();
        if (state === 'UNPAIRED') console.log('Por favor escaneie o QR code novamente!');
    });
    
    return client;
};

// Iniciar a API
startWhatsApp().then(client => {
    // Endpoint para enviar mensagem
    app.post('/send-message', async (req, res) => {
        try {
            const { phoneNumber, message } = req.body;
            
            // Formatar número para WhatsApp
            const formattedNumber = phoneNumber.replace(/\D/g, '');
            
            // Verificar se o número existe no WhatsApp
            const numberExists = await client.checkNumberStatus(`${formattedNumber}@c.us`);
            if (!numberExists.canReceiveMessage) {
                return res.status(400).json({ success: false, message: 'Número não encontrado no WhatsApp' });
            }
            
            // Enviar mensagem
            const response = await client.sendText(`${formattedNumber}@c.us`, message);
            res.json({ success: true, response });
        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            res.status(500).json({ success: false, error: error.message });
        }
    });

    // Iniciar o servidor
    app.listen(PORT, () => {
        console.log(`Servidor rodando na porta ${PORT}`);
    });
});