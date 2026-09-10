//! Exercise the real HTTP parser and both dispatch paths, not only header helpers.
use super::*;
use std::net::{Shutdown, TcpStream};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

#[derive(Default)]
struct CountingServer(AtomicUsize);

impl ToolServer for CountingServer {
    fn server_info(&self) -> Value {
        json!({"name":"http-test","version":"0"})
    }
    fn tool_descriptors(&self) -> Vec<Value> {
        vec![json!({"name":"echo"})]
    }
    fn call_tool(&self, _: Option<&str>, _: &Map<String, Value>) -> Value {
        self.0.fetch_add(1, Ordering::SeqCst);
        text_result("called", false)
    }
}

const CALL: &str = r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"echo"}}"#;

fn exchange(method: &str, path: &str, headers: &str, body: &[u8]) -> (String, usize, usize) {
    let http = tiny_http::Server::http(("127.0.0.1", 0)).unwrap();
    let address = http.server_addr().to_ip().unwrap();
    let server = Arc::new(CountingServer::default());
    let calls = server.clone();
    let streams = Arc::new(AtomicUsize::new(0));
    let stream_calls = streams.clone();
    let worker = std::thread::spawn(move || {
        let request = http
            .recv_timeout(Duration::from_secs(5))
            .unwrap()
            .expect("request");
        let stream: Arc<StreamHandler> = Arc::new(move |_, writer| {
            stream_calls.fetch_add(1, Ordering::SeqCst);
            writer
                .write_all(b"data: {\"type\":\"line\",\"text\":\"first\"}\n\n")
                .unwrap();
            writer
                .write_all(b"data: {\"type\":\"exit\",\"exit_code\":0}\n\n")
                .unwrap();
        });
        handle_http_request(
            server.as_ref(),
            request,
            address.port(),
            "test banner",
            Some(stream),
        )
        .unwrap();
    });
    let mut socket = TcpStream::connect(address).unwrap();
    socket
        .set_read_timeout(Some(Duration::from_secs(5)))
        .unwrap();
    socket
        .set_write_timeout(Some(Duration::from_secs(5)))
        .unwrap();
    let headers = headers.replace("{port}", &address.port().to_string());
    write!(
        socket,
        "{method} {path} HTTP/1.1\r\nConnection: close\r\n{headers}\r\n"
    )
    .unwrap();
    socket.write_all(body).unwrap();
    socket.shutdown(Shutdown::Write).unwrap();
    let mut response = String::new();
    socket.read_to_string(&mut response).unwrap();
    drop(socket);
    worker.join().unwrap();
    (
        response,
        calls.0.load(Ordering::SeqCst),
        streams.load(Ordering::SeqCst),
    )
}

fn post_headers(extra: &str, length: usize) -> String {
    format!(
        "Host: 127.0.0.1:{{port}}\r\nContent-Type: application/json\r\nContent-Length: {length}\r\n{extra}"
    )
}

fn status(response: &str) -> u16 {
    response.split_whitespace().nth(1).unwrap().parse().unwrap()
}

#[test]
fn foreign_origins_never_reach_rpc_stream_or_banner() {
    for origin in [
        "https://evil.example",
        "null",
        "",
        "http://localhost:1420",
        "http://127.0.0.1:{port}",
        "https://evil.example https://localhost",
    ] {
        for path in ["/", "/stream", "/mcp/stream/"] {
            let headers = post_headers(&format!("Origin: {origin}\r\n"), CALL.len());
            let (response, calls, streams) = exchange("POST", path, &headers, CALL.as_bytes());
            assert_eq!(
                (status(&response), calls, streams),
                (403, 0, 0),
                "{origin}: {response}"
            );
        }
    }
    let (response, calls, streams) = exchange(
        "GET",
        "/",
        "Host: localhost:{port}\r\nOrigin: https://evil.example\r\n",
        b"",
    );
    assert_eq!((status(&response), calls, streams), (403, 0, 0));
}

