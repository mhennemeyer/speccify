//! Geteilter MCP-Unterbau (Plan toolkit-discovery-terminal.md, T3+):
//! JSON-RPC-Dispatch + Streamable-HTTP- und stdio-Transport. Die
//! Wire-Semantik folgt der dotagent-Referenz (`docs/exec-mcp-contract.md`):
//! Notifications → 202 ohne Body, Parse-Fehler → 400/-32700, unbekannte
//! Methode → -32601, Tool-Ergebnisse als `{content:[{type:"text",…}],isError}`.

pub mod allowlist;
mod http_security;
pub use http_security::MAX_HTTP_BODY_BYTES;

use std::io::{BufRead, Read, Write};
use std::sync::Arc;

use serde_json::{Map, Value, json};

pub const PROTOCOL_VERSION: &str = "2025-03-26";

/// Ein MCP-Server: liefert serverInfo/Tool-Deskriptoren und führt Tools aus.
pub trait ToolServer: Send + Sync + 'static {
    fn server_info(&self) -> Value;
    fn tool_descriptors(&self) -> Vec<Value>;
    /// Ergebnis-Objekt (`text_result`/`error_result`); nie ein JSON-RPC-Fehler.
    fn call_tool(&self, name: Option<&str>, arguments: &Map<String, Value>) -> Value;
}

pub fn text_result(text: impl Into<String>, is_error: bool) -> Value {
    json!({
        "content": [{"type": "text", "text": text.into()}],
        "isError": is_error,
    })
}

pub fn error_result(message: impl Into<String>) -> Value {
    text_result(message, true)
}

/// Verarbeitet eine JSON-RPC-Nachricht. `None` = Notification (Transport
/// antwortet 202 ohne Body bzw. schreibt nichts).
pub fn handle(server: &dyn ToolServer, body: &Value) -> Option<Value> {
    let request_id = body.get("id")?.clone();
    if request_id.is_null() {
        return None;
    }
    let method = body.get("method").and_then(Value::as_str).unwrap_or("");

    let result = match method {
        "initialize" => json!({
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": server.server_info(),
        }),
        "tools/list" => json!({"tools": server.tool_descriptors()}),
        "tools/call" => {
            let empty = Map::new();
            let params = body.get("params").and_then(Value::as_object);
            let name = params
                .and_then(|params| params.get("name"))
                .and_then(Value::as_str);
            let arguments = params
                .and_then(|params| params.get("arguments"))
                .and_then(Value::as_object)
                .unwrap_or(&empty);
            server.call_tool(name, arguments)
        }
        _ => {
            return Some(json!({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": format!("Unbekannte Methode: {method}")},
            }));
        }
    };
    Some(json!({"jsonrpc": "2.0", "id": request_id, "result": result}))
}

pub const PARSE_ERROR: &str =
    r#"{"jsonrpc": "2.0", "id": null, "error": {"code": -32700, "message": "Parse error"}}"#;

/// Streamable-HTTP-Transport (127.0.0.1, threaded). Blockiert den Aufrufer;
/// `banner` beantwortet GET-Requests. Ein optionaler `stream`-Handler
/// bekommt POST-Requests, deren Pfad auf `stream` endet (Exec-MCP, T4).
pub fn serve_http(
    server: Arc<dyn ToolServer>,
    port: u16,
    banner: &'static str,
    stream: Option<Arc<StreamHandler>>,
) -> Result<(), String> {
    let http = tiny_http::Server::http(("127.0.0.1", port))
        .map_err(|e| format!("HTTP-Server auf Port {port}: {e}"))?;
    // Port 0 selects an ephemeral port; validate the actual bound authority.
    let port = http.server_addr().to_ip().expect("TCP listener").port();
    let http = Arc::new(http);
    loop {
        let request = match http.recv() {
            Ok(request) => request,
            Err(_) => continue,
        };
        let server = Arc::clone(&server);
        let stream = stream.clone();
        std::thread::spawn(move || {
            let _ = handle_http_request(server.as_ref(), request, port, banner, stream);
        });
    }
}

pub type StreamHandler = dyn Fn(&Value, &mut dyn Write) + Send + Sync;

fn json_response(payload: &str, status: u32) -> tiny_http::Response<std::io::Cursor<Vec<u8>>> {
    let mut response = tiny_http::Response::from_string(payload).with_status_code(status as u16);
    response.add_header(
        tiny_http::Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap(),
    );
    response
}

