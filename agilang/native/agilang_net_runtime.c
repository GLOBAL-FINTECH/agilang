#include "agilang_net_runtime.h"
#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <process.h>
#pragma comment(lib, "ws2_32.lib")
typedef SOCKET agi_socket_t;
#define AGI_INVALID_SOCKET INVALID_SOCKET
#define AGI_CLOSE closesocket
#define AGI_THREAD_RETURN unsigned __stdcall
#else
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <sys/socket.h>
#include <unistd.h>
typedef int agi_socket_t;
#define AGI_INVALID_SOCKET (-1)
#define AGI_CLOSE close
#define AGI_THREAD_RETURN void*
#endif

#define AGI_WS_GUID "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
#define AGI_WS_DEFAULT_MAX_FRAME (1024u * 1024u)
#define AGI_WS_MAX_HEADER 65536

struct agi_ws_peer {
    agi_socket_t fd;
    int connected;
    struct agi_ws_server *server;
    struct agi_ws_peer *next;
#ifdef _WIN32
    HANDLE thread;
#else
    pthread_t thread;
#endif
};

struct agi_ws_server {
    agi_socket_t fd;
    agi_ws_server_config cfg;
    int running;
    agi_ws_peer *peers;
#ifdef _WIN32
    HANDLE accept_thread;
    CRITICAL_SECTION lock;
#else
    pthread_t accept_thread;
    pthread_mutex_t lock;
#endif
};

static agi_ws_server *g_default_server = NULL;

static int agi_net_init(void) {
#ifdef _WIN32
    static int ready = 0;
    if (ready) return 0;
    WSADATA wsa;
    int rc = WSAStartup(MAKEWORD(2,2), &wsa);
    if (rc == 0) ready = 1;
    return rc;
#else
    return 0;
#endif
}

static void agi_lock(agi_ws_server *s) {
#ifdef _WIN32
    EnterCriticalSection(&s->lock);
#else
    pthread_mutex_lock(&s->lock);
#endif
}
static void agi_unlock(agi_ws_server *s) {
#ifdef _WIN32
    LeaveCriticalSection(&s->lock);
#else
    pthread_mutex_unlock(&s->lock);
#endif
}

static uint32_t rol32(uint32_t value, uint32_t bits) { return (value << bits) | (value >> (32 - bits)); }

static void sha1(const uint8_t *data, size_t len, uint8_t out[20]) {
    uint32_t h0 = 0x67452301, h1 = 0xEFCDAB89, h2 = 0x98BADCFE, h3 = 0x10325476, h4 = 0xC3D2E1F0;
    uint64_t bit_len = (uint64_t)len * 8u;
    size_t new_len = len + 1;
    while ((new_len % 64) != 56) new_len++;
    uint8_t *msg = (uint8_t*)calloc(new_len + 8, 1);
    if (!msg) return;
    memcpy(msg, data, len);
    msg[len] = 0x80;
    for (int i = 0; i < 8; i++) msg[new_len + i] = (uint8_t)((bit_len >> (56 - 8*i)) & 0xff);
    for (size_t offset = 0; offset < new_len + 8; offset += 64) {
        uint32_t w[80];
        for (int i = 0; i < 16; i++) {
            w[i] = ((uint32_t)msg[offset + i*4] << 24) | ((uint32_t)msg[offset+i*4+1] << 16) | ((uint32_t)msg[offset+i*4+2] << 8) | msg[offset+i*4+3];
        }
        for (int i = 16; i < 80; i++) w[i] = rol32(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1);
        uint32_t a=h0,b=h1,c=h2,d=h3,e=h4;
        for (int i=0; i<80; i++) {
            uint32_t f,k;
            if (i<20) { f=(b & c) | ((~b) & d); k=0x5A827999; }
            else if (i<40) { f=b ^ c ^ d; k=0x6ED9EBA1; }
            else if (i<60) { f=(b & c) | (b & d) | (c & d); k=0x8F1BBCDC; }
            else { f=b ^ c ^ d; k=0xCA62C1D6; }
            uint32_t temp = rol32(a,5) + f + e + k + w[i];
            e=d; d=c; c=rol32(b,30); b=a; a=temp;
        }
        h0 += a; h1 += b; h2 += c; h3 += d; h4 += e;
    }
    free(msg);
    uint32_t hs[5] = {h0,h1,h2,h3,h4};
    for (int i=0; i<5; i++) { out[i*4]=(uint8_t)(hs[i]>>24); out[i*4+1]=(uint8_t)(hs[i]>>16); out[i*4+2]=(uint8_t)(hs[i]>>8); out[i*4+3]=(uint8_t)hs[i]; }
}

