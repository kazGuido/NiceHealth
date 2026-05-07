/**
 * Baileys (WhatsApp Web) HTTP bridge: send documents to E.164-like digit strings.
 * First run: scan QR printed in container logs. Session persisted in AUTH_DIR.
 * On session drop, POSTs to backend WEBHOOK_URL so owners/admins get email alerts.
 */
import express from 'express';
import multer from 'multer';
import pino from 'pino';
import makeWASocket, { DisconnectReason, useMultiFileAuthState } from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
const PORT = parseInt(process.env.PORT || '8765', 10);
const AUTH_DIR = process.env.AUTH_DIR || './auth_info';

const app = express();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 20 * 1024 * 1024 } });

let sock;
let isReady = false;
/** True once we have seen a successful connection (avoid alerting on close before first QR). */
let hadSuccessfulConnection = false;
/** True after we emailed session_lost until session_restored is sent. */
let disconnectAlertActive = false;

function formatDisconnectReason(lastDisconnect) {
  if (!lastDisconnect?.error) return 'unknown';
  const code = lastDisconnect.error?.output?.statusCode;
  const labels = {
    [DisconnectReason.badSession]: 'bad_session',
    [DisconnectReason.connectionClosed]: 'connection_closed',
    [DisconnectReason.connectionLost]: 'connection_lost',
    [DisconnectReason.connectionReplaced]: 'connection_replaced',
    [DisconnectReason.loggedOut]: 'logged_out',
    [DisconnectReason.restartRequired]: 'restart_required',
    [DisconnectReason.timedOut]: 'timed_out',
    [DisconnectReason.multideviceMismatch]: 'multidevice_mismatch',
  };
  const label = code !== undefined ? labels[code] : null;
  const msg = lastDisconnect.error?.message || '';
  if (label) return `${label}${msg ? `: ${msg}` : ''}`;
  return msg || String(lastDisconnect.error);
}

async function postWebhook(event, reason) {
  const url = process.env.WEBHOOK_URL?.trim();
  const secret = process.env.WEBHOOK_SECRET?.trim();
  if (!url || !secret) {
    logger.warn(
      'WEBHOOK_URL or WEBHOOK_SECRET not set — set WHATSAPP_BRIDGE_WEBHOOK_SECRET on backend and bridge for owner email alerts'
    );
    return;
  }
  const payload = JSON.stringify({
    event,
    reason: reason || null,
    at: new Date().toISOString(),
  });
  for (let attempt = 0; attempt < 5; attempt++) {
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Webhook-Secret': secret,
        },
        body: payload,
      });
      const text = await r.text();
      if (r.ok) {
        logger.info({ event, status: r.status }, 'monitor webhook delivered');
        return;
      }
      logger.warn({ attempt, status: r.status, body: text.slice(0, 500) }, 'monitor webhook rejected');
    } catch (e) {
      logger.warn({ attempt, err: e?.message || e }, 'monitor webhook fetch failed');
    }
    await new Promise((res) => setTimeout(res, 1500 * (attempt + 1)));
  }
  logger.error({ event }, 'monitor webhook failed after retries');
}

async function startSocket() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  sock = makeWASocket({
    auth: state,
    printQRInTerminal: true,
    logger: pino({ level: 'warn' }),
  });

  sock.ev.on('creds.update', saveCreds);
  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      qrcode.generate(qr, { small: true });
    }
    if (connection === 'open') {
      isReady = true;
      hadSuccessfulConnection = true;
      logger.info('WhatsApp connection open');
      if (disconnectAlertActive) {
        disconnectAlertActive = false;
        postWebhook('session_restored', 'connection_open').catch(() => {});
      }
    } else if (connection === 'close') {
      isReady = false;
      const reasonText = formatDisconnectReason(lastDisconnect);
      logger.warn({ lastDisconnect }, 'WhatsApp connection closed');
      if (hadSuccessfulConnection && !disconnectAlertActive) {
        disconnectAlertActive = true;
        postWebhook('session_lost', reasonText).catch(() => {});
      }
    }
  });
}

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', whatsappReady: isReady });
});

app.post('/send-document', upload.single('file'), async (req, res) => {
  try {
    if (!isReady || !sock) {
      return res.status(503).json({ error: 'WhatsApp not connected. Scan QR in container logs (first run).' });
    }
    const to = String(req.body?.to || '').replace(/\D/g, '');
    if (!to) {
      return res.status(400).json({ error: 'body field "to" (phone digits) is required' });
    }
    const file = req.file;
    if (!file || !file.buffer) {
      return res.status(400).json({ error: 'multipart file field "file" is required' });
    }
    const caption = String(req.body?.caption || '');
    const jid = `${to}@s.whatsapp.net`;
    await sock.sendMessage(jid, {
      document: file.buffer,
      mimetype: file.mimetype || 'application/pdf',
      fileName: file.originalname || 'rapport.pdf',
      caption: caption || undefined,
    });
    return res.json({ ok: true });
  } catch (e) {
    logger.error(e);
    return res.status(500).json({ error: String(e?.message || e) });
  }
});

startSocket()
  .then(() => {
    app.listen(PORT, '0.0.0.0', () => {
      logger.info({ PORT, AUTH_DIR }, 'whatsapp-bridge listening');
    });
  })
  .catch((e) => {
    logger.error(e, 'failed to start Baileys');
    process.exit(1);
  });
