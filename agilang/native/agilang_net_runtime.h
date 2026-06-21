#ifndef AGILANG_NET_RUNTIME_H
#define AGILANG_NET_RUNTIME_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct agi_http_request {
    const char *method;
    const char *path;
    const char *query;
    const char *body;
} agi_http_request;

typedef struct agi_http_response {
    int status;
    const char *content_type;
    const char *body;
} agi_http_response;

typedef agi_http_response (*agi_http_handler)(agi_http_request request);
int agi_http_listen(const char *host, int port, agi_http_handler handler);
const char *agi_net_runtime_version(void);
const char *agi_net_runtime_capabilities(void);
int agi_net_runtime_selftest(void);

typedef struct agi_ws_peer agi_ws_peer;
typedef void (*agi_ws_message_handler)(agi_ws_peer *peer, const char *message, void *userdata);
typedef void (*agi_ws_event_handler)(agi_ws_peer *peer, void *userdata);

typedef struct agi_ws_server_config {
    const char *host;
    int port;
    const char *path;
    const char *allowed_origin;
    const char *auth_token;
    size_t max_frame_bytes;
    int backlog;
    agi_ws_message_handler on_message;
    agi_ws_event_handler on_connect;
    agi_ws_event_handler on_disconnect;
    void *userdata;
} agi_ws_server_config;

typedef struct agi_ws_server agi_ws_server;

int agi_ws_server_start(agi_ws_server **out, const agi_ws_server_config *config);
int agi_ws_server_stop(agi_ws_server *server);
int agi_ws_server_broadcast(agi_ws_server *server, const char *message);
int agi_ws_peer_send_text(agi_ws_peer *peer, const char *message);
int agi_ws_peer_close(agi_ws_peer *peer);

/* Backwards-compatible simple API: blocking echo/broadcast-capable server. */
int agi_ws_listen(const char *host, int port, const char *path);
int agi_ws_broadcast(const char *message);

#ifdef __cplusplus
}
#endif

#endif