#[test]
fn authority_must_match_literal_loopback_and_actual_port() {
    for host in [
        "evil.example:{port}",
        "localhost.evil.example:{port}",
        "127.0.0.1.evil.example:{port}",
        "127.0.0.1:1",
        "localhost",
        "127.1:{port}",
        "0.0.0.0:{port}",
        "localhost:{port}@evil.example",
        "localhost:{port}, evil.example",
        "localhost.:{port}",
    ] {
        let headers = format!(
            "Host: {host}\r\nX-Forwarded-Host: localhost:{{port}}\r\nContent-Type: application/json\r\nContent-Length: {}\r\n",
            CALL.len()
        );
        let (response, calls, streams) = exchange("POST", "/stream", &headers, CALL.as_bytes());
        assert_eq!(
            (status(&response), calls, streams),
            (403, 0, 0),
            "{host}: {response}"
        );
    }
    for host in ["", "Host: localhost:{port}\r\nHost: 127.0.0.1:{port}\r\n"] {
        let headers = format!("{host}Content-Length: 0\r\n");
        let (response, calls, streams) = exchange("GET", "/", &headers, b"");
        assert_eq!((status(&response), calls, streams), (403, 0, 0));
    }
}

#[test]
fn native_handshake_banner_and_rpc_remain_compatible() {
    for (body, expected) in [
        (r#"{"jsonrpc":"2.0","id":1,"method":"initialize"}"#, 200),
        (
            r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#,
            202,
        ),
        (r#"{"jsonrpc":"2.0","id":2,"method":"tools/list"}"#, 200),
    ] {
        let headers = post_headers(
            "Accept: application/json, text/event-stream\r\n",
            body.len(),
        );
        let (response, calls, streams) = exchange("POST", "/mcp", &headers, body.as_bytes());
        assert_eq!((status(&response), calls, streams), (expected, 0, 0));
        if body.contains("initialize\"") {
            assert!(response.contains(PROTOCOL_VERSION));
        }
        if expected == 202 {
            assert!(response.ends_with("\r\n\r\n"));
        }
        if body.contains("tools/list") {
            assert!(response.contains("echo"));
        }
    }
    for host in ["127.0.0.1", "localhost", "LOCALHOST"] {
        let headers = format!(
            "Host: {host}:{{port}}\r\nContent-Type: Application/JSON; charset=utf-8\r\nContent-Length: {}\r\n",
            CALL.len()
        );
        let (response, calls, streams) = exchange("POST", "/any-path", &headers, CALL.as_bytes());
        assert_eq!((status(&response), calls, streams), (200, 1, 0));
    }
    let (response, _, _) = exchange("GET", "/", "Host: localhost:{port}\r\n", b"");
    assert_eq!(status(&response), 200);
    assert!(response.ends_with("test banner"));
}

#[test]
fn methods_and_browser_simple_content_types_are_rejected() {
    for method in ["PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"] {
        let (response, calls, streams) = exchange(
            method,
            "/stream",
            &post_headers("", CALL.len()),
            CALL.as_bytes(),
        );
        assert_eq!((status(&response), calls, streams), (405, 0, 0));
        assert!(response.contains("Allow: GET, POST"));
    }
    for content_type in [
        "",
        "Content-Type: text/plain\r\n",
        "Content-Type: application/x-www-form-urlencoded\r\n",
        "Content-Type: multipart/form-data; boundary=x\r\n",
        "Content-Type: application/json\r\nContent-Type: text/plain\r\n",
    ] {
        let headers = format!(
            "Host: localhost:{{port}}\r\nContent-Length: {}\r\n{content_type}",
            CALL.len()
        );
        let (response, calls, streams) = exchange("POST", "/", &headers, CALL.as_bytes());
        assert_eq!((status(&response), calls, streams), (415, 0, 0));
    }
}

#[test]
fn bounded_bodies_include_chunked_and_exact_limit() {
    let mut body = CALL.as_bytes().to_vec();
    body.resize(MAX_HTTP_BODY_BYTES, b' ');
    let (response, calls, streams) = exchange("POST", "/", &post_headers("", body.len()), &body);
    assert_eq!((status(&response), calls, streams), (200, 1, 0));
    body.push(b' ');
    for path in ["/", "/stream"] {
        let (response, calls, streams) =
            exchange("POST", path, &post_headers("", body.len()), &body);
        assert_eq!((status(&response), calls, streams), (413, 0, 0));
        let mut chunked = format!("{:X}\r\n", body.len()).into_bytes();
        chunked.extend_from_slice(&body);
        chunked.extend_from_slice(b"\r\n0\r\n\r\n");
        let (response, calls, streams) = exchange(
            "POST",
            path,
            "Host: localhost:{port}\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n",
            &chunked,
        );
        assert_eq!((status(&response), calls, streams), (413, 0, 0));
    }
}

#[test]
fn malformed_requests_cannot_dispatch() {
    for body in [b"not json".as_slice(), &[0xff, 0xfe]] {
        let (response, calls, streams) =
            exchange("POST", "/stream", &post_headers("", body.len()), body);
        assert_eq!((status(&response), calls, streams), (400, 0, 0));
        assert!(response.contains("-32700"));
    }
    for framing in [
        "Content-Length: 0\r\nContent-Length: 0\r\n",
        "Content-Length: wrong\r\n",
        "Content-Length: 0\r\nTransfer-Encoding: chunked\r\n",
        "Transfer-Encoding: gzip\r\n",
        "Transfer-Encoding: chunked\r\nTransfer-Encoding: chunked\r\n",
    ] {
        let headers =
            format!("Host: localhost:{{port}}\r\nContent-Type: application/json\r\n{framing}");
        let (response, calls, streams) = exchange("POST", "/stream", &headers, b"0\r\n\r\n");
        assert_eq!(
            (status(&response), calls, streams),
            (400, 0, 0),
            "{framing}: {response}"
        );
    }
}

#[test]
fn valid_stream_still_emits_lines_and_exit() {
    let body = b"{}";
    let (response, calls, streams) =
        exchange("POST", "/stream", &post_headers("", body.len()), body);
    assert_eq!((status(&response), calls, streams), (200, 0, 1));
    assert!(response.contains("text/event-stream"));
    assert!(response.contains("data: {\"type\":\"line\""));
    assert!(response.contains("data: {\"type\":\"exit\""));
}

#[test]
fn large_declared_body_is_rejected_without_continue_or_reading_it() {
    let headers = post_headers("Expect: 100-continue\r\n", MAX_HTTP_BODY_BYTES + 1);
    let (response, calls, streams) = exchange("POST", "/stream", &headers, b"");
    assert_eq!((status(&response), calls, streams), (413, 0, 0));
    assert!(!response.contains("100 Continue"));
}

#[test]
fn truncated_body_and_duplicate_origins_cannot_dispatch() {
    let (response, calls, streams) =
        exchange("POST", "/", &post_headers("", 2048), CALL.as_bytes());
    assert_eq!((status(&response), calls, streams), (400, 0, 0));
    let headers = post_headers(
        "oRiGiN: http://localhost:{port}\r\nOrigin: https://evil.example\r\n",
        CALL.len(),
    );
    let (response, calls, streams) = exchange("POST", "/", &headers, CALL.as_bytes());
    assert_eq!((status(&response), calls, streams), (403, 0, 0));
}

#[test]
fn native_chunked_json_remains_supported() {
    let body = format!("{:X}\r\n{CALL}\r\n0\r\n\r\n", CALL.len());
    let (response, calls, streams) = exchange(
        "POST",
        "/",
        "Host: localhost:{port}\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n",
        body.as_bytes(),
    );
    assert_eq!((status(&response), calls, streams), (200, 1, 0));
}