fn handle_http_request(
    server: &dyn ToolServer,
    mut request: tiny_http::Request,
    port: u16,
    banner: &'static str,
    stream: Option<Arc<StreamHandler>>,
) -> std::io::Result<()> {
    if let Err(rejection) = http_security::validate(&request, port) {
        let payload = json!({"error": {"code": rejection.code, "message": rejection.message}});
        let mut response = json_response(&payload.to_string(), rejection.status.into());
        if rejection.status == 405 {
            response.add_header(tiny_http::Header::from_bytes("Allow", "GET, POST").unwrap());
        }
        return request.respond(response);
    }
    if request.method() == &tiny_http::Method::Get {
        return request.respond(tiny_http::Response::from_string(banner));
    }
    let mut raw = Vec::new();
    let read = request
        .as_reader()
        .take((MAX_HTTP_BODY_BYTES + 1) as u64)
        .read_to_end(&mut raw);
    if raw.len() > MAX_HTTP_BODY_BYTES {
        return request.respond(json_response(
            r#"{"error":{"code":"body_too_large","message":"Request body exceeds the 1 MiB limit."}}"#, 413,
        ));
    }
    if read.is_err()
        || request
            .body_length()
            .is_some_and(|length| length != raw.len())
    {
        return request.respond(json_response(PARSE_ERROR, 400));
    }
    let Ok(body) = serde_json::from_slice::<Value>(&raw) else {
        return request.respond(json_response(PARSE_ERROR, 400));
    };

    // Streaming-Endpoint (kein JSON-RPC): Pfad endet auf "stream".
    // tiny_http chunk-encodet einen Reader (data_length None) und terminiert
    // die Antwort sauber (0-Chunk) — der Client erkennt das Ende ohne
    // Connection-Close. Der Handler läuft in einem Thread und schiebt SSE-
    // Bytes durch einen Kanal; bricht der Client ab, schließt tiny_http den
    // Reader → der Kanal fällt weg → `emit` liefert BrokenPipe (Stop-Semantik).
    if let Some(stream_handler) = stream
        && request.url().trim_end_matches('/').ends_with("stream")
    {
        let (tx, rx) = std::sync::mpsc::sync_channel::<Vec<u8>>(64);
        std::thread::spawn(move || {
            let mut writer = ChannelWriter { tx };
            stream_handler(&body, &mut writer);
        });
        let headers = vec![
            tiny_http::Header::from_bytes(&b"Content-Type"[..], &b"text/event-stream"[..]).unwrap(),
            tiny_http::Header::from_bytes(&b"Cache-Control"[..], &b"no-cache"[..]).unwrap(),
        ];
        let response = tiny_http::Response::new(
            tiny_http::StatusCode(200),
            headers,
            ChannelReader {
                rx,
                buffer: Vec::new(),
                position: 0,
            },
            None,
            None,
        );
        return request.respond(response);
    }

    match handle(server, &body) {
        Some(response) => request.respond(json_response(&response.to_string(), 200)),
        None => request.respond(tiny_http::Response::empty(202)),
    }
}

/// Schreibt SSE-Bytes in einen Kanal; `Err(BrokenPipe)`, sobald der Reader
/// (die HTTP-Antwort) weg ist — das signalisiert dem Handler den Abbruch.
struct ChannelWriter {
    tx: std::sync::mpsc::SyncSender<Vec<u8>>,
}

impl Write for ChannelWriter {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        self.tx
            .send(buf.to_vec())
            .map(|_| buf.len())
            .map_err(|_| std::io::Error::new(std::io::ErrorKind::BrokenPipe, "client gone"))
    }

    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

/// Blockierender Reader über dem SSE-Kanal; EOF, wenn der Handler fertig ist.
struct ChannelReader {
    rx: std::sync::mpsc::Receiver<Vec<u8>>,
    buffer: Vec<u8>,
    position: usize,
}

impl std::io::Read for ChannelReader {
    fn read(&mut self, out: &mut [u8]) -> std::io::Result<usize> {
        if self.position >= self.buffer.len() {
            match self.rx.recv() {
                Ok(chunk) => {
                    self.buffer = chunk;
                    self.position = 0;
                }
                Err(_) => return Ok(0), // Handler fertig → EOF.
            }
        }
        let available = &self.buffer[self.position..];
        let count = available.len().min(out.len());
        out[..count].copy_from_slice(&available[..count]);
        self.position += count;
        Ok(count)
    }
}

/// stdio-Transport: eine JSON-RPC-Nachricht pro Zeile (MCP-stdio-Framing).
pub fn serve_stdio(server: &dyn ToolServer) {
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        if line.trim().is_empty() {
            continue;
        }
        let Ok(body) = serde_json::from_str::<Value>(&line) else {
            let mut out = stdout.lock();
            let _ = writeln!(out, "{PARSE_ERROR}");
            let _ = out.flush();
            continue;
        };
        if let Some(response) = handle(server, &body) {
            let mut out = stdout.lock();
            let _ = writeln!(out, "{response}");
            let _ = out.flush();
        }
    }
}

#[cfg(test)]
mod http_tests;

#[cfg(test)]
mod tests {
    use super::*;

    struct Echo;

    impl ToolServer for Echo {
        fn server_info(&self) -> Value {
            json!({"name": "echo", "version": "0", "mode": "test"})
        }
        fn tool_descriptors(&self) -> Vec<Value> {
            vec![json!({"name": "echo"})]
        }
        fn call_tool(&self, name: Option<&str>, _arguments: &Map<String, Value>) -> Value {
            match name {
                Some("echo") => text_result("ok", false),
                other => error_result(format!("Unbekanntes Tool: {}", other.unwrap_or("?"))),
            }
        }
    }

    #[test]
    fn dispatch_matches_contract() {
        let init = handle(
            &Echo,
            &json!({"jsonrpc":"2.0","id":1,"method":"initialize"}),
        )
        .unwrap();
        assert_eq!(init["result"]["protocolVersion"], PROTOCOL_VERSION);
        assert_eq!(init["result"]["serverInfo"]["mode"], "test");

        // Notification (ohne id) → None.
        assert!(
            handle(
                &Echo,
                &json!({"jsonrpc":"2.0","method":"notifications/initialized"})
            )
            .is_none()
        );

        let unknown = handle(&Echo, &json!({"jsonrpc":"2.0","id":2,"method":"nope"})).unwrap();
        assert_eq!(unknown["error"]["code"], -32601);

        let call = handle(
            &Echo,
            &json!({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"echo"}}),
        )
        .unwrap();
        assert_eq!(call["result"]["isError"], false);
    }
}
