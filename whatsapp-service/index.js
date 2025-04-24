// whatsapp-service/index.js
const { default: makeWASocket, DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const qrcode = require('qrcode-terminal');

// Configurações
const PORT = process.env.PORT || 3000;
const SESSION_DIR = './whatsapp-sessions';

// Criar diretório de sessões
if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
}

// Inicializar Express
const app = express();
app.use(bodyParser.json());

// Armazenar conexão ativa
let whatsappConnection = null;

// Função para conectar ao WhatsApp
async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
    
    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: true,
    });
    
    // Manipular eventos de conexão
    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;
        
        if (qr) {
            // Exibir QR code no terminal
            qrcode.generate(qr, { small: true });
            console.log('QR Code gerado. Escaneie para conectar ao WhatsApp');
        }
        
        if (connection === 'open') {
            console.log('Conexão com WhatsApp estabelecida!');
            whatsappConnection = sock;
        }
        
        if (connection === 'close') {
            const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
            
            if (shouldReconnect) {
                console.log('Reconectando ao WhatsApp...');
                connectToWhatsApp();
            }
        }
    });
    
    // Salvar credenciais quando atualizadas
    sock.ev.on('creds.update', saveCreds);
    
    return sock;
}

// Endpoint para enviar mensagem
app.post('/api/send-message', async (req, res) => {
    try {
        const { phone, message } = req.body;
        
        if (!phone || !message) {
            return res.status(400).json({
                success: false,
                message: 'Telefone e mensagem são obrigatórios'
            });
        }
        
        if (!whatsappConnection) {
            return res.status(503).json({
                success: false,
                message: 'Serviço WhatsApp não está conectado'
            });
        }
        
        // Formatar número de telefone
        const formattedPhone = formatPhoneNumber(phone);
        
        // Enviar mensagem
        const result = await whatsappConnection.sendMessage(formattedPhone, { text: message });
        
        res.status(200).json({
            success: true,
            message: 'Mensagem enviada com sucesso',
            messageId: result.key.id
        });
    } catch (error) {
        console.error('Erro ao enviar mensagem:', error);
        res.status(500).json({
            success: false,
            message: 'Erro ao enviar mensagem',
            error: error.message
        });
    }
});

// Endpoint para verificar status
app.get('/api/status', (req, res) => {
    res.status(200).json({
        success: true,
        connected: !!whatsappConnection,
        status: whatsappConnection ? 'connected' : 'disconnected'
    });
});

// Função para formatar número de telefone
function formatPhoneNumber(phone) {
    // Remover caracteres não numéricos
    let cleaned = phone.replace(/\D/g, '');
    
    // Adicionar código do país (55) se não estiver presente
    if (!cleaned.startsWith('55')) {
        cleaned = '55' + cleaned;
    }
    
    // Verificar se é um número brasileiro com 13 dígitos (55 + DDD + 9 + 8 dígitos)
    // Isso significa que é um celular com o 9 na frente
    if (cleaned.length === 13 && cleaned.startsWith('55')) {
        // Extrair o DDD (posições 2 e 3)
        const ddd = cleaned.substring(2, 4);
        
        // Verificar se o quinto dígito é 9 (posição após DDD)
        if (cleaned.charAt(4) === '9') {
            // Remover o dígito 9 inicial do número do celular
            // 55 (país) + DDD + restante sem o 9
            cleaned = '55' + ddd + cleaned.substring(5);
            console.log(`Número formatado: ${phone} → ${cleaned}`);
        }
    }

    return cleaned + '@s.whatsapp.net';
}

// Iniciar o servidor e conectar ao WhatsApp
app.listen(PORT, () => {
    console.log(`Servidor WhatsApp rodando na porta ${PORT}`);
    connectToWhatsApp();
});