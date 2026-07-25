//! Geteilter MCP-Unterbau (Plan toolkit-discovery-terminal.md, T3+):
//! JSON-RPC-Dispatch + Streamable-HTTP- und stdio-Transport. Die
//! Wire-Semantik folgt der dotagent-Referenz (`docs/exec-mcp-contract.md`):
//! Notifications → 202 ohne Body, Parse-Fehler → 400/-32700, unbekannte
//! Methode → -32601, Tool-Ergebnisse als `{content:[{type:"text",…}],isError}`.

use std::io::{BufRead, Write};
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
    let http = Arc::new(http);
    loop {
        let request = match http.recv() {
            Ok(request) => request,
            Err(_) => continue,
        };
        let server = Arc::clone(&server);
        let stream = stream.clone();
        std::thread::spawn(move || {
            let _ = handle_http_request(server.as_ref(), request, banner, stream);
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
    banner: &'static str,
    stream: Option<Arc<StreamHandler>>,
) -> std::io::Result<()> {
    if request.method() == &tiny_http::Method::Get {
        return request.respond(tiny_http::Response::from_string(banner));
    }
    let mut raw = String::new();
    let _ = request.as_reader().read_to_string(&mut raw);
    let Ok(body) = serde_json::from_str::<Value>(&raw) else {
        return request.respond(json_response(PARSE_ERROR, 400));
    };

    // Streaming-Endpoint (kein JSON-RPC): Pfad endet auf "stream".
    if let Some(stream_handler) = stream
        && request.url().trim_end_matches('/').ends_with("stream")
    {
        let writer = request.into_writer();
        let mut writer = SseWriter::new(writer);
        stream_handler(&body, &mut writer);
        return Ok(());
    }

    match handle(server, &body) {
        Some(response) => request.respond(json_response(&response.to_string(), 200)),
        None => request.respond(tiny_http::Response::empty(202)),
    }
}

/// Schreibt eine rohe HTTP/1.1-SSE-Antwort auf den Socket (Header + Events).
/// tiny_http gibt uns über `into_writer` die nackte Verbindung — genau
/// richtig für flush-genaues SSE und Broken-Pipe-Erkennung (Stop-Semantik).
struct SseWriter {
    inner: Box<dyn Write + Send>,
    headers_sent: bool,
}

impl SseWriter {
    fn new(inner: Box<dyn Write + Send>) -> Self {
        Self {
            inner,
            headers_sent: false,
        }
    }
}

impl Write for SseWriter {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        if !self.headers_sent {
            self.headers_sent = true;
            self.inner.write_all(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n",
            )?;
        }
        self.inner.write(buf)
    }

    fn flush(&mut self) -> std::io::Result<()> {
        self.inner.flush()
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