static const char B64[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
static void base64_encode(const uint8_t *in, size_t len, char *out, size_t outsz) {
    size_t j=0;
    for (size_t i=0; i<len && j+4<outsz; i+=3) {
        uint32_t v = (uint32_t)in[i] << 16;
        if (i+1 < len) v |= (uint32_t)in[i+1] << 8;
        if (i+2 < len) v |= in[i+2];
        out[j++] = B64[(v >> 18) & 63];
        out[j++] = B64[(v >> 12) & 63];
        out[j++] = (i+1 < len) ? B64[(v >> 6) & 63] : '=';
        out[j++] = (i+2 < len) ? B64[v & 63] : '=';
    }
    out[j] = 0;
}

static void ws_accept_key(const char *key, char out[64]) {
    char combo[256];
    uint8_t digest[20];
    snprintf(combo, sizeof(combo), "%s%s", key, AGI_WS_GUID);
    sha1((const uint8_t*)combo, strlen(combo), digest);
    base64_encode(digest, 20, out, 64);
}

static int recv_until_header(agi_socket_t fd, char *buf, size_t max) {
    size_t used = 0;
    while (used + 1 < max) {
        int n = (int)recv(fd, buf + used, 1, 0);
        if (n <= 0) return -1;
        used += (size_t)n;
        buf[used] = 0;
        if (used >= 4 && strstr(buf, "\r\n\r\n")) return (int)used;
    }
    return -2;
}

static int header_value(const char *headers, const char *name, char *out, size_t outsz) {
    size_t name_len = strlen(name);
    const char *p = headers;
    while (*p) {
        const char *line_end = strstr(p, "\r\n");
        if (!line_end) break;
        const char *colon = memchr(p, ':', (size_t)(line_end - p));
        if (colon && (size_t)(colon - p) == name_len) {
            int match = 1;
            for (size_t i=0; i<name_len; i++) if (tolower((unsigned char)p[i]) != tolower((unsigned char)name[i])) match = 0;
            if (match) {
                const char *v = colon + 1;
                while (*v == ' ' || *v == '\t') v++;
                size_t n = (size_t)(line_end - v);
                if (n >= outsz) n = outsz - 1;
                memcpy(out, v, n); out[n] = 0; return 1;
            }
        }
        p = line_end + 2;
    }
    return 0;
}

static int path_matches(const char *request_target, const char *required_path) {
    char path[1024];
    size_t n = 0;
    while (request_target[n] && request_target[n] != '?' && n + 1 < sizeof(path)) { path[n] = request_target[n]; n++; }
    path[n] = 0;
    return strcmp(path, required_path ? required_path : "/") == 0;
}

static int token_matches(const char *request_target, const char *token) {
    if (!token || !*token) return 1;
    const char *q = strchr(request_target, '?');
    if (!q) return 0;
    q++;
    char needle[512];
    snprintf(needle, sizeof(needle), "token=%s", token);
    return strstr(q, needle) != NULL;
}

static int ws_handshake(agi_ws_server *server, agi_socket_t fd) {
    char req[AGI_WS_MAX_HEADER];
    if (recv_until_header(fd, req, sizeof(req)) < 0) return -1;
    char method[16] = {0}, target[1024] = {0}, version[16] = {0};
    if (sscanf(req, "%15s %1023s %15s", method, target, version) != 3) return -2;
    if (strcmp(method, "GET") != 0 || !path_matches(target, server->cfg.path) || !token_matches(target, server->cfg.auth_token)) return -3;
    char key[256], upgrade[64], version_h[32], origin[512];
    if (!header_value(req, "sec-websocket-key", key, sizeof(key))) return -4;
    if (!header_value(req, "upgrade", upgrade, sizeof(upgrade))) return -5;
    if (!header_value(req, "sec-websocket-version", version_h, sizeof(version_h)) || strcmp(version_h, "13") != 0) return -6;
    if (server->cfg.allowed_origin && *server->cfg.allowed_origin) {
        if (!header_value(req, "origin", origin, sizeof(origin)) || strcmp(origin, server->cfg.allowed_origin) != 0) return -7;
    }
    char accept[64]; ws_accept_key(key, accept);
    char resp[512];
    int n = snprintf(resp, sizeof(resp), "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n", accept);
    return send(fd, resp, n, 0) == n ? 0 : -8;
}

static int ws_write_frame(agi_socket_t fd, uint8_t opcode, const char *payload) {
    size_t len = payload ? strlen(payload) : 0;
    uint8_t header[10]; size_t hlen = 0;
    header[0] = 0x80 | (opcode & 0x0f);
    if (len < 126) { header[1] = (uint8_t)len; hlen = 2; }
    else if (len <= 65535) { header[1] = 126; header[2] = (uint8_t)(len >> 8); header[3] = (uint8_t)len; hlen = 4; }
    else { header[1] = 127; for (int i=0;i<8;i++) header[2+i] = (uint8_t)(len >> (56 - i*8)); hlen = 10; }
    if (send(fd, (const char*)header, (int)hlen, 0) != (int)hlen) return -1;
    if (len && send(fd, payload, (int)len, 0) != (int)len) return -2;
    return 0;
}

static int recv_all(agi_socket_t fd, uint8_t *buf, size_t len) {
    size_t got = 0;
    while (got < len) {
        int n = (int)recv(fd, (char*)buf + got, (int)(len - got), 0);
        if (n <= 0) return -1;
        got += (size_t)n;
    }
    return 0;
}

static int ws_read_text(agi_ws_server *server, agi_socket_t fd, char **out) {
    uint8_t h[2];
    if (recv_all(fd, h, 2) != 0) return -1;
    uint8_t opcode = h[0] & 0x0f;
    int masked = h[1] & 0x80;
    uint64_t len = h[1] & 0x7f;
    if ((h[0] & 0x80) == 0) return -2;
    if (len == 126) { uint8_t e[2]; if (recv_all(fd,e,2)!=0) return -1; len = ((uint64_t)e[0]<<8)|e[1]; }
    else if (len == 127) { uint8_t e[8]; if (recv_all(fd,e,8)!=0) return -1; len=0; for (int i=0;i<8;i++) len=(len<<8)|e[i]; }
    size_t max = server->cfg.max_frame_bytes ? server->cfg.max_frame_bytes : AGI_WS_DEFAULT_MAX_FRAME;
    if (len > max) return -3;
    uint8_t mask[4] = {0,0,0,0};
    if (!masked && opcode != 0x8) return -4; /* client-to-server frames must be masked */
    if (masked && recv_all(fd, mask, 4) != 0) return -1;
    char *payload = (char*)calloc((size_t)len + 1, 1);
    if (!payload) return -5;
    if (len && recv_all(fd, (uint8_t*)payload, (size_t)len) != 0) { free(payload); return -1; }
    if (masked) for (uint64_t i=0; i<len; i++) payload[i] = (char)(((uint8_t)payload[i]) ^ mask[i % 4]);
    if (opcode == 0x8) { free(payload); return 1; }
    if (opcode == 0x9) { ws_write_frame(fd, 0xA, payload); free(payload); return 2; }
    if (opcode != 0x1) { free(payload); return -6; }
    *out = payload;
    return 0;
}

int agi_ws_peer_send_text(agi_ws_peer *peer, const char *message) {
    if (!peer || !peer->connected) return -1;
    return ws_write_frame(peer->fd, 0x1, message ? message : "");
}

int agi_ws_peer_close(agi_ws_peer *peer) {
    if (!peer) return -1;
    peer->connected = 0;
    ws_write_frame(peer->fd, 0x8, "");
    AGI_CLOSE(peer->fd);
    return 0;
}

int agi_ws_server_broadcast(agi_ws_server *server, const char *message) {
    if (!server) return -1;
    int delivered = 0;
    agi_lock(server);
    for (agi_ws_peer *p = server->peers; p; p = p->next) {
        if (p->connected && agi_ws_peer_send_text(p, message) == 0) delivered++;
    }
    agi_unlock(server);
    return delivered;
}

static AGI_THREAD_RETURN ws_client_thread(void *arg) {
    agi_ws_peer *peer = (agi_ws_peer*)arg;
    agi_ws_server *server = peer->server;
    if (server->cfg.on_connect) server->cfg.on_connect(peer, server->cfg.userdata);
    while (server->running && peer->connected) {
        char *msg = NULL;
        int rc = ws_read_text(server, peer->fd, &msg);
        if (rc == 0) {
            if (server->cfg.on_message) server->cfg.on_message(peer, msg, server->cfg.userdata);
            free(msg);
        } else if (rc == 2) {
            continue;
        } else {
            break;
        }
    }
    peer->connected = 0;
    if (server->cfg.on_disconnect) server->cfg.on_disconnect(peer, server->cfg.userdata);
    AGI_CLOSE(peer->fd);
    agi_lock(server);
    agi_ws_peer **cur = &server->peers;
    while (*cur) {
        if (*cur == peer) { *cur = peer->next; break; }
        cur = &((*cur)->next);
    }
    agi_unlock(server);
    free(peer);
#ifdef _WIN32
    return 0;
#else
    return NULL;
#endif
}

static AGI_THREAD_RETURN ws_accept_thread(void *arg) {
    agi_ws_server *server = (agi_ws_server*)arg;
    while (server->running) {
        agi_socket_t client = accept(server->fd, NULL, NULL);
        if (client == AGI_INVALID_SOCKET) continue;
        if (ws_handshake(server, client) != 0) { AGI_CLOSE(client); continue; }
        agi_ws_peer *peer = (agi_ws_peer*)calloc(1, sizeof(*peer));
        if (!peer) { AGI_CLOSE(client); continue; }
        peer->fd = client; peer->connected = 1; peer->server = server;
        agi_lock(server); peer->next = server->peers; server->peers = peer; agi_unlock(server);
#ifdef _WIN32
        peer->thread = (HANDLE)_beginthreadex(NULL, 0, ws_client_thread, peer, 0, NULL);
#else
        pthread_create(&peer->thread, NULL, ws_client_thread, peer);
        pthread_detach(peer->thread);
#endif
    }
#ifdef _WIN32
    return 0;
#else
    return NULL;
#endif
}

int agi_ws_server_start(agi_ws_server **out, const agi_ws_server_config *config) {
    if (!out || !config) return -1;
    if (agi_net_init() != 0) return -2;
    agi_ws_server *s = (agi_ws_server*)calloc(1, sizeof(*s));
    if (!s) return -3;
    s->cfg = *config;
    if (!s->cfg.path) s->cfg.path = "/";
    if (!s->cfg.host) s->cfg.host = "127.0.0.1";
    if (!s->cfg.backlog) s->cfg.backlog = 128;
#ifdef _WIN32
    InitializeCriticalSection(&s->lock);
#else
    pthread_mutex_init(&s->lock, NULL);
#endif
    s->fd = socket(AF_INET, SOCK_STREAM, 0);
    if (s->fd == AGI_INVALID_SOCKET) { free(s); return -4; }
    int opt = 1;
#ifdef _WIN32
    setsockopt(s->fd, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
#else
    setsockopt(s->fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
#endif
    struct sockaddr_in addr; memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)s->cfg.port);
    addr.sin_addr.s_addr = inet_addr(s->cfg.host);
    if (addr.sin_addr.s_addr == INADDR_NONE) addr.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(s->fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) { AGI_CLOSE(s->fd); free(s); return -5; }
    if (listen(s->fd, s->cfg.backlog) < 0) { AGI_CLOSE(s->fd); free(s); return -6; }
    s->running = 1;
#ifdef _WIN32
    s->accept_thread = (HANDLE)_beginthreadex(NULL, 0, ws_accept_thread, s, 0, NULL);
#else
    pthread_create(&s->accept_thread, NULL, ws_accept_thread, s);
#endif
    *out = s;
    return 0;
}

int agi_ws_server_stop(agi_ws_server *server) {
    if (!server) return -1;
    server->running = 0;
    AGI_CLOSE(server->fd);
    agi_lock(server);
    agi_ws_peer *p = server->peers;
    while (p) { p->connected = 0; AGI_CLOSE(p->fd); p = p->next; }
    agi_unlock(server);
#ifdef _WIN32
    WaitForSingleObject(server->accept_thread, 1000);
    DeleteCriticalSection(&server->lock);
#else
    pthread_join(server->accept_thread, NULL);
    pthread_mutex_destroy(&server->lock);
#endif
    free(server);
    return 0;
}

static void echo_handler(agi_ws_peer *peer, const char *message, void *userdata) {
    (void)userdata;
    agi_ws_peer_send_text(peer, message ? message : "");
}

int agi_ws_listen(const char *host, int port, const char *path) {
    agi_ws_server_config cfg; memset(&cfg, 0, sizeof(cfg));
    cfg.host = host ? host : "127.0.0.1";
    cfg.port = port;
    cfg.path = path ? path : "/";
    cfg.max_frame_bytes = AGI_WS_DEFAULT_MAX_FRAME;
    cfg.on_message = echo_handler;
    int rc = agi_ws_server_start(&g_default_server, &cfg);
    if (rc != 0) return rc;
    printf("AGILANG native C WebSocket runtime listening on %s:%d%s\n", cfg.host, cfg.port, cfg.path);
    for (;;) {
#ifdef _WIN32
        Sleep(1000);
#else
        sleep(1);
#endif
    }
}

int agi_ws_broadcast(const char *message) {
    return agi_ws_server_broadcast(g_default_server, message);
}


const char *agi_net_runtime_version(void) {
    return "AGILANG native net runtime 1.9.3";
}

const char *agi_net_runtime_capabilities(void) {
    return "{\"runtime\":\"agilang-native-c\",\"version\":\"1.9.3\",\"http\":true,\"websocket\":true,\"sha1\":true,\"base64\":true,\"broadcast\":true,\"ping_pong\":true,\"origin_guard\":true,\"token_guard\":true,\"max_frame_limit\":true,\"mobile_bridge\":true}";
}

int agi_net_runtime_selftest(void) {
    char out[64];
    ws_accept_key("dGhlIHNhbXBsZSBub25jZQ==", out);
    return strcmp(out, "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=") == 0 ? 0 : 1;
}

int agi_http_listen(const char *host, int port, agi_http_handler handler) {
    (void)host;
    if (agi_net_init() != 0) return -1;
    agi_socket_t server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd == AGI_INVALID_SOCKET) return -2;
    int opt = 1;
#ifdef _WIN32
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
#else
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
#endif
    struct sockaddr_in addr; memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET; addr.sin_addr.s_addr = htonl(INADDR_ANY); addr.sin_port = htons((unsigned short)port);
    if (bind(server_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) return -3;
    if (listen(server_fd, 16) < 0) return -4;
    for (;;) {
        agi_socket_t client = accept(server_fd, NULL, NULL);
        if (client == AGI_INVALID_SOCKET) continue;
        char buffer[8192]; int n = (int)recv(client, buffer, sizeof(buffer)-1, 0);
        if (n <= 0) { AGI_CLOSE(client); continue; }
        buffer[n] = 0;
        char method[16] = "GET", path[1024] = "/";
        sscanf(buffer, "%15s %1023s", method, path);
        agi_http_request req = { method, path, "", "" };
        agi_http_response resp = handler ? handler(req) : (agi_http_response){200, "text/plain", "AGILANG native HTTP"};
        if (!resp.content_type) resp.content_type = "text/plain";
        if (!resp.body) resp.body = "";
        char header[512]; int body_len = (int)strlen(resp.body);
        snprintf(header, sizeof(header), "HTTP/1.1 %d OK\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\n\r\n", resp.status, resp.content_type, body_len);
        send(client, header, (int)strlen(header), 0); send(client, resp.body, body_len, 0); AGI_CLOSE(client);
    }
}
